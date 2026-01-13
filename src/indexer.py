"""
Code indexer with parallel processing and incremental updates.
Builds a vector database of code chunks for fast semantic search.
"""

import hashlib
import json
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import lancedb
import pyarrow as pa
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
)

from src.chunker import CodeChunk, chunk_file
from src.config import (
    DEBUG,
    EMBEDDING_DIM,
    ENABLE_PROGRESS_BAR,
    HASH_ALGORITHM,
    MAX_WORKERS,
    USE_INCREMENTAL,
    get_index_path,
    is_code_file,
    should_skip_dir,
)
from src.embedder import Embedder


@dataclass
class FileMetadata:
    """Metadata for tracking file changes."""

    path: str
    mtime: float
    size: int
    hash: str


class Indexer:
    """Code indexer with incremental updates."""

    def __init__(self, project_path: Path, force: bool = False):
        self.project_path = project_path.resolve()
        self.force = force
        self.index_path = get_index_path(self.project_path)
        self.db_path = self.index_path / "chunks.lance"  # Table name matches what we create
        self.metadata_path = self.index_path / "metadata.json"

        # Load existing metadata
        self.file_metadata: Dict[str, FileMetadata] = {}
        if not force and self.metadata_path.exists():
            self._load_metadata()

        # Stats
        self.stats = {
            "files_scanned": 0,
            "files_indexed": 0,
            "files_skipped": 0,
            "files_unchanged": 0,
            "chunks_created": 0,
            "total_time": 0.0,
        }

    def _load_metadata(self):
        """Load existing file metadata."""
        try:
            with open(self.metadata_path, "r") as f:
                data = json.load(f)
                self.file_metadata = {path: FileMetadata(**meta) for path, meta in data.items()}
        except Exception as e:
            if DEBUG:
                print(f"Could not load metadata: {e}")
            self.file_metadata = {}

    def _save_metadata(self):
        """Save file metadata."""
        try:
            data = {path: asdict(meta) for path, meta in self.file_metadata.items()}
            with open(self.metadata_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save metadata: {e}")

    def _compute_file_hash(self, file_path: Path) -> str:
        """Compute hash of file contents."""
        hasher = hashlib.new(HASH_ALGORITHM)
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception:
            return ""

    def _has_file_changed(self, file_path: Path) -> bool:
        """Check if a file has changed since last indexing."""
        if self.force or not USE_INCREMENTAL:
            return True

        path_str = str(file_path.relative_to(self.project_path))
        if path_str not in self.file_metadata:
            return True

        meta = self.file_metadata[path_str]

        # Check mtime and size first (fast)
        stat = file_path.stat()
        if stat.st_mtime != meta.mtime or stat.st_size != meta.size:
            return True

        # If mtime and size match, check hash (slower but reliable)
        file_hash = self._compute_file_hash(file_path)
        return file_hash != meta.hash

    def _find_code_files(self) -> List[Path]:
        """Find all code files in the project."""
        files = []

        for path in self.project_path.rglob("*"):
            # Skip directories
            if path.is_dir():
                if should_skip_dir(path):
                    continue
                continue

            # Check if it's a code file
            if is_code_file(path):
                files.append(path)

        return files

    def _process_file(
        self, file_path: Path
    ) -> Tuple[Optional[List[CodeChunk]], Optional[FileMetadata]]:
        """
        Process a single file and return its chunks.
        This runs in a separate process for parallel processing.
        """
        try:
            # Check if file has changed
            if not self._has_file_changed(file_path):
                return None, None

            # Chunk the file
            chunks = chunk_file(file_path)

            if not chunks:
                return None, None

            # Create metadata
            stat = file_path.stat()
            file_hash = self._compute_file_hash(file_path)
            metadata = FileMetadata(
                path=str(file_path.relative_to(self.project_path)),
                mtime=stat.st_mtime,
                size=stat.st_size,
                hash=file_hash,
            )

            return chunks, metadata

        except Exception as e:
            if DEBUG:
                print(f"Error processing {file_path}: {e}")
            return None, None

    def index(self):
        """Index the project with parallel processing."""
        start_time = time.time()

        print(f"\n🔍 Scanning project: {self.project_path}")

        # Find all code files
        all_files = self._find_code_files()
        self.stats["files_scanned"] = len(all_files)

        print(f"📁 Found {len(all_files)} code files")

        if not all_files:
            print("⚠️  No code files found")
            return

        # Process files in parallel
        all_chunks = []
        new_metadata = {}

        if ENABLE_PROGRESS_BAR:
            progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TimeRemainingColumn(),
            )

            with progress:
                task = progress.add_task("Chunking files...", total=len(all_files))

                # Use ProcessPoolExecutor for CPU-bound chunking
                with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
                    futures = {
                        executor.submit(self._process_file, file_path): file_path
                        for file_path in all_files
                    }

                    for future in as_completed(futures):
                        file_path = futures[future]
                        try:
                            chunks, metadata = future.result()

                            if chunks is not None and metadata is not None:
                                all_chunks.extend(chunks)
                                new_metadata[metadata.path] = metadata
                                self.stats["files_indexed"] += 1
                            elif chunks is None and metadata is None:
                                self.stats["files_unchanged"] += 1
                            else:
                                self.stats["files_skipped"] += 1

                        except Exception as e:
                            if DEBUG:
                                print(f"Error processing {file_path}: {e}")
                            self.stats["files_skipped"] += 1

                        progress.advance(task)
        else:
            # No progress bar
            with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
                futures = {
                    executor.submit(self._process_file, file_path): file_path
                    for file_path in all_files
                }

                for future in as_completed(futures):
                    try:
                        chunks, metadata = future.result()
                        if chunks is not None and metadata is not None:
                            all_chunks.extend(chunks)
                            new_metadata[metadata.path] = metadata
                            self.stats["files_indexed"] += 1
                        elif chunks is None and metadata is None:
                            self.stats["files_unchanged"] += 1
                    except Exception as e:
                        if DEBUG:
                            print(f"Error: {e}")
                        self.stats["files_skipped"] += 1

        self.stats["chunks_created"] = len(all_chunks)

        if not all_chunks:
            print("\n✅ No new chunks to index (all files up to date)")
            self.stats["total_time"] = time.time() - start_time
            return

        print(f"\n📦 Created {len(all_chunks)} chunks")
        print("🔢 Generating embeddings...")

        # Generate embeddings
        embed_start = time.time()
        embeddings = self._generate_embeddings(all_chunks)
        embed_time = time.time() - embed_start

        print(
            f"⚡ Embeddings generated in {embed_time:.1f}s ({len(embeddings)/embed_time:.1f} chunks/s)"
        )

        # Store in LanceDB
        print("💾 Storing in vector database...")
        self._store_in_db(all_chunks, embeddings)

        # Update metadata
        self.file_metadata.update(new_metadata)
        self._save_metadata()

        self.stats["total_time"] = time.time() - start_time

        # Print stats
        self._print_stats()

    def _generate_embeddings(self, chunks: List[CodeChunk]) -> List[List[float]]:
        """Generate embeddings for chunks."""
        # Prepare texts for embedding
        texts = []
        for chunk in chunks:
            # Combine context and content for better embeddings
            text_parts = []

            if chunk.context:
                text_parts.append(chunk.context)

            text_parts.append(chunk.content)

            text = "\n\n".join(text_parts)
            texts.append(text)

        # Generate embeddings in batches
        with Embedder() as embedder:
            embeddings = embedder.embed_batch(texts)

        return embeddings  # type: ignore[no-any-return]

    def _store_in_db(self, chunks: List[CodeChunk], embeddings: List[List[float]]):
        """Store chunks and embeddings in LanceDB."""
        # Prepare data for LanceDB
        data = []
        for chunk, embedding in zip(chunks, embeddings, strict=True):
            data.append(
                {
                    "id": f"{chunk.file_path}:{chunk.start_line}-{chunk.end_line}",
                    "file_path": chunk.file_path,
                    "start_line": chunk.start_line,
                    "end_line": chunk.end_line,
                    "chunk_type": chunk.chunk_type,
                    "context": chunk.context or "",
                    "content": chunk.content,
                    "vector": embedding,
                }
            )

        # Connect to LanceDB
        db = lancedb.connect(str(self.index_path))

        # Create or update table
        if (self.db_path).exists() and not self.force:
            # Append to existing table
            table = db.open_table("chunks")
            table.add(data)
        else:
            # Create new table
            schema = pa.schema(
                [
                    pa.field("id", pa.string()),
                    pa.field("file_path", pa.string()),
                    pa.field("start_line", pa.int64()),
                    pa.field("end_line", pa.int64()),
                    pa.field("chunk_type", pa.string()),
                    pa.field("context", pa.string()),
                    pa.field("content", pa.string()),
                    pa.field("vector", pa.list_(pa.float32(), EMBEDDING_DIM)),
                ]
            )
            db.create_table("chunks", data=data, schema=schema, mode="overwrite")

    def _print_stats(self):
        """Print indexing statistics."""
        print("\n" + "=" * 50)
        print("📊 Indexing Statistics")
        print("=" * 50)
        print(f"Files scanned:     {self.stats['files_scanned']}")
        print(f"Files indexed:     {self.stats['files_indexed']}")
        print(f"Files unchanged:   {self.stats['files_unchanged']}")
        print(f"Files skipped:     {self.stats['files_skipped']}")
        print(f"Chunks created:    {self.stats['chunks_created']}")
        print(f"Total time:        {self.stats['total_time']:.2f}s")

        if self.stats["files_indexed"] > 0:
            avg_time = self.stats["total_time"] / self.stats["files_indexed"]
            print(f"Avg time/file:     {avg_time:.3f}s")

        print("=" * 50)
        print(f"✅ Index stored in: {self.index_path}\n")


def index_project(project_path: Path, force: bool = False):
    """
    Convenience function to index a project.

    Args:
        project_path: Path to the project root
        force: If True, re-index all files regardless of changes
    """
    indexer = Indexer(project_path, force=force)
    indexer.index()
