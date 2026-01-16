# Claude Indexer

![Tests](https://github.com/djalmaaraujo/claude-indexer/actions/workflows/tests.yml/badge.svg)

Local semantic code search with MCP integration for Claude Code. Pre-indexes codebases for instant search (<100ms).

## Quick Start

```bash
# Install
./setup.sh

# Index your project
code-index .

# Search
ss "authentication middleware"
ss "database connection" -n 10 --json
```

## MCP Integration

Exposes semantic search directly inside Claude Code sessions.

```bash
./claude-integration/install.sh
# Restart Claude Code
```

After setup, ask questions naturally:
```
"Where is the authentication code?"
"Find functions that handle database connections"
```

**Manual setup** - add to `.mcp.json`:
```json
{
  "mcpServers": {
    "semantic-search": {
      "command": "/path/to/claude-indexer/venv/bin/python3",
      "args": ["/path/to/claude-indexer/mcp-server/server.py"],
      "env": { "PYTHONPATH": "/path/to/claude-indexer" }
    }
  }
}
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `code-index .` | Index current directory |
| `code-index . --force` | Force full re-index |
| `ss "query"` | Semantic search |
| `ss "query" -n 10 --json` | More results, JSON output |
| `cc "query"` | Search and send to Claude CLI |

## Configuration

**Model selection:**
```bash
export CODE_SEARCH_MODEL="all-MiniLM-L6-v2"        # Fast (default)
export CODE_SEARCH_MODEL="microsoft/codebert-base" # Code-specific
export CODE_SEARCH_MODEL="all-mpnet-base-v2"       # Best quality
```

**Advanced settings** in `src/config.py`:
- `CHUNK_SIZE` - Maximum chunk size (default: 1500)
- `CHUNK_OVERLAP` - Overlap between chunks (default: 200)
- `DEFAULT_TOP_K` - Default search results (default: 5)
- `MAX_WORKERS` - Parallel workers (default: cpu_count)

## Supported Languages

**Tree-sitter AST:** Python, JavaScript, TypeScript

**Regex fallback:** Ruby, Go, Rust, Java, Kotlin, C/C++, C#, PHP, Swift, config files, markdown, SQL, shell scripts

## Architecture

```
Files → Chunker (AST/regex) → Embedder → LanceDB → Searcher
```

- **Embeddings**: sentence-transformers (local, GPU auto-detection)
- **Vector DB**: LanceDB (serverless, Rust-based)
- **Chunking**: Tree-sitter for precise boundaries, regex fallback
- **Storage**: `~/.code-search/indexes/{project_hash}/`

## Development

```bash
source venv/bin/activate
pytest tests/ -v
black src/ tests/
ruff check src/ tests/
```

## License

MIT
