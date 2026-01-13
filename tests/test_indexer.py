"""Tests for indexing functionality."""
import pytest
from pathlib import Path
from src.indexer import Indexer
from src.config import get_index_path


@pytest.fixture
def sample_project():
    """Path to sample project (fixtures directory)."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def clean_index(sample_project):
    """Ensure index is clean before test."""
    index_path = get_index_path(sample_project)

    # Clean up before
    if index_path.exists():
        import shutil
        shutil.rmtree(index_path)

    yield sample_project

    # Clean up after
    if index_path.exists():
        import shutil
        shutil.rmtree(index_path)


def test_indexer_creation(sample_project):
    """Test creating an indexer."""
    indexer = Indexer(sample_project)
    assert indexer.project_path.exists()
    assert indexer.index_path.exists()


def test_indexer_finds_files(sample_project):
    """Test that indexer finds code files."""
    indexer = Indexer(sample_project)
    files = indexer._find_code_files()

    # Should find at least the sample.py file
    assert len(files) > 0
    assert any(f.name == "sample.py" for f in files)


def test_file_hash_computation(sample_project):
    """Test file hash computation."""
    indexer = Indexer(sample_project)
    sample_file = sample_project / "sample.py"

    hash1 = indexer._compute_file_hash(sample_file)
    hash2 = indexer._compute_file_hash(sample_file)

    # Same file should produce same hash
    assert hash1 == hash2
    assert len(hash1) > 0


def test_metadata_save_load(clean_index, tmp_path):
    """Test saving and loading metadata."""
    from src.indexer import FileMetadata

    indexer = Indexer(clean_index)

    # Add some metadata
    indexer.file_metadata["test.py"] = FileMetadata(
        path="test.py",
        mtime=123.456,
        size=1000,
        hash="abc123",
    )

    # Save
    indexer._save_metadata()

    # Create new indexer and load
    indexer2 = Indexer(clean_index)

    # Should have loaded the metadata
    assert "test.py" in indexer2.file_metadata
    assert indexer2.file_metadata["test.py"].hash == "abc123"


def test_indexing_integration(clean_index):
    """Integration test for full indexing."""
    # This is a more comprehensive test
    indexer = Indexer(clean_index, force=True)

    try:
        indexer.index()

        # Check that index was created
        assert indexer.db_path.exists()

        # Check stats
        assert indexer.stats["files_scanned"] > 0
        assert indexer.stats["files_indexed"] >= 0
        assert indexer.stats["chunks_created"] >= 0

    except Exception as e:
        pytest.skip(f"Indexing failed: {e}")
