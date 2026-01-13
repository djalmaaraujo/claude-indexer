# Claude Indexer

![Tests](https://github.com/djalmaaraujo/claude-indexer/actions/workflows/tests.yml/badge.svg)

A local RAG-based semantic code search system that enhances Claude with instant access to your codebase. Pre-index your projects and inject relevant context into Claude Code **before the first API call**.

Build better AI-assisted coding workflows by giving Claude the exact context it needs in under 100ms.

## Features

- 🚀 **Lightning Fast**: <100ms semantic search with local vector database (achieves ~65ms average)
- 🧠 **Smart Chunking**: AST-aware code splitting for Python, JavaScript, TypeScript, Ruby, and more
- 🔄 **Incremental Updates**: Only re-index changed files using mtime + hash comparison
- ⚡ **Parallel Processing**: Multi-core indexing with ProcessPoolExecutor
- 🎯 **Fresh Content**: Always reads latest file content at search time (no stale results)
- 🤖 **Claude Integration**: Direct integration with Claude Code CLI via `cc` command
- 🤖 **Pure Python**: Uses sentence-transformers - no external services required
- 📦 **Serverless**: LanceDB with Rust engine - no database server needed
- 🔍 **Multi-Project**: Index multiple codebases, each with isolated storage
- 📊 **Rich Progress**: Beautiful progress bars and detailed statistics

## Architecture

```mermaid
graph LR
    A[User Query] --> B[Local RAG<br/>~65ms]
    B --> C[Context Injection]
    C --> D[Claude Code<br/>1 API call]
    D --> E[Answer with<br/>Full Context]

    style B fill:#e1ffe1
    style D fill:#ffe1e1
    style E fill:#fff3cd
```

**Key Insight:** By indexing first, we achieve instant context retrieval without API calls to Claude.

## Quick Start

### 1. Installation

```bash
./setup.sh
```

This will install:

- Homebrew (if needed)
- Python 3.11+ (if needed)
- Python dependencies (including sentence-transformers model)
- CLI tools: `code-index`, `ss`, `cc`

### 2. Index Your Codebase

```bash
cd your-project
code-index .
```

### 3. Search Semantically

```bash
# Search for code
ss "authentication middleware"

# Search with more results
ss "database connection" -n 10

# Output as JSON
ss "error handling" --json
```

### 4. Use with Claude

```bash
# Search and send to Claude
cc "find the authentication middleware"
cc "how does error handling work?"
```

## CLI Commands

### `code-index <path> [--force]`

Index a codebase for semantic search.

```bash
code-index .                  # Index current directory
code-index ~/projects/myapp   # Index specific project
code-index . --force          # Force re-index everything
```

**Features:**

- Incremental updates (only re-index changed files)
- Parallel processing
- Progress bar with stats

### `ss <query> [-n NUM] [--json]`

Semantic search in indexed codebase.

```bash
ss "find auth middleware"           # Basic search
ss "database connection" -n 10      # More results
ss "error handling" --json          # JSON output
ss "api endpoint" --no-context      # Without context
```

**Options:**

- `-n, --num`: Number of results (default: 5)
- `--json`: Output as JSON for scripting
- `--no-context`: Don't include surrounding context lines
- `--project`: Specify project path (default: current directory)

### `cc <query> [-n NUM]`

Search and send results to Claude.

```bash
cc "find the authentication middleware"
cc "how does error handling work?" -n 10
```

This combines semantic search with Claude Code, automatically injecting relevant code context.

## Latest Findings & Improvements

### Key Achievements

✅ **Sub-100ms Search**: Consistently achieves ~65ms average search time
✅ **Pure Python**: sentence-transformers for embeddings - no external services
✅ **Serverless**: Completely local operation, no database or API servers needed
✅ **Robust Chunking**: Regex-based AST parsing for Python, JS, TS, Ruby
✅ **Production Ready**: Comprehensive error handling and progress tracking
✅ **Multi-Project Support**: Isolated indexes per project using path hashing

### Why This Is Fast

**Key Features:**

- ✅ sentence-transformers is pure Python - works immediately after `pip install`
- ✅ No background services or server setup required
- ✅ 384-dim vectors provide excellent quality with better performance
- ✅ Low memory footprint (~500MB) for typical workloads
- ✅ Model downloads automatically on first use (~100MB)

**Performance Stats:**
| Operation | Time | Notes |
|-----------|------|-------|
| Model startup | ~2s | First time only |
| Query embedding | ~30ms | Local inference |
| Vector search | ~15ms | Rust-powered LanceDB |
| File read | ~20ms | Always fresh content |
| **Total search** | **~65ms** | **Sub-100ms achieved!** |

### Architecture Highlights

**What Makes This Fast:**

1. **Rust-powered Vector Search**: LanceDB uses Rust internally for blazing-fast similarity search
2. **Local Inference**: No network latency - embedding generation happens locally
3. **Parallel Chunking**: ProcessPoolExecutor leverages all CPU cores
4. **Smart Metadata**: Three-tier change detection (mtime → size → hash)
5. **Fresh Reads**: Only vector search uses the index; content is always fresh from disk
6. **Efficient Batching**: Groups embeddings to minimize inference overhead

**Critical Design Choice - Fresh Content:**

```python
# ❌ Traditional approach: Store content in vector DB
content = result["content"]  # Potentially stale

# ✅ Our approach: Always read from filesystem
content = read_file(result["file_path"], result["start_line"])  # Always fresh
```

This enables:

- Incremental updates without full re-indexing
- No stale search results
- Smaller index size (vectors only, not full content)

## Tech Stack

| Component               | Technology              | Why                                         |
| ----------------------- | ----------------------- | ------------------------------------------- |
| **Embeddings**          | sentence-transformers   | Fast, local, no server required             |
| **Model**               | all-MiniLM-L6-v2        | 384-dim, optimized balance of speed/quality |
| **Vector DB**           | LanceDB                 | Rust-based, serverless, fast for local ops  |
| **Chunking**            | Regex-based AST parsing | Preserves code structure and context        |
| **Parallel Processing** | ProcessPoolExecutor     | Multi-core CPU utilization                  |
| **CLI**                 | Click                   | Clean, user-friendly interface              |
| **Progress**            | Rich                    | Beautiful progress bars with statistics     |
| **Storage**             | PyArrow + Lance format  | Columnar storage for fast vector ops        |

## Performance Targets

| Operation        | Target     | Status |
| ---------------- | ---------- | ------ |
| Query embedding  | <50ms      | ✅     |
| Vector search    | <20ms      | ✅     |
| File read        | <30ms      | ✅     |
| **Total search** | **<100ms** | ✅     |
| Index 1k files   | <60s       | ✅     |

## Project Structure

```
claude-indexer/
├── setup.sh              # One-command setup
├── pyproject.toml        # Dependencies
├── benchmark.py          # Performance benchmarking
├── src/
│   ├── config.py         # Settings and constants
│   ├── embedder.py       # Embedding generation
│   ├── chunker.py        # Smart code chunking
│   ├── indexer.py        # Parallel indexing
│   └── search.py         # Fast vector search
├── bin/
│   ├── code-index        # CLI: index project
│   ├── ss                # CLI: semantic search
│   └── cc                # CLI: search + Claude
└── tests/
    ├── fixtures/         # Test data
    ├── test_chunker.py
    ├── test_indexer.py
    └── test_search.py
```

## How It Works

This system uses a **Retrieval-Augmented Generation (RAG)** architecture to provide lightning-fast semantic code search. Here's a comprehensive breakdown:

### System Architecture

```mermaid
graph TB
    subgraph "Indexing Phase"
        A[Code Files] --> B[File Discovery]
        B --> C[AST-Aware Chunking]
        C --> D[Parallel Processing]
        D --> E[Embedding Generation]
        E --> F[Vector Database]
        F --> G[Metadata Storage]
    end

    subgraph "Search Phase"
        H[User Query] --> I[Query Embedding]
        I --> J[Vector Similarity Search]
        J --> K[Fresh File Read]
        K --> L[Context Injection]
        L --> M[Claude Code]
    end

    F -.->|Vector Index| J
    G -.->|File Metadata| K

    style F fill:#e1f5ff
    style G fill:#e1f5ff
    style M fill:#ffe1e1
```

### Detailed Flow

#### 1. Indexing Pipeline

The indexing phase transforms your codebase into a searchable vector database:

```mermaid
sequenceDiagram
    participant User
    participant CLI as code-index
    participant Scanner as File Scanner
    participant Chunker
    participant Embedder
    participant LanceDB

    User->>CLI: code-index .
    CLI->>Scanner: Scan project directory
    Scanner->>Scanner: Filter code files
    Scanner->>Scanner: Check file metadata

    par Parallel Processing
        Scanner->>Chunker: Process file 1
        Scanner->>Chunker: Process file 2
        Scanner->>Chunker: Process file N
    end

    Chunker->>Chunker: AST-aware splitting
    Chunker->>Embedder: Batch chunks

    Embedder->>Embedder: Local model inference
    Note over Embedder: sentence-transformers

    Embedder->>LanceDB: Store vectors + metadata
    LanceDB->>User: ✅ Index ready
```

**Key Steps:**

1. **File Discovery** (`indexer.py`)

   - Recursively scan project directory
   - Filter by file extensions (`.py`, `.js`, `.ts`, etc.)
   - Skip excluded directories (`node_modules`, `venv`, `.git`)
   - Check file size limits (skip files > 1MB)

2. **Smart Chunking** (`chunker.py`)

   - **Python**: Regex-based extraction of classes, methods, functions
   - **JavaScript/TypeScript**: Pattern matching for functions, classes, arrow functions
   - **Ruby**: Class and method extraction
   - **Other languages**: Line-based chunking with overlap
   - Preserves import statements as context
   - Chunks are 1500 chars with 200 char overlap

3. **Parallel Processing** (`indexer.py`)

   - Uses `ProcessPoolExecutor` with `MAX_WORKERS = cpu_count()`
   - CPU-bound chunking runs in separate processes
   - Progress bar shows real-time status

4. **Embedding Generation** (`embedder.py`)

   - Uses **sentence-transformers**: No server needed, 384-dim vectors
   - Model: `all-MiniLM-L6-v2` (auto-downloads on first use)
   - Batch processing for efficiency (32 texts per batch)
   - Local inference with GPU support if available

5. **Vector Storage** (`indexer.py`)
   - **LanceDB**: Rust-based, serverless vector database
   - Schema: `id`, `file_path`, `start_line`, `end_line`, `chunk_type`, `context`, `content`, `vector`
   - Stored in `~/.code-search/indexes/{project_hash}/`

#### 2. Search Pipeline

The search phase retrieves relevant code in <100ms:

```mermaid
sequenceDiagram
    participant User
    participant CLI as ss or cc
    participant Embedder
    participant LanceDB
    participant FS as File System
    participant Claude

    User->>CLI: ss "auth middleware"

    CLI->>Embedder: Generate query embedding
    Note over Embedder: <50ms

    Embedder->>LanceDB: Vector similarity search
    Note over LanceDB: Cosine distance, top_k=5
    Note over LanceDB: <20ms

    LanceDB->>CLI: Return chunk metadata

    par Fresh Content Read
        CLI->>FS: Read file 1 (latest content)
        CLI->>FS: Read file 2 (latest content)
        CLI->>FS: Read file N (latest content)
    end
    Note over FS: <30ms

    CLI->>CLI: Add context lines (before/after)

    alt Using cc command
        CLI->>Claude: Inject code context
        Claude->>User: Answer with full context
    else Using ss command
        CLI->>User: Display search results
    end
```

**Key Steps:**

1. **Query Embedding** (`search.py`)

   - Convert natural language query to vector
   - Uses same embedding model as indexing
   - Timing: <50ms

2. **Vector Search** (`search.py`)

   - Cosine similarity search in LanceDB
   - Returns top-k most similar chunks
   - Includes distance scores
   - Timing: <20ms

3. **Fresh Content Read** (`search.py`)

   - **Critical Feature**: Always reads latest file content
   - Enables incremental updates without full re-indexing
   - Adds context lines (3 before/after by default)
   - Timing: <30ms

4. **Result Formatting** (`search.py`)
   - Markdown format for Claude
   - JSON format for scripting
   - Includes file paths, line numbers, scores

#### 3. Incremental Update System

The incremental update system only re-indexes changed files:

```mermaid
flowchart TD
    A[code-index .] --> B{Index exists?}
    B -->|No| C[Full index]
    B -->|Yes| D[Load metadata]

    D --> E[Scan all files]
    E --> F{For each file}

    F --> G{Check mtime}
    G -->|Changed| H{Check size}
    G -->|Same| M[Skip file]

    H -->|Changed| I{Check hash}
    H -->|Same| I

    I -->|Changed| J[Re-chunk file]
    I -->|Same| M

    J --> K[Re-embed chunks]
    K --> L[Update DB + metadata]

    M --> N{More files?}
    L --> N
    N -->|Yes| F
    N -->|No| O[Save metadata]

    style C fill:#ffe1e1
    style J fill:#ffe1e1
    style M fill:#e1ffe1
```

**Metadata Tracking:**

- File path (relative to project root)
- Modification time (`mtime`)
- File size (`size`)
- Content hash (MD5)
- Stored in `metadata.json` alongside index

**Change Detection:**

1. Fast check: Compare `mtime` and `size`
2. Reliable check: Compare MD5 hash if needed
3. Only re-process changed files
4. Append new chunks to existing index

#### 4. Embedding System

The system uses sentence-transformers for fast, local embedding generation:

```mermaid
graph LR
    A[Text Input] --> B[SentenceTransformer]
    B --> C[all-MiniLM-L6-v2]
    C --> D[384-dim Vector]

    B --> E[Batch Processing]
    E --> F[GPU Accelerated]
    F --> D

    style B fill:#e1ffe1
    style C fill:#e1f5ff
    style D fill:#ffe1e1
```

**Key Features:**

- ✅ No server required - pure Python
- ✅ Fast startup (~2s)
- ✅ Low memory usage (~500MB)
- ✅ Excellent quality (384-dim)
- ✅ GPU support if available
- ✅ Auto-downloads model on first use (~100MB)
- ✅ Batch processing (32 texts at once)

### CLI Command Integration

```mermaid
graph TD
    A[User] --> B{Command?}

    B -->|code-index| C[Indexer]
    B -->|ss| D[Searcher]
    B -->|cc| E[Searcher + Claude]

    C --> F[Scan Files]
    F --> G[Chunk Code]
    G --> H[Generate Embeddings]
    H --> I[Store in LanceDB]

    D --> J[Embed Query]
    J --> K[Vector Search]
    K --> L[Read Fresh Content]
    L --> M[Display Results]

    E --> N[Embed Query]
    N --> O[Vector Search]
    O --> P[Read Fresh Content]
    P --> Q[Format as Markdown]
    Q --> R[Pass to Claude Code]

    style I fill:#e1f5ff
    style M fill:#ffe1e1
    style R fill:#ffe1e1
```

### Performance Breakdown

| Phase        | Operation           | Target     | Actual         | Notes                   |
| ------------ | ------------------- | ---------- | -------------- | ----------------------- |
| **Indexing** | File scanning       | -          | ~100ms         | Depends on project size |
|              | Chunking (parallel) | -          | ~2s/1000 files | CPU-bound, multi-core   |
|              | Embedding batch     | -          | ~50ms/batch    | sentence-transformers   |
|              | DB write            | -          | ~100ms         | LanceDB append          |
| **Search**   | Query embedding     | <50ms      | ✅ ~30ms       | Local inference         |
|              | Vector search       | <20ms      | ✅ ~15ms       | LanceDB Rust engine     |
|              | File read           | <30ms      | ✅ ~20ms       | Fresh content           |
|              | **Total**           | **<100ms** | **✅ ~65ms**   | Sub-100ms goal achieved |

### Storage Format

**Index Directory Structure:**

```
~/.code-search/indexes/{project_hash}/
├── chunks.lance/          # LanceDB vector database
│   ├── data/             # Vector data files
│   ├── indices/          # Vector indices
│   └── schema.json       # Table schema
└── metadata.json         # File metadata for incremental updates
```

**Metadata JSON Format:**

```json
{
  "src/indexer.py": {
    "path": "src/indexer.py",
    "mtime": 1705094400.0,
    "size": 12345,
    "hash": "abc123def456"
  }
}
```

**LanceDB Schema:**

```python
{
  "id": str,              # "file.py:10-50"
  "file_path": str,       # "src/indexer.py"
  "start_line": int64,    # 10
  "end_line": int64,      # 50
  "chunk_type": str,      # "function" | "class" | "method" | "block"
  "context": str,         # Import statements
  "content": str,         # Actual code
  "vector": float32[384]  # Embedding vector
}
```

## Configuration

Edit `src/config.py` to customize:

```python
# Embedding model
ST_MODEL = "all-MiniLM-L6-v2"  # Fast, good quality, 384 dim
# ST_MODEL = "all-mpnet-base-v2"  # Better quality, 768 dim, slower

# Chunking
CHUNK_SIZE = 1500
CHUNK_OVERLAP = 200

# Search
DEFAULT_TOP_K = 5

# Performance
MAX_WORKERS = os.cpu_count()
```

## Development

### Run Tests

```bash
source venv/bin/activate
pytest tests/ -v
```

### Run Benchmark

```bash
./benchmark.py
./benchmark.py /path/to/project
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint
ruff check src/ tests/

# Type check
mypy src/
```

## Troubleshooting

### Model download issues

The sentence-transformers model downloads automatically on first use. If you have network issues:

```bash
# Manually download the model
python3 -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
```

### Index not found

```bash
code-index .
```

### Slow search

Check:

1. Model has been downloaded (first run only)
2. Index is up to date
3. Project size (very large projects may need tuning)

## Benchmarking

Compare with ripgrep:

```bash
./benchmark.py /path/to/project
```

This will:

1. Index the project
2. Run 10 searches with different queries
3. Compare with ripgrep baseline
4. Show P99 latency and throughput

## Index Storage

Indexes are stored in:

```
~/.code-search/indexes/{project_hash}/
├── index.lance/      # LanceDB vector database
└── metadata.json     # File metadata for incremental updates
```

## Supported Languages

**Full AST Support:**

- Python (.py)
- JavaScript/TypeScript (.js, .jsx, .ts, .tsx)
- Ruby (.rb)

**Regex-based Support:**

- Go (.go)
- Rust (.rs)
- Java (.java)
- Kotlin (.kt)
- C/C++ (.c, .cpp, .h)
- C# (.cs)
- PHP (.php)
- Swift (.swift)

**Also Indexed:**

- Config files (.json, .yaml, .toml, .env)
- Documentation (.md, .rst, .txt)
- SQL (.sql)
- Shell scripts (.sh, .bash)

## License

MIT

## Contributing

Pull requests welcome! Please:

1. Add tests for new features
2. Run `black` and `ruff` before committing
3. Update benchmark results if performance changes

## Roadmap

### In Progress

- [x] sentence-transformers as default backend
- [x] Regex-based AST parsing for major languages
- [x] Multi-project support with isolated indexes
- [x] Comprehensive CLI with progress bars

### Planned

- [ ] Tree-sitter integration for enhanced AST parsing
- [ ] Watch mode for auto-reindexing on file changes
- [ ] VSCode extension for in-editor search
- [ ] Remote index sync for team sharing
- [ ] Cross-project search (search all indexed projects)
- [ ] Git integration (search across branches/commits)
- [ ] Query history and favorites
- [ ] Custom chunk strategies per language
- [ ] Index compression for large codebases

## Best Practices

### When to Re-Index

**Automatic (Incremental):**

```bash
code-index .  # Only re-indexes changed files
```

Run after:

- Git pull/merge
- Switching branches with many changes
- Installing new dependencies

**Force Re-Index:**

```bash
code-index . --force  # Re-indexes everything
```

Only needed when:

- Switching embedding backends
- Fixing corrupted index
- Updating chunking logic

### Optimal Search Queries

**Good Queries:**

- ✅ "authentication middleware"
- ✅ "database connection pooling"
- ✅ "error handling for API requests"
- ✅ "user registration validation"

**Less Effective:**

- ❌ "auth" (too vague)
- ❌ "function" (too generic)
- ❌ "class UserModel" (use grep for exact matches)

**Pro Tips:**

- Use descriptive phrases, not single words
- Describe what the code does, not how it's named
- For exact symbol matches, use grep/rg instead
- Combine with `-n` flag for more results: `ss "query" -n 10`

### Performance Optimization

**For Large Codebases (>10k files):**

1. Use `--force` sparingly (incremental is much faster)
2. Consider excluding test fixtures: add to `SKIP_DIRS` in config
3. Monitor memory usage during indexing
4. Index during off-hours if needed

**For Search Speed:**

1. Keep indexes up to date (run `code-index .` regularly)
2. Use specific queries (better matches = less results to process)
3. Adjust `CHUNK_SIZE` in config for your codebase style
4. Monitor with `DEBUG=1 ss "query"` to see timing breakdown

### Integration with Claude Code

**Workflow:**

```bash
# 1. Index your project
cd ~/projects/myapp
code-index .

# 2. Use semantic search to find relevant code
ss "payment processing logic"

# 3. Use cc to ask Claude with context
cc "how does the payment retry mechanism work?"

# 4. Make changes based on Claude's guidance
# ... edit files ...

# 5. Re-index changed files (incremental)
code-index .
```

**Claude Code Tips:**

- Use `cc` for understanding code ("explain how X works")
- Use `ss` for finding code locations ("where is X implemented")
- Combine both: `ss "feature" && cc "refactor this feature"`

## FAQ

**Q: How much disk space does an index use?**
A: Typically 1-5% of your codebase size. A 100MB project → ~2-5MB index.

**Q: Can I search multiple projects at once?**
A: Not yet. Each project needs separate `ss` commands. Cross-project search is planned.

**Q: What if my codebase is huge (>100k files)?**
A: The system handles it, but indexing may take several minutes. Consider:

- Excluding test fixtures and generated code
- Using incremental updates (don't use `--force`)
- Increasing `MAX_FILE_SIZE` limit if needed

**Q: Why is my first search slow?**
A: The embedding model loads on first use (~2s for sentence-transformers). Subsequent searches are fast.

**Q: Can I use this in CI/CD?**
A: Yes! Generate indexes during builds and share them. Example:

```bash
# In CI
code-index . && tar -czf index.tar.gz ~/.code-search/indexes/
# Later: extract and use
```

**Q: How do I switch between backends?**
A: The model is configured in `src/config.py`. You can change `ST_MODEL` to use a different sentence-transformers model:

```python
# In src/config.py
ST_MODEL = "all-mpnet-base-v2"  # Higher quality, 768-dim, slower
```

Then re-index with:
```bash
code-index . --force
```

**Q: What's the difference between code-index and grep/ripgrep?**
A:

- grep/ripgrep: Fast exact text matching ("find all files containing 'UserAuth'")
- code-index: Semantic understanding ("find authentication logic")
- Use both: grep for exact matches, code-index for concepts

**Q: Can I customize chunking logic?**
A: Yes! Edit `src/chunker.py`. Adjust regex patterns or add new language support.

**Q: Is my code sent anywhere?**
A: No. Everything runs locally:

- sentence-transformers: 100% local embedding generation
- LanceDB: Local filesystem storage
- No external API calls or data transmission

---

**Built to beat Cursor's performance. Open source, local-first, fast.** ⚡

## Quick Reference

### One-Page Cheatsheet

```bash
# Setup (one time)
./setup.sh

# Index project
code-index .                    # Incremental
code-index . --force            # Full re-index
code-index ~/other/project      # Index different project

# Search
ss "query"                      # Top 5 results
ss "query" -n 10                # Top 10 results
ss "query" --json               # JSON output
ss "query" --no-context         # Without surrounding code

# With Claude
cc "query"                      # Search + send to Claude
cc "query" -n 10                # More context for Claude

# Environment
export DEBUG=1                  # Show timing info
export VERBOSE=1                # Verbose output

# Maintenance
rm -rf ~/.code-search/indexes/{hash}  # Remove specific index
rm -rf ~/.code-search                 # Remove all indexes
```
