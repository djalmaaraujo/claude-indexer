"""
Fast semantic code search using vector similarity.
Reads fresh file content from disk for accuracy.
"""

import time
from dataclasses import dataclass
from pathlib import Path
from typing import List

import lancedb

from src.config import (
    DEBUG,
    DEFAULT_TOP_K,
    MAX_TOP_K,
    RESULT_CONTEXT_LINES,
    get_index_path,
)
from src.embedder import embed


@dataclass
class SearchResult:
    """Represents a search result."""

    file_path: str
    start_line: int
    end_line: int
    score: float
    chunk_type: str
    content: str
    context_before: str = ""
    context_after: str = ""


class Searcher:
    """Fast semantic code searcher."""

    def __init__(self, project_path: Path):
        self.project_path = project_path.resolve()
        self.index_path = get_index_path(self.project_path)
        self.db_path = self.index_path / "chunks.lance"  # Match indexer's table name

        # Check if index exists
        if not self.db_path.exists():
            raise FileNotFoundError(
                f"No index found for {project_path}. " f"Run 'code-index {project_path}' first."
            )

        # Connect to LanceDB
        self.db = lancedb.connect(str(self.index_path))
        self.table = self.db.open_table("chunks")

    def search(self, query: str, top_k: int = DEFAULT_TOP_K) -> List[SearchResult]:
        """
        Search for code chunks semantically similar to the query.

        Args:
            query: Search query
            top_k: Number of results to return

        Returns:
            List of search results ordered by relevance

        Note:
            Content is always read fresh from filesystem for accuracy.
        """
        start_time = time.time()

        # Limit top_k
        top_k = min(top_k, MAX_TOP_K)

        # Generate query embedding
        embed_start = time.time()
        query_embedding = embed(query)
        embed_time = (time.time() - embed_start) * 1000

        if DEBUG:
            print(f"[Search] Query embedding: {embed_time:.1f}ms")

        # Vector search
        search_start = time.time()
        results = self.table.search(query_embedding).limit(top_k).to_list()
        search_time = (time.time() - search_start) * 1000

        if DEBUG:
            print(f"[Search] Vector search: {search_time:.1f}ms")

        # Read fresh content and build search results
        read_start = time.time()
        search_results = []

        for result in results:
            # Always read fresh content from filesystem
            # (Content not stored in index for space efficiency)
            content, context_before, context_after = self._read_fresh_content(
                result["file_path"],
                result["start_line"],
                result["end_line"],
            )

            search_results.append(
                SearchResult(
                    file_path=result["file_path"],
                    start_line=result["start_line"],
                    end_line=result["end_line"],
                    score=result["_distance"],  # LanceDB returns distance
                    chunk_type=result["chunk_type"],
                    content=content,
                    context_before=context_before,
                    context_after=context_after,
                )
            )

        read_time = (time.time() - read_start) * 1000

        total_time = (time.time() - start_time) * 1000

        if DEBUG:
            print(f"[Search] Read files: {read_time:.1f}ms")
            print(f"[Search] Total: {total_time:.1f}ms")

        return search_results

    def _read_fresh_content(
        self, file_path: str, start_line: int, end_line: int
    ) -> tuple[str, str, str]:
        """
        Read fresh content from the filesystem.

        Args:
            file_path: Relative file path
            start_line: Starting line number (1-indexed)
            end_line: Ending line number (1-indexed)

        Returns:
            Tuple of (content, context_before, context_after)
        """
        try:
            full_path = self.project_path / file_path
            lines = full_path.read_text(encoding="utf-8", errors="ignore").split("\n")

            # Extract the content (convert to 0-indexed)
            content_lines = lines[start_line - 1 : end_line]
            content = "\n".join(content_lines)

            # Extract context before
            context_start = max(0, start_line - 1 - RESULT_CONTEXT_LINES)
            context_before_lines = lines[context_start : start_line - 1]
            context_before = "\n".join(context_before_lines) if context_before_lines else ""

            # Extract context after
            context_end = min(len(lines), end_line + RESULT_CONTEXT_LINES)
            context_after_lines = lines[end_line:context_end]
            context_after = "\n".join(context_after_lines) if context_after_lines else ""

            return content, context_before, context_after

        except Exception as e:
            if DEBUG:
                print(f"Warning: Could not read {file_path}: {e}")
            # Fall back to empty content
            return "", "", ""

    def format_results_markdown(
        self, results: List[SearchResult], include_context: bool = True
    ) -> str:
        """
        Format search results as markdown for Claude consumption.

        Args:
            results: List of search results
            include_context: Whether to include surrounding context

        Returns:
            Markdown-formatted string
        """
        if not results:
            return "No results found."

        output = []
        output.append("# Search Results\n")

        for i, result in enumerate(results, 1):
            output.append(f"## Result {i}: {result.file_path}:{result.start_line}\n")
            output.append(f"**Type:** {result.chunk_type}  ")
            output.append(f"**Score:** {result.score:.4f}  ")
            output.append(f"**Lines:** {result.start_line}-{result.end_line}\n")

            # Add code block
            output.append("```")

            if include_context and result.context_before:
                output.append("# ... context before ...")
                output.append(result.context_before)
                output.append("")

            output.append(result.content)

            if include_context and result.context_after:
                output.append("")
                output.append("# ... context after ...")
                output.append(result.context_after)

            output.append("```\n")

        return "\n".join(output)

    def format_results_json(self, results: List[SearchResult]) -> str:
        """
        Format search results as JSON.

        Args:
            results: List of search results

        Returns:
            JSON string
        """
        import json

        data = [
            {
                "file_path": r.file_path,
                "start_line": r.start_line,
                "end_line": r.end_line,
                "score": r.score,
                "chunk_type": r.chunk_type,
                "content": r.content,
            }
            for r in results
        ]

        return json.dumps(data, indent=2)


def search(project_path: Path, query: str, top_k: int = DEFAULT_TOP_K) -> List[SearchResult]:
    """
    Convenience function to search a project.

    Args:
        project_path: Path to the project root
        query: Search query
        top_k: Number of results to return

    Returns:
        List of search results
    """
    searcher = Searcher(project_path)
    return searcher.search(query, top_k=top_k)
