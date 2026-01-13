"""Tests for code chunking functionality."""

from pathlib import Path

import pytest

from src.chunker import Chunker, chunk_file


@pytest.fixture
def chunker():
    """Create a chunker instance."""
    return Chunker()


@pytest.fixture
def sample_python_file():
    """Path to sample Python file."""
    return Path(__file__).parent / "fixtures" / "sample.py"


def test_chunk_python_file(chunker, sample_python_file):
    """Test chunking a Python file."""
    chunks = chunker.chunk_file(sample_python_file)

    # Should create multiple chunks
    assert len(chunks) > 0

    # Check that we have different chunk types
    chunk_types = {chunk.chunk_type for chunk in chunks}
    assert "function" in chunk_types or "class" in chunk_types or "method" in chunk_types

    # Verify chunks have required fields
    for chunk in chunks:
        assert chunk.content
        assert chunk.file_path
        assert chunk.start_line > 0
        assert chunk.end_line >= chunk.start_line
        assert chunk.chunk_type in ["function", "class", "method", "block", "raw"]


def test_chunk_preserves_imports(chunker, sample_python_file):
    """Test that import context is preserved."""
    chunks = chunker.chunk_file(sample_python_file)

    # At least one chunk should have import context
    has_context = any(chunk.context for chunk in chunks)
    assert has_context


def test_chunk_line_numbers(chunker, sample_python_file):
    """Test that line numbers are accurate."""
    chunks = chunker.chunk_file(sample_python_file)

    # Read the actual file
    content = sample_python_file.read_text()
    lines = content.split("\n")

    # Verify each chunk's line numbers match the content
    for chunk in chunks:
        # Extract lines from the file
        chunk_lines = lines[chunk.start_line - 1 : chunk.end_line]
        actual_content = "\n".join(chunk_lines)

        # The chunk content should be a substring or match the actual content
        # (allowing for some whitespace differences)
        assert chunk.content.strip() in actual_content or actual_content in chunk.content


def test_chunk_function_detection(chunker, sample_python_file):
    """Test that functions are correctly detected."""
    chunks = chunker.chunk_file(sample_python_file)

    # Should find the authenticate_user function
    auth_chunks = [c for c in chunks if "authenticate_user" in c.content]
    assert len(auth_chunks) > 0

    # Should find the calculate_total function
    calc_chunks = [c for c in chunks if "calculate_total" in c.content]
    assert len(calc_chunks) > 0


def test_chunk_class_detection(chunker, sample_python_file):
    """Test that classes are correctly detected."""
    chunks = chunker.chunk_file(sample_python_file)

    # Should find the UserManager class
    class_chunks = [c for c in chunks if "UserManager" in c.content]
    assert len(class_chunks) > 0


def test_chunk_file_convenience_function(sample_python_file):
    """Test the module-level convenience function."""
    chunks = chunk_file(sample_python_file)
    assert len(chunks) > 0


def test_chunk_nonexistent_file(chunker):
    """Test chunking a nonexistent file."""
    chunks = chunker.chunk_file(Path("/nonexistent/file.py"))
    assert len(chunks) == 0


def test_chunk_empty_file(chunker, tmp_path):
    """Test chunking an empty file."""
    empty_file = tmp_path / "empty.py"
    empty_file.write_text("")

    chunks = chunker.chunk_file(empty_file)
    assert len(chunks) == 0


def test_chunk_min_size(chunker, tmp_path):
    """Test that very small chunks are filtered out."""
    tiny_file = tmp_path / "tiny.py"
    tiny_file.write_text("x = 1")

    chunks = chunker.chunk_file(tiny_file)

    # Should be empty or minimal since it's below MIN_CHUNK_SIZE
    assert len(chunks) <= 1
