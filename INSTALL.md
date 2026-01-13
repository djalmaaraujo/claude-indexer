# Installation Guide

## Step-by-Step Installation

### 1. Run the setup script

```bash
cd ~/dev/claude-indexer
./setup.sh
```

This will:
- ✅ Install Homebrew (if needed)
- ✅ Install Python 3.11+ (if needed)
- ✅ Create a virtual environment in `venv/`
- ✅ Install Python dependencies (including sentence-transformers model)
- ✅ Create symlinks in `~/bin/` for CLI commands
- ✅ Add `~/bin` to your PATH

### 2. Reload your shell

```bash
# For zsh (default on macOS)
source ~/.zshrc

# For bash
source ~/.bashrc
```

### 3. Verify installation

```bash
# Check commands are available
which code-index
# Expected: /Users/djalmaaraujo/bin/code-index

which ss
# Expected: /Users/djalmaaraujo/bin/ss

which cc
# Expected: /Users/djalmaaraujo/bin/cc
```

## Using It on Any Codebase

### The Magic ✨

The CLI commands now work **from any directory** without activating the venv!

```bash
# Go to ANY project
cd ~/projects/my-awesome-app

# Index it (first time)
code-index .

# Search it
ss "authentication logic"

# More results
ss "database connection" -n 10

# Use with Claude
cc "explain the authentication flow"
```

### How It Works

1. **Symlinks**: `~/bin/code-index` → `~/dev/claude-indexer/bin/code-index`
2. **Auto-activation**: Scripts automatically use the venv's Python
3. **Indexes stored**: `~/.code-search/indexes/{project-hash}/`

Each project gets its own index, so you can index multiple codebases!

## Manual Installation (Alternative)

If you prefer to install dependencies manually:

```bash
# 1. Create virtual environment
cd ~/dev/claude-indexer
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -e .

# 3. Create symlinks
mkdir -p ~/bin
ln -sf $(pwd)/bin/code-index ~/bin/code-index
ln -sf $(pwd)/bin/ss ~/bin/ss
ln -sf $(pwd)/bin/cc ~/bin/cc

# 4. Add to PATH (add this to ~/.zshrc)
export PATH="$HOME/bin:$PATH"
```

## Troubleshooting

### Command not found

```bash
# Check if ~/bin is in PATH
echo $PATH | grep "$HOME/bin"

# If not, add to ~/.zshrc or ~/.bashrc
echo 'export PATH="$HOME/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### Import errors

```bash
# Make sure venv exists and has dependencies
cd ~/dev/claude-indexer
source venv/bin/activate
pip install -e .
```

### Model download issues

```bash
# The sentence-transformers model downloads automatically on first use
# If you have network issues, you can manually download it:
python3 -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
```

## Example Workflow

### First Time Setup
```bash
# 1. Install
cd ~/dev/claude-indexer
./setup.sh
source ~/.zshrc

# 2. Test on this project
cd ~/dev/claude-indexer
code-index src/

# 3. Search
ss "embedding"
ss "vector search" -n 5
```

### Daily Usage
```bash
# Navigate to any project
cd ~/projects/my-app

# First time: index it
code-index .

# Search anytime
ss "authentication"
ss "api endpoint" -n 10

# With Claude
cc "find the user authentication logic"
cc "explain how database connections work"

# Re-index after changes (automatic incremental)
code-index .

# Force full re-index
code-index . --force
```

## Uninstall

```bash
# Remove symlinks
rm ~/bin/code-index ~/bin/ss ~/bin/cc

# Remove indexes
rm -rf ~/.code-search

# Remove the project
rm -rf ~/dev/claude-indexer
```

## Next Steps

- Read [README.md](README.md) for full documentation
- Run `pytest tests/` to verify everything works
- Run `./benchmark.py src/` to see performance
- Index your favorite projects!
