# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **local RAG-based semantic code search system** that beats Cursor's performance by pre-indexing codebases and enabling instant semantic search (<100ms, averaging ~65ms). It uses sentence-transformers for embeddings (no external services required) and LanceDB for vector storage.

**Key Achievement**: Semantic code search with fresh file content at search time, enabling incremental updates without full re-indexing.

## Development Commands

### Setup
```bash
./setup.sh                    # One-time setup: installs dependencies, creates symlinks
source venv/bin/activate      # Activate virtual environment
pip install -e .              # Install in editable mode
```

### Testing
```bash
pytest tests/                 # Run all tests
pytest tests/test_chunker.py  # Run specific test file
pytest -v                     # Verbose output
pytest -k "test_name"         # Run tests matching pattern
pytest --cov=src              # With coverage
```

### Code Quality
```bash
black src/ tests/             # Format code (100 char line length)
ruff check src/ tests/        # Lint code
mypy src/                     # Type checking
```

### Benchmarking
```bash
./benchmark.py                # Benchmark current directory
./benchmark.py /path/to/proj  # Benchmark specific project
```

### CLI Usage (after setup)
```bash
code-index .                  # Index current directory (incremental)
code-index . --force          # Force full re-index
ss "query" -n 10              # Semantic search (10 results)
ss "query" --json             # JSON output
cc "query"                    # Search and send to Claude Code
```

## Architecture

### Core Components

**Pipeline**: Files → Chunker → Embedder → Vector DB → Searcher

1. **config.py** - Central configuration
   - Embedding model: `all-MiniLM-L6-v2` (384-dim, sentence-transformers)
   - Chunking: 1500 chars with 200 char overlap
   - Index storage: `~/.code-search/indexes/{project_hash}/`
   - Supported file extensions and skip patterns

2. **chunker.py** - AST-aware code splitting
   - **Python**: Regex-based extraction of classes, methods, functions with import context
   - **JavaScript/TypeScript**: Pattern matching for functions, classes, arrow functions
   - **Ruby**: Class and method extraction with `end` matching
   - **Fallback**: Line-based chunking with overlap for unsupported languages
   - Returns `CodeChunk` dataclass with file_path, start_line, end_line, chunk_type, context

3. **embedder.py** - Dual backend embedding generation
   - **Default**: sentence-transformers (local, no server, 384-dim)
   - **Optional**: Ollama backend (768-dim, requires service)
   - Batch processing with connection pooling
   - Switch via `EMBEDDING_BACKEND` environment variable

4. **indexer.py** - Parallel indexing with incremental updates
   - Uses `ProcessPoolExecutor` with `MAX_WORKERS = cpu_count()`
   - **Incremental logic**: Three-tier change detection (mtime → size → hash)
   - Stores metadata in `metadata.json` alongside vector DB
   - LanceDB schema: `id, file_path, start_line, end_line, chunk_type, context, content, vector`

5. **search.py** - Fast semantic search with fresh content
   - **Critical design**: Vector search finds chunks, then reads fresh file content from disk
   - This enables incremental updates without stale results
   - Cosine similarity search in LanceDB
   - Returns `SearchResult` with file paths, line numbers, scores, content

### Data Flow

**Indexing**:
```
Files → filter by extension → ProcessPoolExecutor (parallel chunking)
→ batch embedding generation → LanceDB storage → metadata.json
```

**Searching**:
```
Query → embed (< 50ms) → LanceDB vector search (< 20ms)
→ read fresh file content (< 30ms) → return results (total: ~65ms)
```

**Incremental Updates**:
```
Check metadata.json → compare mtime/size/hash → only re-process changed files
→ append new chunks to LanceDB → update metadata.json
```

## Key Design Decisions

### Why Fresh Content Reads?
Vector DB only stores embeddings and metadata (file_path, line numbers). Actual code is read from disk at search time. This enables:
- No stale search results
- Smaller index size
- Incremental updates without full re-indexing

### Why sentence-transformers as Default?
- No external service required (Ollama needs separate installation)
- Pure Python, works immediately after `pip install`
- 384-dim vectors: good quality with better performance than 768-dim
- Lower memory footprint

### Index Storage Location
`~/.code-search/indexes/{project_hash}/` where `project_hash = md5(absolute_path)[:16]`
- Enables multi-project support
- Each project gets isolated storage
- Indexes persist across sessions

## Configuration

All tunable parameters in `src/config.py`:
- `CHUNK_SIZE = 1500` - Maximum chunk size in characters
- `CHUNK_OVERLAP = 200` - Overlap between chunks for context
- `DEFAULT_TOP_K = 5` - Default number of search results
- `MAX_WORKERS = cpu_count()` - Parallel processing workers
- `CODE_EXTENSIONS` - Set of file extensions to index
- `SKIP_DIRS` - Directories to skip (node_modules, venv, .git, etc.)

## CLI Binaries

Located in `bin/`:
- `code-index` - Indexing CLI (calls `src/indexer.py`)
- `ss` - Search CLI (calls `src/search.py`)
- `cc` - Search + Claude integration
- `ss-benchmark` / `cc-benchmark` - Performance testing

These are symlinked to `~/bin/` by `setup.sh` for global access.

## Future Integration: Claude Code Plugin (planned-future-implementation.md)

A comprehensive plan exists for deep Claude Code integration:
- **SessionStart Hook**: Auto-index on session start (background, non-blocking)
- **MCP Server**: Expose semantic search as tools Claude can call automatically
- **Skill**: Automatic recognition of "find X" / "where is X" queries
- **Slash Commands**: `/search`, `/reindex`, `/index-status`

Estimated effort: 4-6 hours. See `planned-future-implementation.md` for full checklist.

## Performance Targets

- Query embedding: <50ms ✅
- Vector search: <20ms ✅
- File read: <30ms ✅
- **Total search: <100ms ✅** (achieves ~65ms)
- Index 1k files: <60s ✅

## Working with the Codebase

### Adding New Language Support
Edit `src/chunker.py`:
1. Add regex patterns for language constructs (classes, functions, etc.)
2. Implement language-specific chunking method (e.g., `_chunk_rust()`)
3. Add file extensions to `CODE_EXTENSIONS` in `src/config.py`
4. Add tests in `tests/test_chunker.py`

### Modifying Embedding Backend
Edit `src/embedder.py`:
1. Implement new backend in `_init_*()` and `_embed_*()` methods
2. Update `EMBEDDING_BACKEND` options in `src/config.py`
3. Update `EMBEDDING_DIM` based on model dimensions

### Changing Storage Backend
Currently uses LanceDB. To swap:
1. Modify `src/indexer.py` `_store_in_db()` method
2. Modify `src/search.py` to use new vector search API
3. Update schema in both files to match new backend

## Troubleshooting

**Slow first search**: Embedding model loads on first use (~2s for sentence-transformers)

**Index not found**: Run `code-index .` in project directory

**Out of memory during indexing**: Reduce `MAX_WORKERS` in `src/config.py`

**Wrong search results**: Force re-index with `code-index . --force` (switches backends or fixes corruption)
