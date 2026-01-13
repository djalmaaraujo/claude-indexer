"""
Configuration settings for the semantic code search system.
"""

import os
from pathlib import Path
from typing import Set

# ===================================================================
# EMBEDDING MODEL CONFIGURATION
# ===================================================================
# Choose your embedding model based on your needs:
#
# Option 1: all-MiniLM-L6-v2 (DEFAULT - Recommended for most users)
#   - Speed: FAST (30ms per embedding)
#   - Quality: Good
#   - Size: 90MB
#   - Dimensions: 384
#   - Best for: General code search, fast indexing
#
# Option 2: microsoft/codebert-base (Code-specific model)
#   - Speed: Medium (45ms per embedding)
#   - Quality: Better for code understanding
#   - Size: 500MB
#   - Dimensions: 768
#   - Best for: Better code semantics, willing to trade speed
#
# Option 3: all-mpnet-base-v2 (High quality general model)
#   - Speed: Medium (45ms per embedding)
#   - Quality: Excellent
#   - Size: 420MB
#   - Dimensions: 768
#   - Best for: Best overall quality, not code-specific
# ===================================================================

ST_MODEL = os.environ.get("CODE_SEARCH_MODEL", "all-MiniLM-L6-v2")

# Model dimensions mapping
MODEL_DIMENSIONS = {
    "all-MiniLM-L6-v2": 384,
    "all-mpnet-base-v2": 768,
    "microsoft/codebert-base": 768,
}

# Get embedding dimensions for the selected model
EMBEDDING_DIM = MODEL_DIMENSIONS.get(ST_MODEL, 384)
EMBEDDING_MODEL = ST_MODEL

# Chunking settings
CHUNK_SIZE = 1500  # characters
CHUNK_OVERLAP = 200  # characters for context preservation
MIN_CHUNK_SIZE = 100  # minimum chunk size to index

# Search settings
DEFAULT_TOP_K = 5
MAX_TOP_K = 50

# Index storage
INDEX_DIR = Path.home() / ".code-search" / "indexes"
INDEX_DIR.mkdir(parents=True, exist_ok=True)

# Performance settings
MAX_WORKERS = os.cpu_count() or 4  # for parallel processing
CACHE_SIZE = 1000  # LRU cache size for file reads

# File filtering
CODE_EXTENSIONS: Set[str] = {
    # Python
    ".py",
    ".pyw",
    ".pyx",
    ".pyi",
    # JavaScript/TypeScript
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".mjs",
    ".cjs",
    # Web
    ".html",
    ".htm",
    ".css",
    ".scss",
    ".sass",
    ".less",
    ".vue",
    ".svelte",
    # Ruby
    ".rb",
    ".rake",
    ".gemspec",
    # Go
    ".go",
    # Rust
    ".rs",
    # Java/Kotlin
    ".java",
    ".kt",
    ".kts",
    # C/C++
    ".c",
    ".cpp",
    ".cc",
    ".cxx",
    ".h",
    ".hpp",
    ".hxx",
    # C#
    ".cs",
    # PHP
    ".php",
    # Swift
    ".swift",
    # Shell
    ".sh",
    ".bash",
    ".zsh",
    ".fish",
    # Config/Data
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".xml",
    ".env",
    ".env.local",
    ".env.production",
    # Documentation
    ".md",
    ".rst",
    ".txt",
    # SQL
    ".sql",
}

SKIP_DIRS: Set[str] = {
    # Version control
    ".git",
    ".svn",
    ".hg",
    ".bzr",
    # Dependencies
    "node_modules",
    "bower_components",
    "vendor",
    "vendors",
    # Python
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "venv",
    "env",
    ".venv",
    ".env",
    ".tox",
    "eggs",
    ".eggs",
    "dist",
    "build",
    "*.egg-info",
    # Ruby
    ".bundle",
    # IDE
    ".vscode",
    ".idea",
    ".vs",
    # Build outputs
    "out",
    "target",
    # Caches
    ".cache",
    ".parcel-cache",
    ".next",
    ".nuxt",
    # OS
    ".DS_Store",
    "Thumbs.db",
    # Misc
    "coverage",
    ".coverage",
    "htmlcov",
    ".angular",
    ".gradle",
}

SKIP_FILES: Set[str] = {
    ".DS_Store",
    "Thumbs.db",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "Gemfile.lock",
    "Cargo.lock",
    "poetry.lock",
}

# Binary/large file size limits
MAX_FILE_SIZE = 1_000_000  # 1MB - skip files larger than this

# Incremental indexing
USE_INCREMENTAL = True  # enable incremental updates
HASH_ALGORITHM = "md5"  # for file change detection

# Search result formatting
RESULT_CONTEXT_LINES = 3  # lines to show before/after match

# Vector search settings
VECTOR_SEARCH_METRIC = "cosine"  # similarity metric
VECTOR_SEARCH_NPROBES = 10  # number of probes for search (speed/accuracy tradeoff)

# CLI output
ENABLE_PROGRESS_BAR = True
ENABLE_COLOR_OUTPUT = True

# Debug settings
DEBUG = os.getenv("DEBUG", "").lower() in ("1", "true", "yes")
VERBOSE = os.getenv("VERBOSE", "").lower() in ("1", "true", "yes")


def get_project_hash(project_path: Path) -> str:
    """Generate a unique hash for a project path."""
    import hashlib

    normalized_path = str(project_path.resolve())
    return hashlib.md5(normalized_path.encode()).hexdigest()[:16]


def get_index_path(project_path: Path) -> Path:
    """Get the index directory path for a project."""
    project_hash = get_project_hash(project_path)
    index_path = INDEX_DIR / project_hash
    index_path.mkdir(parents=True, exist_ok=True)
    return index_path


def is_code_file(file_path: Path) -> bool:
    """Check if a file should be indexed."""
    # Check extension
    if file_path.suffix.lower() not in CODE_EXTENSIONS:
        return False

    # Check filename
    if file_path.name in SKIP_FILES:
        return False

    # Check if any parent directory should be skipped
    for parent in file_path.parents:
        if parent.name in SKIP_DIRS:
            return False

    # Check file size
    try:
        if file_path.stat().st_size > MAX_FILE_SIZE:
            return False
    except (OSError, FileNotFoundError):
        return False

    return True


def should_skip_dir(dir_path: Path) -> bool:
    """Check if a directory should be skipped."""
    return dir_path.name in SKIP_DIRS
