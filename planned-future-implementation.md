# Plan: Seamless Claude Code Integration for Semantic Search

## 📋 TODO List for Implementation

When ready to implement this plan, follow this checklist:

### Phase 1: MCP Server (Core) - ~2-3 hours
- [ ] Create `~/dev/claude-indexer/mcp-server/` directory
- [ ] Implement `mcp-server/server.py` with MCP protocol (stdio transport)
- [ ] Add `search_code(query, num_results)` tool using `src/search.py`
- [ ] Add `get_index_status()` tool
- [ ] Add `reindex_project(force)` tool using `src/indexer.py`
- [ ] Create `mcp-server/requirements.txt`
- [ ] Test MCP server standalone: `python mcp-server/server.py`
- [ ] Register in `~/.claude/mcp.json`
- [ ] Verify with: `claude mcp list` and `claude mcp get semantic-search`

### Phase 2: SessionStart Hook (Auto-indexing) - ~30 min
- [ ] Create `~/dev/claude-indexer/claude-integration/hooks/auto-index.sh`
- [ ] Test hook script manually
- [ ] Make executable: `chmod +x auto-index.sh`
- [ ] Copy to `~/.claude/hooks/auto-index.sh`
- [ ] Register in `~/.claude/settings.json` hooks array
- [ ] Test: Start Claude in a code project, verify "🔍 Indexing..." appears
- [ ] Verify indexing runs in background (non-blocking)

### Phase 3: Skill (Automatic Recognition) - ~30 min
- [ ] Create `~/dev/claude-indexer/claude-integration/skills/semantic-search/SKILL.md`
- [ ] Write skill instructions for automatic triggering on "find"/"where is" queries
- [ ] Copy to `~/.claude/skills/semantic-search/SKILL.md`
- [ ] Test: Ask "where is the authentication middleware?"
- [ ] Verify Claude automatically calls `search_code` tool

### Phase 4: Slash Commands (Manual Control) - ~30 min
- [ ] Create `~/dev/claude-indexer/claude-integration/commands/search.md`
- [ ] Create `~/dev/claude-indexer/claude-integration/commands/reindex.md`
- [ ] Create `~/dev/claude-indexer/claude-integration/commands/index-status.md`
- [ ] Copy all to `~/.claude/commands/`
- [ ] Test: `/search database connection`
- [ ] Test: `/reindex`
- [ ] Test: `/index-status`

### Phase 5: Testing & Validation - ~1-2 hours
- [ ] Test auto-indexing on session start (multiple projects)
- [ ] Test automatic semantic search recognition
- [ ] Test manual slash commands
- [ ] Test cross-project functionality (index multiple projects)
- [ ] Verify performance (<100ms search time)
- [ ] Check MCP server logs for errors: `claude mcp logs semantic-search`
- [ ] Test fallback behavior when index doesn't exist

### Phase 6: Plugin Bundle (Optional) - ~30 min
- [ ] Create plugin structure: `~/dev/claude-indexer/claude-integration/plugin/`
- [ ] Write `.claude-plugin/plugin.json` manifest
- [ ] Copy all components (hooks, skills, commands, MCP) into plugin
- [ ] Test plugin installation locally
- [ ] Consider publishing to Claude Code marketplace

### Phase 7: Documentation - ~30 min
- [ ] Update main `README.md` with Claude integration instructions
- [ ] Create `CLAUDE_INTEGRATION.md` guide
- [ ] Add troubleshooting section for common issues
- [ ] Document `/search`, `/reindex`, `/index-status` commands
- [ ] Add usage examples and screenshots

---

## Goal
Integrate the semantic search tool with Claude Code so it:
- Auto-indexes projects on session start
- Automatically uses semantic search before file reads
- Requires one-time setup only
- Works transparently for the user

## Current Status
✅ Semantic search tool exists (`code-index`, `ss`, `cc` commands)
✅ Works independently from any directory
❌ Not integrated with Claude Code workflows
❌ User must manually run commands

