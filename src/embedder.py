"""
Fast embedding generation using sentence-transformers.
"""
import time
from typing import List
from sentence_transformers import SentenceTransformer
from src.config import ST_MODEL, DEBUG


class Embedder:
    """Fast embedding generator using sentence-transformers."""

    def __init__(self):
        print(f"Loading sentence-transformers model: {ST_MODEL}")
        self.model = SentenceTransformer(ST_MODEL)
        print(f"✓ Model loaded")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def embed_single(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            List of float values representing the embedding vector
        """
        start_time = time.time()

        embedding = self.model.encode(text, convert_to_numpy=True)

        if DEBUG:
            elapsed = (time.time() - start_time) * 1000
            print(f"[Embedder] Embedding: {elapsed:.1f}ms")

        return embedding.tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts efficiently.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        if len(texts) == 1:
            return [self.embed_single(texts[0])]

        start_time = time.time()

        # sentence-transformers handles batching efficiently
        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True,
            show_progress_bar=False,
            batch_size=32,  # Process 32 at a time
        )

        if DEBUG:
            elapsed = (time.time() - start_time) * 1000
            avg_per_text = elapsed / len(texts)
            print(f"[Embedder] Batch of {len(texts)}: {elapsed:.1f}ms ({avg_per_text:.1f}ms/text)")

        return [emb.tolist() for emb in embeddings]

    def test_connection(self) -> bool:
        """
        Test if the embedder is working.

        Returns:
            True if model is loaded successfully
        """
        try:
            # Try a simple embedding
            test_emb = self.model.encode("test", convert_to_numpy=True)
            return len(test_emb) > 0
        except Exception as e:
            print(f"Embedder test failed: {e}")
            return False


# Module-level convenience functions
_default_embedder = None


def get_embedder() -> Embedder:
    """Get or create the default embedder instance."""
    global _default_embedder
    if _default_embedder is None:
        _default_embedder = Embedder()
    return _default_embedder


def embed(text: str) -> List[float]:
    """
    Convenience function to embed a single text.

    Args:
        text: Text to embed

    Returns:
        Embedding vector
    """
    embedder = get_embedder()
    return embedder.embed_single(text)


def embed_batch(texts: List[str]) -> List[List[float]]:
    """
    Convenience function to embed multiple texts.

    Args:
        texts: List of texts to embed

    Returns:
        List of embedding vectors
    """
    embedder = get_embedder()
    return embedder.embed_batch(texts)


def test_connection() -> bool:
    """
    Convenience function to test embedder.

    Returns:
        True if model is loaded successfully
    """
    embedder = get_embedder()
    return embedder.test_connection()
