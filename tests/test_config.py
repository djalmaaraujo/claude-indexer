"""Tests for the config module."""
import tempfile
from pathlib import Path
import pytest
from src import config


class TestConfiguration:
    """Test cases for configuration settings."""

    def test_embedding_settings(self):
        """Test embedding configuration."""
        assert config.EMBEDDING_DIM == 384
        assert config.EMBEDDING_MODEL == "all-MiniLM-L6-v2"
        assert config.ST_MODEL in ["all-MiniLM-L6-v2", "all-mpnet-base-v2"]

    def test_chunking_settings(self):
        """Test chunking configuration."""
        assert config.CHUNK_SIZE > 0
        assert config.CHUNK_OVERLAP > 0
        assert config.MIN_CHUNK_SIZE > 0
        assert config.CHUNK_OVERLAP < config.CHUNK_SIZE

    def test_search_settings(self):
        """Test search configuration."""
        assert config.DEFAULT_TOP_K > 0
        assert config.MAX_TOP_K >= config.DEFAULT_TOP_K
        assert config.RESULT_CONTEXT_LINES >= 0

    def test_index_dir_exists(self):
        """Test index directory is created."""
        assert config.INDEX_DIR.exists()
        assert config.INDEX_DIR.is_dir()

    def test_performance_settings(self):
        """Test performance configuration."""
        assert config.MAX_WORKERS > 0
        assert config.CACHE_SIZE > 0

    def test_code_extensions(self):
        """Test code extensions configuration."""
        assert isinstance(config.CODE_EXTENSIONS, set)
        assert len(config.CODE_EXTENSIONS) > 0
        assert ".py" in config.CODE_EXTENSIONS
        assert ".js" in config.CODE_EXTENSIONS
        assert ".ts" in config.CODE_EXTENSIONS

    def test_skip_dirs(self):
        """Test skip directories configuration."""
        assert isinstance(config.SKIP_DIRS, set)
        assert "node_modules" in config.SKIP_DIRS
        assert "venv" in config.SKIP_DIRS
        assert ".git" in config.SKIP_DIRS
        assert "__pycache__" in config.SKIP_DIRS

    def test_skip_files(self):
        """Test skip files configuration."""
        assert isinstance(config.SKIP_FILES, set)
        assert "package-lock.json" in config.SKIP_FILES
        assert ".DS_Store" in config.SKIP_FILES


class TestProjectHash:
    """Test project hash generation."""

    def test_get_project_hash(self):
        """Test project hash generation."""
        path = Path("/test/project")
        hash1 = config.get_project_hash(path)

        assert isinstance(hash1, str)
        assert len(hash1) == 16  # MD5 hash truncated to 16 chars

    def test_get_project_hash_consistency(self):
        """Test same path produces same hash."""
        path = Path("/test/project")
        hash1 = config.get_project_hash(path)
        hash2 = config.get_project_hash(path)

        assert hash1 == hash2

    def test_get_project_hash_different_paths(self):
        """Test different paths produce different hashes."""
        path1 = Path("/test/project1")
        path2 = Path("/test/project2")

        hash1 = config.get_project_hash(path1)
        hash2 = config.get_project_hash(path2)

        assert hash1 != hash2


class TestIndexPath:
    """Test index path generation."""

    def test_get_index_path(self):
        """Test index path generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            index_path = config.get_index_path(path)

            assert index_path.exists()
            assert index_path.is_dir()
            assert index_path.parent == config.INDEX_DIR

    def test_get_index_path_creates_directory(self):
        """Test index path is created if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            index_path = config.get_index_path(path)

            assert index_path.exists()


class TestFileFiltering:
    """Test file and directory filtering functions."""

    def test_is_code_file_python(self):
        """Test Python files are recognized as code files."""
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
            f.write(b"# test")
            assert config.is_code_file(Path(f.name)) is True

    def test_is_code_file_javascript(self):
        """Test JavaScript files are recognized as code files."""
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".js", delete=False) as f:
            f.write(b"// test")
            assert config.is_code_file(Path(f.name)) is True

        with tempfile.NamedTemporaryFile(suffix=".ts", delete=False) as f:
            f.write(b"// test")
            assert config.is_code_file(Path(f.name)) is True

    def test_is_code_file_other_extensions(self):
        """Test other code extensions are recognized."""
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".go", delete=False) as f:
            f.write(b"package main")
            assert config.is_code_file(Path(f.name)) is True

    def test_is_code_file_skip_files(self):
        """Test skip files are not recognized as code files."""
        assert config.is_code_file(Path("package-lock.json")) is False
        assert config.is_code_file(Path(".DS_Store")) is False

    def test_is_code_file_wrong_extension(self):
        """Test files with wrong extensions are not code files."""
        assert config.is_code_file(Path("test.txt")) is False
        assert config.is_code_file(Path("image.png")) is False
        assert config.is_code_file(Path("data.csv")) is False

    def test_should_skip_dir(self):
        """Test directories that should be skipped."""
        assert config.should_skip_dir(Path("node_modules")) is True
        assert config.should_skip_dir(Path("venv")) is True
        assert config.should_skip_dir(Path(".git")) is True
        assert config.should_skip_dir(Path("__pycache__")) is True

    def test_should_not_skip_dir(self):
        """Test directories that should not be skipped."""
        assert config.should_skip_dir(Path("src")) is False
        assert config.should_skip_dir(Path("tests")) is False
        assert config.should_skip_dir(Path("lib")) is False

    def test_is_code_file_in_skip_dir(self):
        """Test files in skip directories are not code files."""
        assert config.is_code_file(Path("node_modules/package/index.js")) is False
        assert config.is_code_file(Path("venv/lib/module.py")) is False
        assert config.is_code_file(Path(".git/objects/file")) is False