## Phase 1: Understanding Integration Options ✅

### Claude Code Integration Systems Available

Based on exploration of your Claude Code setup, we have **5 integration mechanisms**:

1. **Hooks** - Event-driven automation
   - `SessionStart` - Runs when Claude starts (perfect for auto-indexing)
   - `PreToolUse` - Intercepts before tools run (can inject semantic search before Read/Glob)
   - `PostToolUse` - Runs after tools complete
   - Location: `~/.claude/hooks/` + register in `~/.claude/settings.json`

2. **Slash Commands** - User-invoked commands
   - Creates `/search` command for manual semantic search
   - Location: `~/.claude/commands/search.md`
   - Can pre-approve tools via `allowed-tools` frontmatter

3. **Skills** - Reusable expertise bundles
   - Claude can automatically recognize when to use semantic search
   - Progressive disclosure: metadata always loaded, body loaded when needed
   - Location: `~/.claude/skills/semantic-search/`

4. **MCP Servers** - Protocol-based integrations
   - Exposes search capabilities as MCP tools
   - Claude can call `search_code()` tool automatically
   - Most powerful but requires MCP server implementation

5. **Plugins** - Distribution bundles
   - Packages all components together
   - Shareable with team via marketplace
   - Location: `~/.claude/plugins/semantic-search/`

### Your Current Setup
✅ Already using hooks (session-context, commit-validator, auto-format)
✅ Already using skills (prompt-compressor)
✅ Already using plugins (context-a8c, planner, slack, etc.)
✅ Already using MCP (context7 plugin)

## Phase 2: User Requirements ✅

Based on your answers:
- ✅ **Workflow**: Mix of approaches → Solution must work from any starting point
- ✅ **Automation**: Fully automatic → Claude should recognize when to search semantically
- ✅ **Performance**: Background, non-blocking → Index on session start without blocking

## Phase 3: Design - Multi-Layer Integration Strategy

### Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│ Session Start                                           │
│  ↓                                                      │
│ SessionStart Hook → Auto-index in background           │
│  • Non-blocking                                        │
│  • Only if in code project                            │
│  • Incremental (fast if nothing changed)              │
└─────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────┐
│ User asks: "Where is auth middleware?"                 │
│  ↓                                                      │
│ Claude recognizes search intent (via Skill)            │
│  ↓                                                      │
│ Calls MCP tool: search_code("auth middleware")         │
│  ↓                                                      │
│ Returns results with file paths + line numbers         │
│  ↓                                                      │
│ Claude reads the actual files and explains             │
└─────────────────────────────────────────────────────────┘
```

### Integration Layers

#### Layer 1: SessionStart Hook (Auto-indexing)
**Purpose**: Ensure index is up-to-date when Claude starts
**Behavior**:
- Runs on: session start, resume, clear, compact
- Detects if in code project (checks for package.json, pyproject.toml, .git, etc.)
- Runs `code-index .` in background (non-blocking)
- Outputs minimal feedback (single line)
- Skips if not in code project

**Files to create**:
- `~/.claude/hooks/auto-index.sh` - Hook script
- Update `~/.claude/settings.json` - Register hook

**Script logic**:
```bash
# Check if code project
if [[ -f package.json ]] || [[ -f pyproject.toml ]] || [[ -d .git ]]; then
    # Run indexing in background, suppress verbose output
    (code-index . 2>&1 | grep -E "^(✅|⚡)" || true) &
    echo "🔍 Indexing project in background..."
