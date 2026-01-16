#!/usr/bin/env bash
#
# Install Claude Code integration for semantic search
#
# This script:
# 1. Installs MCP Python SDK
# 2. Copies hook script to ~/.claude/hooks/
# 3. Registers MCP server in ~/.claude/mcp.json
# 4. Registers SessionStart hook in ~/.claude/settings.json
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CLAUDE_DIR="$HOME/.claude"

echo "Installing Claude Code integration for semantic search..."
echo ""

# 1. Install MCP Python SDK
echo "[1/4] Installing MCP SDK..."
"$PROJECT_DIR/venv/bin/pip" install -q "mcp>=1.0.0"
echo "      Done."

# 2. Create hooks directory and copy hook script
echo "[2/4] Installing SessionStart hook..."
mkdir -p "$CLAUDE_DIR/hooks"
cp "$SCRIPT_DIR/hooks/auto-index.sh" "$CLAUDE_DIR/hooks/auto-index.sh"
chmod +x "$CLAUDE_DIR/hooks/auto-index.sh"
echo "      Copied to $CLAUDE_DIR/hooks/auto-index.sh"

# 3. Register MCP server globally using claude CLI
echo "[3/4] Registering MCP server..."

# Remove existing registration if present (ignore errors)
claude mcp remove semantic-search -s user 2>/dev/null || true

# Add MCP server at user scope (global)
claude mcp add semantic-search \
    -s user \
    -e PYTHONPATH="$PROJECT_DIR" \
    -- "$PROJECT_DIR/venv/bin/python3" "$PROJECT_DIR/mcp-server/server.py"

echo "      Registered semantic-search MCP globally"

# 4. Register SessionStart hook in settings.json
echo "[4/4] Registering SessionStart hook..."
SETTINGS_CONFIG="$CLAUDE_DIR/settings.json"

# Create settings.json if it doesn't exist
if [[ ! -f "$SETTINGS_CONFIG" ]]; then
    echo '{}' >"$SETTINGS_CONFIG"
fi

python3 <<EOF
import json

settings_path = "$SETTINGS_CONFIG"
hook_path = "$CLAUDE_DIR/hooks/auto-index.sh"

with open(settings_path, 'r') as f:
    settings = json.load(f)

# Claude Code uses a nested hooks structure:
# hooks: { EventType: [ { matcher: "...", hooks: [...] } ] }
if 'hooks' not in settings:
    settings['hooks'] = {}

hooks = settings['hooks']

# Ensure SessionStart section exists
if 'SessionStart' not in hooks:
    hooks['SessionStart'] = []

# Find existing SessionStart matcher or create one
session_start = hooks['SessionStart']
hook_entry = {"type": "command", "command": hook_path}

# Check if our hook already exists in any SessionStart config
hook_exists = False
for config in session_start:
    if isinstance(config, dict) and 'hooks' in config:
        for h in config['hooks']:
            if h.get('command') == hook_path:
                hook_exists = True
                break
    if hook_exists:
        break

if not hook_exists:
    # Find startup matcher or create one
    startup_matcher = None
    for config in session_start:
        if isinstance(config, dict) and config.get('matcher', '') in ['startup', 'startup|resume|clear|compact']:
            startup_matcher = config
            break

    if startup_matcher:
        startup_matcher['hooks'].append(hook_entry)
    else:
        # Create new matcher
        session_start.append({
            "matcher": "startup|resume|clear|compact",
            "hooks": [hook_entry]
        })

    print(f"      Added hook to {settings_path}")
else:
    print(f"      Hook already registered in {settings_path}")

with open(settings_path, 'w') as f:
    json.dump(settings, f, indent=2)
EOF

echo ""
echo "============================================"
echo "Installation complete!"
echo "============================================"
echo ""
echo "Restart Claude Code to activate the integration."
echo ""
echo "Features enabled:"
echo "  - Auto-indexing on session start (when in git repos)"
echo "  - MCP tools: search_code, get_index_status, reindex_project"
echo ""
echo "To verify:"
echo "  1. Start a new Claude Code session in a git project"
echo "  2. You should see: 'Semantic search: indexing in background...'"
echo "  3. Ask Claude: 'Where is the main function?'"
echo ""
