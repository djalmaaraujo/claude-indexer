# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Overview

A **local RAG-based semantic code search system** with MCP integration for Claude Code. Pre-indexes codebases for instant semantic search (<100ms, ~65ms average). Uses sentence-transformers for embeddings and LanceDB for vector storage - no external services required.

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

### CLI Usage
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

2. **chunker.py** + **tree_sitter_chunker.py** - Code splitting
   - Tree-sitter AST parsing for Python, JavaScript, TypeScript
   - Regex fallback for other languages
   - Returns `CodeChunk` dataclass with file_path, start_line, end_line, chunk_type, context

3. **embedder.py** - Embedding generation
   - sentence-transformers (local, 384-dim)
   - GPU auto-detection (CUDA/MPS)
   - Batch processing with caching

4. **indexer.py** - Parallel indexing
   - `ProcessPoolExecutor` with `MAX_WORKERS = cpu_count()`
   - Three-tier change detection (mtime → size → hash)
   - Stores metadata in `metadata.json`

5. **search.py** - Semantic search
   - Vector search finds chunks, reads fresh file content from disk
   - Cosine similarity in LanceDB
   - Returns `SearchResult` with file paths, line numbers, scores

### MCP Server

**Location**: `mcp-server/server.py`

Exposes three tools for Claude Code:
- `search_code(query, num_results)` - Semantic search, returns up to 3000 chars per result
- `get_index_status()` - Check if index exists
- `reindex_project(force)` - Trigger indexing

**Registration**: Project-level `.mcp.json` or via `claude-integration/install.sh`

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

## Key Design Decisions

### Fresh Content Reads
Vector DB stores only embeddings and metadata. Actual code is read from disk at search time:
- No stale search results
- Smaller index size
- Incremental updates without full re-indexing

### MCP Content Size
`search_code` returns up to 3000 chars per result to reduce follow-up Read() calls while keeping responses reasonable.

### Index Storage
`~/.code-search/indexes/{project_hash}/` where `project_hash = md5(absolute_path)[:16]`

## Configuration

Key parameters in `src/config.py`:
- `CHUNK_SIZE = 1500` - Maximum chunk size
- `CHUNK_OVERLAP = 200` - Overlap between chunks
- `DEFAULT_TOP_K = 5` - Default search results
- `MAX_WORKERS = cpu_count()` - Parallel workers
- `CODE_EXTENSIONS` - File extensions to index
- `SKIP_DIRS` - Directories to skip

## File Locations

```
src/
├── config.py                 # Settings
├── embedder.py               # Embedding generation
├── embedding_cache.py        # Content-hash caching
├── chunker.py                # Regex chunking (fallback)
├── tree_sitter_chunker.py    # AST chunking (Python, JS, TS)
├── indexer.py                # Parallel indexing
└── search.py                 # Vector search

mcp-server/
└── server.py                 # MCP server for Claude Code

claude-integration/
├── hooks/auto-index.sh       # SessionStart hook
└── install.sh                # MCP installer

bin/
├── code-index                # Indexing CLI
├── ss                        # Search CLI
└── cc                        # Search + Claude CLI
```

## Working with the Codebase

### Adding Language Support
1. Add tree-sitter grammar to `tree_sitter_chunker.py` or regex patterns to `chunker.py`
2. Add file extensions to `CODE_EXTENSIONS` in `config.py`
3. Add tests in `tests/`

### Modifying MCP Server
Edit `mcp-server/server.py`:
- Tools are defined with `@mcp.tool()` decorator
- Returns JSON strings
- Uses `Searcher` and `Indexer` classes from `src/`

## Performance Targets

- Query embedding: <50ms
- Vector search: <20ms
- File read: <30ms
- **Total search: <100ms** (achieves ~65ms)
- Index 1k files: <60s

## Troubleshooting

**Slow first search**: Embedding model loads on first use (~2s)

**Index not found**: Run `code-index .` in project directory

**MCP not available**: Restart Claude Code after `install.sh`

**Out of memory**: Reduce `MAX_WORKERS` in `src/config.py`