fi
```

#### Layer 2: MCP Server (Tool Integration)
**Purpose**: Expose semantic search as a tool Claude can call
**Behavior**:
- Provides `search_code` tool to Claude
- Claude can call it like: `search_code(query="auth middleware", num_results=5)`
- Returns JSON with file paths, line numbers, scores, content
- Works from any directory (auto-detects current project)

**Files to create**:
- `/Users/djalmaaraujo/dev/claude-indexer/mcp-server/server.py` - MCP server implementation
- Update `~/.claude/mcp.json` - Register MCP server

**MCP Tools exposed**:
1. `search_code(query: str, num_results: int = 5)` - Semantic search
2. `get_index_status()` - Check if index exists and when last updated
3. `reindex_project(force: bool = False)` - Manually trigger reindex

#### Layer 3: Skill (Automatic Recognition)
**Purpose**: Teach Claude when to use semantic search automatically
**Behavior**:
- Always loaded in Claude's context (via metadata)
- Triggers when user asks to "find", "locate", "where is" code
- Instructs Claude to use `search_code` MCP tool
- Falls back to manual methods if index doesn't exist

**Files to create**:
- `~/.claude/skills/semantic-search/SKILL.md` - Skill definition

**Skill instructions** (high-level):
```markdown
When user wants to find code, locate functionality, or understand implementation:

