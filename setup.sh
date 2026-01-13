#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Timing
START_TIME=$(date +%s)

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Fast Semantic Code Search Setup${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Track what we installed
INSTALLED=()

# 1. Check/Install Homebrew
echo -e "${YELLOW}[1/5]${NC} Checking Homebrew..."
if ! command -v brew &> /dev/null; then
    echo -e "${YELLOW}Installing Homebrew...${NC}"
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    INSTALLED+=("Homebrew")
else
    echo -e "${GREEN}✓ Homebrew already installed${NC}"
fi

# 2. Check/Install Python 3.11+
echo -e "\n${YELLOW}[2/5]${NC} Checking Python 3.11+..."
PYTHON_CMD=""
if command -v python3.11 &> /dev/null; then
    PYTHON_CMD="python3.11"
elif command -v python3.12 &> /dev/null; then
    PYTHON_CMD="python3.12"
elif command -v python3 &> /dev/null; then
    VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
    MAJOR=$(echo $VERSION | cut -d'.' -f1)
    MINOR=$(echo $VERSION | cut -d'.' -f2)
    if [ "$MAJOR" -eq 3 ] && [ "$MINOR" -ge 11 ]; then
        PYTHON_CMD="python3"
    fi
fi

if [ -z "$PYTHON_CMD" ]; then
    echo -e "${YELLOW}Installing Python 3.12...${NC}"
    brew install python@3.12
    PYTHON_CMD="python3.12"
    INSTALLED+=("Python 3.12")
else
    echo -e "${GREEN}✓ Python $($PYTHON_CMD --version | cut -d' ' -f2) found${NC}"
fi

# 3. Create and setup virtual environment
echo -e "\n${YELLOW}[3/5]${NC} Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    $PYTHON_CMD -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${GREEN}✓ Virtual environment exists${NC}"
fi

# Activate venv and install dependencies
echo -e "${YELLOW}Installing Python dependencies...${NC}"
source venv/bin/activate
pip install --upgrade pip > /dev/null 2>&1
pip install -e ".[dev]" || {
    echo -e "${YELLOW}Note: Will install dependencies after pyproject.toml is created${NC}"
}

# 4. Create symlinks
echo -e "\n${YELLOW}[4/5]${NC} Creating CLI symlinks..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$HOME/bin"

# Create ~/bin if it doesn't exist
mkdir -p "$BIN_DIR"

# Make bin scripts executable
chmod +x bin/* 2>/dev/null || echo "Note: CLI scripts will be created later"

# Create symlinks
for cmd in code-index ss cc; do
    if [ -f "$SCRIPT_DIR/bin/$cmd" ]; then
        ln -sf "$SCRIPT_DIR/bin/$cmd" "$BIN_DIR/$cmd"
        echo -e "${GREEN}✓ Linked $cmd${NC}"
    fi
done

# Add ~/bin to PATH if not already there
if [[ ":$PATH:" != *":$HOME/bin:"* ]]; then
    echo -e "\n${YELLOW}Adding ~/bin to PATH...${NC}"

    # Detect shell
    if [ -n "$ZSH_VERSION" ]; then
        SHELL_RC="$HOME/.zshrc"
    elif [ -n "$BASH_VERSION" ]; then
        SHELL_RC="$HOME/.bashrc"
    else
        SHELL_RC="$HOME/.profile"
    fi

    echo 'export PATH="$HOME/bin:$PATH"' >> "$SHELL_RC"
    echo -e "${GREEN}✓ Added to $SHELL_RC${NC}"
    echo -e "${YELLOW}Run: source $SHELL_RC${NC}"
fi

# 5. Run self-test
echo -e "\n${YELLOW}[5/5]${NC} Running self-test..."
TEST_PASSED=true

# Test Python environment
echo -n "  Testing Python environment... "
if $PYTHON_CMD -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" 2>/dev/null; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    TEST_PASSED=false
fi

# Calculate timing
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

# Summary
echo -e "\n${BLUE}========================================${NC}"
echo -e "${BLUE}Setup Complete!${NC}"
echo -e "${BLUE}========================================${NC}\n"

if [ ${#INSTALLED[@]} -gt 0 ]; then
    echo -e "${GREEN}Installed:${NC}"
    for item in "${INSTALLED[@]}"; do
        echo -e "  • $item"
    done
    echo ""
fi

echo -e "${GREEN}Setup time: ${DURATION}s${NC}\n"

if [ "$TEST_PASSED" = true ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}\n"
    echo -e "Next steps:"
    echo -e "  1. source venv/bin/activate"
    echo -e "  2. cd to your codebase"
    echo -e "  3. code-index .              # Index the codebase"
    echo -e "  4. ss 'your query'           # Search semantically"
    echo -e "  5. cc 'find something'       # Search + send to Claude"
else
    echo -e "${YELLOW}⚠ Some tests failed. Please check the output above.${NC}\n"
fi

echo -e "${BLUE}========================================${NC}\n"
