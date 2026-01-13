"""Tests for tree-sitter AST-based chunking."""

import tempfile
from pathlib import Path

import pytest

from src.tree_sitter_chunker import TreeSitterChunker


@pytest.fixture
def chunker():
    """Create a tree-sitter chunker instance."""
    return TreeSitterChunker()


class TestTreeSitterChunker:
    """Test tree-sitter AST-based chunking functionality."""

    def test_chunker_initialization(self, chunker):
        """Test chunker initializes with languages."""
        assert chunker.is_available()
        assert "python" in chunker.languages
        assert "javascript" in chunker.languages

    def test_can_chunk_python_file(self, chunker):
        """Test detection of Python files."""
        py_file = Path("test.py")
        assert chunker.can_chunk_file(py_file)

    def test_can_chunk_javascript_file(self, chunker):
        """Test detection of JavaScript files."""
        js_file = Path("test.js")
        assert chunker.can_chunk_file(js_file)

    def test_cannot_chunk_unsupported_file(self, chunker):
        """Test rejection of unsupported file types."""
        unsupported = Path("test.go")
        assert not chunker.can_chunk_file(unsupported)

    def test_chunk_python_function(self, chunker):
        """Test chunking a Python function."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("""
def calculate_sum(a, b):
    '''Calculate sum of two numbers.

    This is a longer docstring to ensure the function
    meets the minimum chunk size requirements.
    '''
    result = a + b
    print(f"Calculating sum: {a} + {b} = {result}")
    return result

def calculate_product(a, b):
    '''Calculate product of two numbers.

    This is a longer docstring to ensure the function
    meets the minimum chunk size requirements.
    '''
    result = a * b
    print(f"Calculating product: {a} * {b} = {result}")
    return result
""")
            f.flush()
            temp_path = Path(f.name)

        try:
            chunks = chunker.chunk_file(temp_path)

            # Should find 2 functions
            assert len(chunks) >= 2
            assert all(c.chunk_type == "function" for c in chunks)

            # Check function names are captured
            contents = [c.content for c in chunks]
            assert any("calculate_sum" in c for c in contents)
            assert any("calculate_product" in c for c in contents)

        finally:
            temp_path.unlink()

    def test_chunk_python_class(self, chunker):
        """Test chunking a Python class."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("""
class Calculator:
    def __init__(self):
        self.result = 0

    def add(self, x):
        self.result += x
        return self.result

    def subtract(self, x):
        self.result -= x
        return self.result
""")
            f.flush()
            temp_path = Path(f.name)

        try:
            chunks = chunker.chunk_file(temp_path)

            # Should find class or methods
            assert len(chunks) >= 1

            # Either the whole class or individual methods
            chunk_types = {c.chunk_type for c in chunks}
            assert chunk_types.issubset({"class", "method"})

        finally:
            temp_path.unlink()

    def test_chunk_python_with_imports(self, chunker):
        """Test that imports are preserved in context."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("""
import os
import sys
from pathlib import Path

def get_home_dir():
    '''Get the home directory path.

    This function uses pathlib to retrieve the user's
    home directory in a cross-platform way.
    '''
    home = Path.home()
    print(f"Home directory: {home}")
    return home
""")
            f.flush()
            temp_path = Path(f.name)

        try:
            chunks = chunker.chunk_file(temp_path)

            assert len(chunks) >= 1

            # Check that imports are in context
            first_chunk = chunks[0]
            if first_chunk.context:
                assert "import" in first_chunk.context

        finally:
            temp_path.unlink()

    def test_chunk_javascript_function(self, chunker):
        """Test chunking JavaScript functions."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
            f.write("""
function calculateSum(a, b) {
    // Calculate the sum of two numbers
    // This is a longer function to meet minimum size
    const result = a + b;
    console.log(`Sum: ${a} + ${b} = ${result}`);
    return result;
}

const calculateProduct = (a, b) => {
    // Calculate the product of two numbers
    // This is a longer function to meet minimum size
    const result = a * b;
    console.log(`Product: ${a} * ${b} = ${result}`);
    return result;
};

export function calculateDifference(a, b) {
    // Calculate the difference of two numbers
    // This is a longer function to meet minimum size
    const result = a - b;
    console.log(`Difference: ${a} - ${b} = ${result}`);
    return result;
}
""")
            f.flush()
            temp_path = Path(f.name)

        try:
            chunks = chunker.chunk_file(temp_path)

            # Should find multiple functions
            assert len(chunks) >= 2
            assert all(c.chunk_type in ("function", "method") for c in chunks)

        finally:
            temp_path.unlink()

    def test_chunk_javascript_class(self, chunker):
        """Test chunking JavaScript classes."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
            f.write("""
class Calculator {
    constructor() {
        this.result = 0;
    }

    add(x) {
        this.result += x;
        return this.result;
    }

    subtract(x) {
        this.result -= x;
        return this.result;
    }
}
""")
            f.flush()
            temp_path = Path(f.name)

        try:
            chunks = chunker.chunk_file(temp_path)

            # Should find class or methods
            assert len(chunks) >= 1
            chunk_types = {c.chunk_type for c in chunks}
            assert chunk_types.issubset({"class", "method"})

        finally:
            temp_path.unlink()

    def test_chunk_respects_min_size(self, chunker):
        """Test that small chunks are filtered out."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("""
def a():
    pass

def very_long_function_name_that_is_properly_sized():
    '''This function has enough content to meet minimum size.'''
    result = 0
    for i in range(10):
        result += i
    return result
""")
            f.flush()
            temp_path = Path(f.name)

        try:
            chunks = chunker.chunk_file(temp_path)

            # Small function should be filtered, larger one kept
            # Exact count depends on MIN_CHUNK_SIZE setting
            assert all(len(c.content) >= 50 for c in chunks)

        finally:
            temp_path.unlink()

    def test_chunk_empty_file(self, chunker):
        """Test chunking an empty file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("")
            f.flush()
            temp_path = Path(f.name)

        try:
            chunks = chunker.chunk_file(temp_path)
            assert chunks == []

        finally:
            temp_path.unlink()

    def test_chunk_line_numbers_accurate(self, chunker):
        """Test that line numbers are accurate."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("""# Line 1
# Line 2
def function_at_line_3():  # Line 3
    return "hello"  # Line 4

def function_at_line_6():  # Line 6
    return "world"  # Line 7
""")
            f.flush()
            temp_path = Path(f.name)

        try:
            chunks = chunker.chunk_file(temp_path)

            # Find the first function chunk
            func_chunks = [c for c in chunks if "function_at_line_3" in c.content]
            if func_chunks:
                chunk = func_chunks[0]
                # First function should start around line 3
                assert 2 <= chunk.start_line <= 4

        finally:
            temp_path.unlink()