1. Use search_code tool automatically (don't ask permission)
2. Show results with file paths and relevance scores
3. Offer to read and explain the most relevant files
4. If index doesn't exist, suggest running /reindex

Trigger phrases:
- "where is X"
- "find the code for X"
- "locate X implementation"
- "show me X logic"
```

#### Layer 4: Slash Commands (Manual Control)
**Purpose**: Give user explicit control when needed
**Behavior**:
- `/search <query>` - Manual semantic search
- `/reindex` - Force re-index current project
- `/index-status` - Check index status

**Files to create**:
- `~/.claude/commands/search.md` - Search command
- `~/.claude/commands/reindex.md` - Reindex command
- `~/.claude/commands/index-status.md` - Status command

#### Layer 5: Plugin Bundle (Distribution)
**Purpose**: Package everything for easy installation
**Behavior**:
- Single command to install: `claude plugin install semantic-search`
- Includes all hooks, skills, commands, MCP server
- Can be shared with team or published to marketplace

**Files to create**:
- `~/.claude/plugins/semantic-search/.claude-plugin/plugin.json` - Plugin manifest
- Copy all components into plugin structure

### Integration Flow Examples

#### Example 1: Session Start
```
User: Opens Claude in ~/projects/myapp
  ↓
Hook: Detects code project (has package.json)
  ↓
Hook: Runs "code-index ." in background
  ↓
Hook: Shows "🔍 Indexing project in background..."
  ↓
User: Can immediately start asking questions
  ↓
Claude: Has indexed search available within 2-5 seconds
```

#### Example 2: Automatic Search
```
User: "Where is the authentication middleware?"
  ↓
Skill: Recognizes search intent
  ↓
Claude: Calls search_code("authentication middleware", num_results=5)
  ↓
MCP: Returns 5 results with file paths
  ↓
Claude: "I found 5 relevant locations:
         1. src/middleware/auth.js:45 (score: 0.12)
         2. src/routes/api.js:120 (score: 0.18)
         Would you like me to show you the main implementation?"
```

#### Example 3: Manual Override
```
User: "/search database connection pooling"
  ↓
Command: Calls search_code MCP tool directly
  ↓
Command: Returns formatted results
  ↓
User: Can see raw search results before Claude explains
```

### Component Dependencies

```
Plugin (bundle)
  ├── SessionStart Hook → code-index CLI
  ├── MCP Server → code-index + ss + search.py
  ├── Skill → MCP Server tools
  └── Slash Commands → MCP Server tools
```

**Critical**: MCP server must be running for skills and commands to work. This is auto-started by Claude Code when registered in `~/.claude/mcp.json`.

### File Structure

```
~/.claude/
├── settings.json (updated)
│   └── Add SessionStart hook registration
├── mcp.json (updated)
│   └── Add semantic-search MCP server
├── hooks/
│   └── auto-index.sh (new)
├── skills/
│   └── semantic-search/
│       └── SKILL.md (new)
└── commands/
    ├── search.md (new)
    ├── reindex.md (new)
    └── index-status.md (new)

~/dev/claude-indexer/
├── mcp-server/
│   ├── server.py (new) - MCP server implementation
│   ├── requirements.txt (new)
│   └── README.md (new)
└── claude-integration/
    └── plugin/
        └── .claude-plugin/
            └── plugin.json (new)
```

## Phase 4: Implementation Details

### Component 1: SessionStart Hook

**File**: `~/.claude/hooks/auto-index.sh`
```bash
#!/usr/bin/env bash
# Auto-index projects on Claude session start
set -e

PROJECT_DIR="$PWD"

# Check if code-index exists
if ! command -v code-index &> /dev/null; then
    exit 0
fi

# Check if this is a code project
if [[ -f "package.json" ]] || [[ -f "pyproject.toml" ]] || \
   [[ -f "Cargo.toml" ]] || [[ -f "go.mod" ]] || [[ -d ".git" ]]; then

    # Run in background, non-blocking
    (code-index "$PROJECT_DIR" 2>&1 | tail -1) &
    echo "🔍 Semantic search: indexing in background..."
fi
```

**Registration in** `~/.claude/settings.json`:
```json
{
  "hooks": [
    {
      "event": "SessionStart",
      "script": "/Users/djalmaaraujo/.claude/hooks/auto-index.sh",
      "timeout": 120000
    }
  ]
}
```

### Component 2: MCP Server

**File**: `~/dev/claude-indexer/mcp-server/server.py`

**Core functionality**:
- Implements MCP protocol (stdio transport)
- Exposes 3 tools: `search_code`, `get_index_status`, `reindex_project`
- Uses existing `src/search.py` and `src/indexer.py` modules
- Auto-detects current working directory
- Returns structured JSON results

**Key methods**:
```python
async def search_code(query: str, num_results: int = 5) -> dict:
    """Search semantically in current project"""
    # Use src/search.py Searcher class
    # Return: [{file_path, start_line, end_line, score, content}]

async def get_index_status() -> dict:
    """Check index status"""
    # Check if ~/.code-search/indexes/{project_hash}/ exists
    # Return: {exists, last_updated, num_chunks, project_path}

async def reindex_project(force: bool = False) -> dict:
    """Trigger re-indexing"""
    # Use src/indexer.py Indexer class
    # Return: {success, files_indexed, chunks_created, time}
```

**MCP Server registration in** `~/.claude/mcp.json`:
```json
{
  "mcpServers": {
    "semantic-search": {
      "command": "python",
      "args": [
        "/Users/djalmaaraujo/dev/claude-indexer/mcp-server/server.py"
      ],
      "cwd": "/Users/djalmaaraujo/dev/claude-indexer",
      "env": {
        "PYTHONPATH": "/Users/djalmaaraujo/dev/claude-indexer",
        "EMBEDDING_BACKEND": "sentence-transformers"
      }
    }
  }
}
```

### Component 3: Skill

**File**: `~/.claude/skills/semantic-search/SKILL.md`

```markdown
---
name: semantic-search
description: Automatically search code semantically using vector similarity when user asks to find, locate, or understand code implementation
---

# Semantic Search Skill

You have access to a powerful semantic code search system via MCP tools.

## When to Use

**Automatically trigger** (without asking) when user:
- Asks "where is X" or "find X"
- Wants to locate functionality: "show me auth logic"
- Needs to understand implementation location
- Asks about code organization

## How to Use

1. Call `search_code(query, num_results=5)` tool with user's intent
2. Parse results: file paths, line numbers, relevance scores
3. Show results to user in clear format
4. Offer to read and explain the most relevant files

## Example

User: "Where is the authentication middleware?"

You: *calls search_code("authentication middleware", 5)*

Results: [
  {file: "src/middleware/auth.js", line: 45, score: 0.12},
  {file: "src/routes/api.js", line: 120, score: 0.18}
]

You: "I found authentication middleware in:
1. **src/middleware/auth.js:45** (main implementation, score: 0.12)
2. **src/routes/api.js:120** (usage, score: 0.18)

Would you like me to show you the main implementation?"

## Priority

**Use this BEFORE** Glob/Grep when searching for code concepts (not exact strings).

For exact string matches (like "class UserAuth"), use Grep instead.

## Fallback

If search_code tool unavailable or returns empty:
- Suggest user run: `code-index .`
- Fall back to Glob/Grep
```

### Component 4: Slash Commands

**File**: `~/.claude/commands/search.md`
```markdown
---
description: Search code semantically using vector similarity
argument-hint: <query>
---

Search for code using semantic search:

!`ss "$ARGUMENTS" -n 10`

Present results in a clear, formatted way.
```

**File**: `~/.claude/commands/reindex.md`
```markdown
---
description: Re-index current project for semantic search
---

Re-indexing the current project...

!`code-index . --force`

Index updated successfully!
```

**File**: `~/.claude/commands/index-status.md`
```markdown
---
description: Check semantic search index status
---

Checking index status...

!`ss "test" --project . 2>&1 | head -1 || echo "No index found"`

Use `/reindex` to create or update the index.
```

### Component 5: Plugin Bundle

**File**: `~/.claude/plugins/semantic-search/.claude-plugin/plugin.json`
```json
{
  "name": "semantic-search",
  "version": "1.0.0",
  "description": "Seamless semantic code search integration with Claude Code",
  "author": "Djalma Araujo",
  "repository": "https://github.com/djalmaaraujo/claude-indexer",
  "components": {
    "hooks": ["hooks/auto-index.sh"],
    "skills": ["skills/semantic-search"],
    "commands": ["commands/search.md", "commands/reindex.md", "commands/index-status.md"],
    "mcp": ["mcp/semantic-search.json"]
  },
  "dependencies": {
    "external": ["code-index", "ss"]
  },
  "setup": {
    "instructions": "Run setup.sh in the claude-indexer project first"
  }
}
```

## Phase 5: Verification & Testing

### Installation Steps

1. **Create hook script**:
   ```bash
   mkdir -p ~/.claude/hooks
   cp ~/dev/claude-indexer/claude-integration/hooks/auto-index.sh ~/.claude/hooks/
   chmod +x ~/.claude/hooks/auto-index.sh
   ```

2. **Register hook in settings.json**:
   - Manually add to `~/.claude/settings.json` hooks array
   - Or use Claude Code settings UI

3. **Start MCP server**:
   ```bash
   # Test MCP server manually first
   cd ~/dev/claude-indexer
   python mcp-server/server.py
   ```

4. **Register MCP server**:
   ```bash
   claude mcp add --transport stdio --scope user \
     semantic-search \
     -- python /Users/djalmaaraujo/dev/claude-indexer/mcp-server/server.py
   ```

5. **Create skill**:
   ```bash
   mkdir -p ~/.claude/skills/semantic-search
   cp ~/dev/claude-indexer/claude-integration/skills/semantic-search/SKILL.md \
      ~/.claude/skills/semantic-search/
   ```

6. **Create commands**:
   ```bash
   mkdir -p ~/.claude/commands
   cp ~/dev/claude-indexer/claude-integration/commands/*.md ~/.claude/commands/
   ```

### Testing Plan

#### Test 1: Auto-indexing on Session Start
```bash
# 1. Start Claude in a code project
cd ~/projects/some-project
claude

# Expected: See "🔍 Semantic search: indexing in background..."
# Expected: Index created in ~/.code-search/indexes/
```

#### Test 2: Automatic Semantic Search
```bash
# In Claude session:
User: "Where is the authentication middleware?"

# Expected: Claude automatically calls search_code tool
# Expected: Shows results with file paths and scores
# Expected: Offers to read the files
```

#### Test 3: Manual Slash Commands
```bash
# In Claude session:
User: "/search database connection"

# Expected: Shows search results directly
# Expected: Lists files and line numbers

User: "/index-status"

# Expected: Shows index status

User: "/reindex"

# Expected: Re-indexes project with progress
```

#### Test 4: MCP Tool Availability
```bash
# Verify MCP server is running
claude mcp list

# Expected: Shows "semantic-search" server

# Test MCP tools
claude mcp get semantic-search

# Expected: Shows 3 tools: search_code, get_index_status, reindex_project
```

#### Test 5: Cross-Project Works
```bash
# Test in different project
cd ~/different/project
claude

# Expected: Auto-indexes this new project
# Expected: Search works with this project's index
# Expected: Both indexes coexist in ~/.code-search/indexes/
```

### Success Criteria

✅ Hook runs on session start without blocking
✅ Indexing completes in background (<10s for small projects)
✅ Claude automatically uses semantic search when appropriate
✅ MCP tools work from any directory
✅ Multiple projects can be indexed simultaneously
✅ Commands work for manual control
✅ No errors in Claude Code logs
✅ Performance: Search completes in <100ms

### Troubleshooting

**If hook doesn't run**:
- Check `~/.claude/settings.json` has correct hook registration
- Verify `code-index` command is in PATH
- Test hook manually: `~/.claude/hooks/auto-index.sh`

**If MCP server fails**:
- Check MCP server logs: `claude mcp logs semantic-search`
- Verify Python dependencies: `pip list | grep -E "(lancedb|httpx)"`
- Test MCP server manually: `python ~/dev/claude-indexer/mcp-server/server.py`

**If skill doesn't trigger**:
- Verify skill file exists in `~/.claude/skills/semantic-search/SKILL.md`
- Check Claude recognizes the skill (shows in context)
- Try explicit: "/search query" to force usage

**If search returns empty**:
- Verify index exists: `ls ~/.code-search/indexes/`
- Check index status with `/index-status`
- Re-index with `/reindex`

## Alternative Approaches Considered

### Alternative 1: Pure Hook-Based (No MCP)
**Approach**: Use PreToolUse hook to intercept Glob/Read and inject search results
**Pros**: Simpler, no MCP server needed
**Cons**: Less control, harder to format results, can't expose as tool
**Decision**: Rejected - MCP provides better integration

### Alternative 2: Bash-Only Solution (No Python MCP)
**Approach**: Slash commands call `ss` CLI directly, no MCP server
**Pros**: Simpler implementation, no MCP overhead
**Cons**: Claude can't automatically trigger search, no structured output
**Decision**: Rejected - Loses automatic recognition benefit

### Alternative 3: Polling-Based Indexing
**Approach**: Background daemon watches for file changes and auto-indexes
**Pros**: Always up-to-date index
**Cons**: Extra process running, battery drain, complexity
**Decision**: Rejected - Incremental indexing on session start is sufficient

## Recommended Implementation Order

1. **MCP Server** (core functionality)
2. **SessionStart Hook** (auto-indexing)
3. **Skill** (automatic recognition)
4. **Slash Commands** (manual control)
5. **Plugin Bundle** (distribution)

This order ensures each layer builds on the previous, allowing incremental testing.

## Critical Files to Modify

1. `~/.claude/settings.json` - Register SessionStart hook
2. `~/.claude/mcp.json` - Register MCP server
3. Create new files in:
   - `~/.claude/hooks/`
   - `~/.claude/skills/`
   - `~/.claude/commands/`
   - `~/dev/claude-indexer/mcp-server/`

## Estimated Effort

- MCP Server implementation: 2-3 hours
- Hook + skill + commands: 1 hour
- Testing + debugging: 1-2 hours
- Plugin packaging: 30 min
- **Total**: 4-6 hours

## Next Steps

1. Implement MCP server with search_code tool
2. Create and test SessionStart hook
3. Create skill for automatic recognition
4. Add slash commands for manual control
5. Test end-to-end workflow
6. Package as plugin for distribution
