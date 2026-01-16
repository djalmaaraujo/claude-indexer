#!/usr/bin/env bash
#
# SessionStart Hook: Auto-index code projects for semantic search
#
# This hook runs when Claude Code starts a session. It:
# 1. Detects if the current directory is a code project (has .git)
# 2. Runs code-index in the background (non-blocking)
# 3. Outputs minimal feedback
#
# The indexing is incremental, so subsequent runs are fast if nothing changed.
#

set -e

PROJECT_DIR="$PWD"

# Check if code-index command exists
if ! command -v code-index &>/dev/null; then
    # Try the direct path
    CODE_INDEX="$HOME/bin/code-index"
    if [[ ! -x "$CODE_INDEX" ]]; then
        # Silently exit if code-index not found
        exit 0
    fi
else
    CODE_INDEX="code-index"
fi

# Only index if this is a git repository
if [[ -d ".git" ]]; then
    # Run indexing in background (non-blocking)
    # Redirect all output to /dev/null so it doesn't block
    nohup "$CODE_INDEX" "$PROJECT_DIR" &>/dev/null &

    echo "Semantic search: indexing in background..."
fi
