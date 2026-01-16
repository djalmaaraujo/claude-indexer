#!/usr/bin/env python3
"""
MCP Server for Semantic Code Search.

Exposes semantic search capabilities as MCP tools for Claude Code integration.
Uses stdio transport for communication with Claude Code.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path to import src modules
SCRIPT_DIR = Path(__file__).resolve().parent
PACKAGE_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(PACKAGE_DIR))

from mcp.server.fastmcp import FastMCP

# Import existing modules
from src.search import Searcher
from src.indexer import Indexer
from src.config import get_index_path

# Initialize MCP server
mcp = FastMCP("semantic-search")


def get_project_path() -> Path:
    """Get the current project path from environment or cwd."""
    project_path = os.environ.get("PROJECT_PATH", os.getcwd())
    return Path(project_path).resolve()


@mcp.tool()
def search_code(query: str, num_results: int = 5) -> str:
    """
    Search for code semantically using vector similarity.

    Use this tool when:
    - User asks "where is X" or "find X"
    - User wants to locate functionality
    - User needs to understand code organization
    - User asks about implementation location

    Args:
        query: Natural language description of what to find
        num_results: Number of results to return (default: 5, max: 20)

    Returns:
        JSON with search results including file paths, line numbers, scores, and content
    """
    project_path = get_project_path()

    # Clamp num_results
    num_results = max(1, min(num_results, 20))

    try:
        searcher = Searcher(project_path)
        results = searcher.search(query, top_k=num_results)

        # Format results as JSON
        output = {
            "success": True,
            "project": str(project_path),
            "query": query,
            "num_results": len(results),
            "results": [
                {
                    "file_path": r.file_path,
                    "start_line": r.start_line,
                    "end_line": r.end_line,
                    "score": round(r.score, 4),
                    "chunk_type": r.chunk_type,
                    "content": r.content[:3000] + "..." if len(r.content) > 3000 else r.content,
                }
                for r in results
            ],
        }

        return json.dumps(output, indent=2)

    except FileNotFoundError:
        return json.dumps(
            {
                "success": False,
                "error": "no_index",
                "message": f"No index found for {project_path}. Run 'code-index {project_path}' first.",
                "suggestion": "Use the reindex_project tool to create an index.",
            }
        )
    except Exception as e:
        return json.dumps({"success": False, "error": "search_failed", "message": str(e)})


@mcp.tool()
def get_index_status() -> str:
    """
    Check the semantic search index status for the current project.

    Returns information about:
    - Whether an index exists
    - When it was last updated
    - Number of files indexed
    - Project path

    Returns:
        JSON with index status information
    """
    project_path = get_project_path()
    index_path = get_index_path(project_path)
    metadata_path = index_path / "metadata.json"
    db_path = index_path / "chunks.lance"

    try:
        if not db_path.exists():
            return json.dumps(
                {
                    "success": True,
                    "exists": False,
                    "project": str(project_path),
                    "message": "No index found. Run 'code-index .' or use reindex_project tool.",
                }
            )

        # Load metadata
        metadata = {}
        if metadata_path.exists():
            with open(metadata_path, "r") as f:
                metadata = json.load(f)

        # Get last modified time of the database
        last_updated = datetime.fromtimestamp(db_path.stat().st_mtime).isoformat()

        return json.dumps(
            {
                "success": True,
                "exists": True,
                "project": str(project_path),
                "index_path": str(index_path),
                "last_updated": last_updated,
                "files_indexed": len(metadata),
                "message": "Index is ready for searching.",
            }
        )

    except Exception as e:
        return json.dumps({"success": False, "error": "status_check_failed", "message": str(e)})


@mcp.tool()
def reindex_project(force: bool = False) -> str:
    """
    Trigger re-indexing of the current project.

    Args:
        force: If True, re-index all files. If False, only index changed files (incremental).

    Returns:
        JSON with indexing results including files processed and time taken
    """
    project_path = get_project_path()

    try:
        import time

        start_time = time.time()

        indexer = Indexer(project_path, force=force)
        indexer.index()

        elapsed = time.time() - start_time

        return json.dumps(
            {
                "success": True,
                "project": str(project_path),
                "force": force,
                "stats": {
                    "files_scanned": indexer.stats["files_scanned"],
                    "files_indexed": indexer.stats["files_indexed"],
                    "files_unchanged": indexer.stats["files_unchanged"],
                    "chunks_created": indexer.stats["chunks_created"],
                    "time_seconds": round(elapsed, 2),
                },
                "message": f"Indexed {indexer.stats['files_indexed']} files in {elapsed:.1f}s",
            }
        )

    except Exception as e:
        return json.dumps({"success": False, "error": "indexing_failed", "message": str(e)})


# Run with stdio transport (required for Claude Code)
if __name__ == "__main__":
    mcp.run(transport="stdio")
