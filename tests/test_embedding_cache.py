"""Tests for embedding cache functionality."""

import tempfile
from pathlib import Path

import pytest

from src.embedding_cache import EmbeddingCache


class TestEmbeddingCache:
    """Test embedding cache operations."""

    def test_cache_initialization(self):
        """Test cache can be initialized."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "test_cache.pkl"
            cache = EmbeddingCache(cache_path)

            assert len(cache) == 0
            assert cache.hits == 0
            assert cache.misses == 0

    def test_cache_put_and_get(self):
        """Test putting and getting embeddings from cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "test_cache.pkl"
            cache = EmbeddingCache(cache_path)

            # Put embedding
            content = "def hello(): pass"
            embedding = [0.1, 0.2, 0.3]
            cache.put(content, embedding)

            # Get embedding
            result = cache.get(content)
            assert result == embedding
            assert cache.hits == 1
            assert cache.misses == 0

    def test_cache_miss(self):
        """Test cache miss for non-existent content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "test_cache.pkl"
            cache = EmbeddingCache(cache_path)

            result = cache.get("non-existent content")
            assert result is None
            assert cache.hits == 0
            assert cache.misses == 1

    def test_cache_persistence(self):
        """Test cache can be saved and loaded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "test_cache.pkl"

            # Create and populate cache
            cache1 = EmbeddingCache(cache_path)
            cache1.put("content1", [0.1, 0.2])
            cache1.put("content2", [0.3, 0.4])
            cache1.save()

            # Load cache in new instance
            cache2 = EmbeddingCache(cache_path)
            assert len(cache2) == 2
            assert cache2.get("content1") == [0.1, 0.2]
            assert cache2.get("content2") == [0.3, 0.4]

    def test_cache_stats(self):
        """Test cache statistics calculation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "test_cache.pkl"
            cache = EmbeddingCache(cache_path)

            # Add some entries and access them
            cache.put("content1", [0.1, 0.2])
            cache.put("content2", [0.3, 0.4])

            cache.get("content1")  # hit
            cache.get("content1")  # hit
            cache.get("content3")  # miss
            cache.get("content2")  # hit

            stats = cache.get_stats()
            assert stats["hits"] == 3
            assert stats["misses"] == 1
            assert stats["size"] == 2
            assert stats["hit_rate"] == 75.0

    def test_get_or_compute_batch(self):
        """Test batch operations with cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "test_cache.pkl"
            cache = EmbeddingCache(cache_path)

            # Pre-populate with one entry
            cache.put("content1", [0.1, 0.2])

            # Batch with mixed hits and misses
            contents = ["content1", "content2", "content3"]

            def compute_fn(missing_contents):
                return [[0.3, 0.4], [0.5, 0.6]]

            embeddings, hits, misses = cache.get_or_compute_batch(contents, compute_fn)

            assert len(embeddings) == 3
            assert embeddings[0] == [0.1, 0.2]  # cache hit
            assert embeddings[1] == [0.3, 0.4]  # computed
            assert embeddings[2] == [0.5, 0.6]  # computed
            assert hits == 1
            assert misses == 2

    def test_cache_clear(self):
        """Test cache clearing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "test_cache.pkl"
            cache = EmbeddingCache(cache_path)

            cache.put("content1", [0.1, 0.2])
            cache.put("content2", [0.3, 0.4])
            cache.save()

            assert len(cache) == 2
            assert cache_path.exists()

            cache.clear()

            assert len(cache) == 0
            assert cache.hits == 0
            assert cache.misses == 0
            assert not cache_path.exists()

    def test_cache_content_hashing(self):
        """Test that same content produces same hash."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "test_cache.pkl"
            cache = EmbeddingCache(cache_path)

            content = "def test(): pass"
            cache.put(content, [0.1, 0.2])

            # Same content should retrieve same embedding
            result = cache.get(content)
            assert result == [0.1, 0.2]

            # Different content should not
            result = cache.get("def test(): return True")
            assert result is None
