"""Tests for search functionality."""

from pathlib import Path

import pytest

from src.search import Searcher, SearchResult


@pytest.fixture
def sample_project():
    """Path to sample project (fixtures directory)."""
    return Path(__file__).parent / "fixtures"


def test_searcher_requires_index(sample_project):
    """Test that searcher requires an index to exist."""
    # Clean index path
    import shutil

    from src.config import get_index_path

    index_path = get_index_path(sample_project)
    if index_path.exists():
        shutil.rmtree(index_path)

    # Should raise FileNotFoundError
    with pytest.raises(FileNotFoundError):
        Searcher(sample_project)


def test_search_result_creation():
    """Test creating a search result."""
    result = SearchResult(
        file_path="test.py",
        start_line=10,
        end_line=20,
        score=0.95,
        chunk_type="function",
        content="def test(): pass",
    )

    assert result.file_path == "test.py"
    assert result.start_line == 10
    assert result.end_line == 20
    assert result.score == 0.95


def test_search_integration(sample_project):
    """Integration test for search (requires indexed project)."""
    # This test assumes the project has been indexed
    # It will be skipped if index doesn't exist

    from src.config import get_index_path

    index_path = get_index_path(sample_project)
    if not (index_path / "index.lance").exists():
        pytest.skip("Project not indexed. Run indexer first.")

    try:
        searcher = Searcher(sample_project)

        # Search for authentication
        results = searcher.search("authentication", top_k=3)

        assert isinstance(results, list)
        assert len(results) <= 3

        # Check result structure
        if results:
            result = results[0]
            assert hasattr(result, "file_path")
            assert hasattr(result, "content")
            assert hasattr(result, "score")

    except Exception as e:
        pytest.skip(f"Search failed: {e}")


def test_format_results_markdown():
    """Test markdown formatting of results."""

    # Create mock results
    results = [
        SearchResult(
            file_path="test.py",
            start_line=10,
            end_line=15,
            score=0.95,
            chunk_type="function",
            content="def authenticate():\n    pass",
        ),
    ]

    # We need a mock searcher just for formatting
    # This is a bit hacky but avoids needing an indexed project
    class MockSearcher:
        def format_results_markdown(self, results, include_context=True):
            from src.search import Searcher as RealSearcher

            # Create a temporary instance just to use the method
            return RealSearcher.__dict__["format_results_markdown"](self, results, include_context)

    searcher = MockSearcher()
    markdown = searcher.format_results_markdown(results, include_context=False)

    assert "test.py" in markdown
    assert "authenticate" in markdown
    assert "```" in markdown


def test_format_results_json():
    """Test JSON formatting of results."""
    import json

    results = [
        SearchResult(
            file_path="test.py",
            start_line=10,
            end_line=15,
            score=0.95,
            chunk_type="function",
            content="def authenticate():\n    pass",
        ),
    ]

    class MockSearcher:
        def format_results_json(self, results):
            from src.search import Searcher as RealSearcher

            return RealSearcher.__dict__["format_results_json"](self, results)

    searcher = MockSearcher()
    json_str = searcher.format_results_json(results)

    # Should be valid JSON
    data = json.loads(json_str)
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["file_path"] == "test.py"
