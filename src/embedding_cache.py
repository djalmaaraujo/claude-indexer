"""
Embedding cache for fast re-indexing.
Caches embeddings by content hash to avoid re-computing unchanged chunks.
"""

import hashlib
import pickle
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from src.config import DEBUG


class EmbeddingCache:
    """Cache for storing and retrieving embeddings by content hash."""

    def __init__(self, cache_path: Path):
        """
        Initialize the embedding cache.

        Args:
            cache_path: Path to cache file (*.pkl)
        """
        self.cache_path = cache_path
        self.cache: Dict[str, List[float]] = {}
        self.hits = 0
        self.misses = 0

        # Load existing cache if available
        self._load()

    def _load(self):
        """Load cache from disk."""
        if self.cache_path.exists():
            try:
                with open(self.cache_path, "rb") as f:
                    self.cache = pickle.load(f)

                if DEBUG:
                    print(f"[Cache] Loaded {len(self.cache)} embeddings from cache")

            except Exception as e:
                if DEBUG:
                    print(f"[Cache] Could not load cache: {e}")
                self.cache = {}

    def save(self):
        """Save cache to disk."""
        try:
            # Create parent directory if needed
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self.cache_path, "wb") as f:
                pickle.dump(self.cache, f, protocol=pickle.HIGHEST_PROTOCOL)

            if DEBUG:
                print(f"[Cache] Saved {len(self.cache)} embeddings to cache")

        except Exception as e:
            print(f"Warning: Could not save cache: {e}")

    def get(self, content: str) -> Optional[List[float]]:
        """
        Get embedding from cache.

        Args:
            content: Text content to look up

        Returns:
            Embedding vector if found, None otherwise
        """
        content_hash = self._hash_content(content)

        if content_hash in self.cache:
            self.hits += 1
            return self.cache[content_hash]

        self.misses += 1
        return None

    def put(self, content: str, embedding: List[float]):
        """
        Store embedding in cache.

        Args:
            content: Text content
            embedding: Embedding vector
        """
        content_hash = self._hash_content(content)
        self.cache[content_hash] = embedding

    def get_or_compute_batch(
        self, contents: List[str], compute_fn
    ) -> Tuple[List[List[float]], int, int]:
        """
        Get embeddings from cache or compute missing ones.

        Args:
            contents: List of text contents
            compute_fn: Function to compute embeddings for missing content

        Returns:
            Tuple of (embeddings, cache_hits, cache_misses)
        """
        embeddings = []
        missing_indices = []
        missing_contents = []

        # Check cache
        for i, content in enumerate(contents):
            cached = self.get(content)
            if cached is not None:
                embeddings.append(cached)
            else:
                # Placeholder, will be filled later
                embeddings.append([])
                missing_indices.append(i)
                missing_contents.append(content)

        # Compute missing embeddings
        if missing_contents:
            new_embeddings = compute_fn(missing_contents)

            # Fill in missing embeddings and update cache
            for idx, embedding in zip(missing_indices, new_embeddings, strict=True):
                embeddings[idx] = embedding
                self.put(missing_contents[missing_indices.index(idx)], embedding)

        return embeddings, self.hits, self.misses

    def _hash_content(self, content: str) -> str:
        """
        Generate hash for content.

        Args:
            content: Text content

        Returns:
            MD5 hash hex string
        """
        return hashlib.md5(content.encode("utf-8"), usedforsecurity=False).hexdigest()

    def get_stats(self) -> Dict[str, int]:
        """
        Get cache statistics.

        Returns:
            Dict with hits, misses, size, hit_rate
        """
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0

        return {
            "hits": self.hits,
            "misses": self.misses,
            "size": len(self.cache),
            "hit_rate": hit_rate,
        }

    def clear(self):
        """Clear the cache."""
        self.cache = {}
        self.hits = 0
        self.misses = 0

        if self.cache_path.exists():
            self.cache_path.unlink()

    def __len__(self) -> int:
        """Return number of cached embeddings."""
        return len(self.cache)
