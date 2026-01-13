"""Tests for the embedder module."""

from src.embedder import Embedder, embed, embed_batch, get_embedder


class TestEmbedder:
    """Test cases for the Embedder class."""

    def test_embedder_initialization(self):
        """Test embedder initializes successfully."""
        embedder = Embedder()
        assert hasattr(embedder, "model")
        assert embedder.model is not None

    def test_embed_single(self):
        """Test embedding a single text."""
        embedder = Embedder()
        text = "This is a test sentence for embedding."
        embedding = embedder.embed_single(text)

        assert isinstance(embedding, list)
        assert len(embedding) == 384  # all-MiniLM-L6-v2 dimension
        assert all(isinstance(val, float) for val in embedding)

    def test_embed_batch(self):
        """Test embedding multiple texts."""
        embedder = Embedder()
        texts = [
            "First test sentence",
            "Second test sentence",
            "Third test sentence",
        ]
        embeddings = embedder.embed_batch(texts)

        assert isinstance(embeddings, list)
        assert len(embeddings) == 3
        assert all(len(emb) == 384 for emb in embeddings)
        assert all(isinstance(val, float) for emb in embeddings for val in emb)

    def test_embed_batch_empty(self):
        """Test embedding empty list returns empty list."""
        embedder = Embedder()
        embeddings = embedder.embed_batch([])
        assert embeddings == []

    def test_embed_batch_single_text(self):
        """Test embedding single text in batch."""
        embedder = Embedder()
        embeddings = embedder.embed_batch(["Single text"])

        assert isinstance(embeddings, list)
        assert len(embeddings) == 1
        assert len(embeddings[0]) == 384

    def test_context_manager(self):
        """Test embedder works as context manager."""
        with Embedder() as embedder:
            embedding = embedder.embed_single("Test text")
            assert len(embedding) == 384

    def test_test_connection(self):
        """Test connection test succeeds."""
        embedder = Embedder()
        assert embedder.test_connection() is True

    def test_embeddings_are_different_for_different_texts(self):
        """Test that different texts produce different embeddings."""
        embedder = Embedder()
        emb1 = embedder.embed_single("authentication middleware")
        emb2 = embedder.embed_single("database connection pool")

        assert emb1 != emb2

    def test_embeddings_are_consistent(self):
        """Test that same text produces same embedding."""
        embedder = Embedder()
        text = "consistent text for testing"
        emb1 = embedder.embed_single(text)
        emb2 = embedder.embed_single(text)

        # Embeddings should be very similar (allowing for small floating point differences)
        assert len(emb1) == len(emb2)
        differences = sum(abs(a - b) for a, b in zip(emb1, emb2, strict=True))
        assert differences < 1e-5  # Very small difference threshold

    def test_embed_batch_parallel(self):
        """Test parallel batch embedding."""
        embedder = Embedder()
        texts = [f"Test sentence number {i}" for i in range(100)]
        embeddings = embedder.embed_batch_parallel(texts)

        assert isinstance(embeddings, list)
        assert len(embeddings) == 100
        assert all(len(emb) == 384 for emb in embeddings)
        assert all(isinstance(val, float) for emb in embeddings for val in emb)

    def test_embed_batch_parallel_empty(self):
        """Test parallel embedding with empty list."""
        embedder = Embedder()
        embeddings = embedder.embed_batch_parallel([])
        assert embeddings == []

    def test_embed_batch_parallel_single(self):
        """Test parallel embedding with single text."""
        embedder = Embedder()
        embeddings = embedder.embed_batch_parallel(["Single text"])
        assert len(embeddings) == 1
        assert len(embeddings[0]) == 384

    def test_embed_batch_parallel_matches_serial(self):
        """Test parallel and serial embedding produce same results."""
        embedder = Embedder()
        texts = ["First text", "Second text", "Third text"]

        serial_embeddings = embedder.embed_batch(texts)
        parallel_embeddings = embedder.embed_batch_parallel(texts)

        assert len(serial_embeddings) == len(parallel_embeddings)
        for serial, parallel in zip(serial_embeddings, parallel_embeddings, strict=True):
            differences = sum(abs(a - b) for a, b in zip(serial, parallel, strict=True))
            assert differences < 1e-5  # Should be essentially identical

    def test_gpu_detection(self):
        """Test GPU detection sets device attribute."""
        embedder = Embedder()
        assert hasattr(embedder, "device")
        assert embedder.device in ["cpu", "cuda", "mps"]  # mps = Apple Silicon GPU


class TestModuleFunctions:
    """Test module-level convenience functions."""

    def test_get_embedder(self):
        """Test get_embedder returns singleton."""
        embedder1 = get_embedder()
        embedder2 = get_embedder()
        assert embedder1 is embedder2  # Same instance

    def test_embed_function(self):
        """Test module-level embed function."""
        embedding = embed("test text")
        assert isinstance(embedding, list)
        assert len(embedding) == 384

    def test_embed_batch_function(self):
        """Test module-level embed_batch function."""
        texts = ["text 1", "text 2"]
        embeddings = embed_batch(texts)
        assert len(embeddings) == 2
        assert all(len(emb) == 384 for emb in embeddings)
