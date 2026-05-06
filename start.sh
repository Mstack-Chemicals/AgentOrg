#!/usr/bin/env bash
set -euo pipefail

# agentorg start — one-command launcher
# Usage: ./start.sh  (or: curl -sL <url>/start.sh | bash)

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

info()  { echo -e "${GREEN}[agentorg]${NC} $1"; }
warn()  { echo -e "${YELLOW}[agentorg]${NC} $1"; }
error() { echo -e "${RED}[agentorg]${NC} $1"; }

# -------------------------------------------------------------------
# 1. Check prerequisites
# -------------------------------------------------------------------

missing=0

# Python
if ! command -v python3 &>/dev/null; then
    error "python3 not found. Install Python 3.10+."
    missing=1
fi

# Claude Code CLI
if ! command -v claude &>/dev/null; then
    error "claude CLI not found. Install Claude Code: https://docs.anthropic.com/en/docs/claude-code"
    missing=1
fi

# ANTHROPIC_API_KEY
if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
    warn "ANTHROPIC_API_KEY not set. Success criteria auto-generation will be unavailable."
    warn "Set it with: export ANTHROPIC_API_KEY=sk-ant-..."
fi

if [ "$missing" -eq 1 ]; then
    error "Missing prerequisites. Fix the above and re-run."
    exit 1
fi

# -------------------------------------------------------------------
# 2. Install agentorg if not present
# -------------------------------------------------------------------

if ! command -v agentorg &>/dev/null; then
    info "Installing agentorg..."
    pip install agentorg
fi

info "agentorg $(agentorg version 2>&1 | head -1)"

# -------------------------------------------------------------------
# 3. Run agentorg init
# -------------------------------------------------------------------

info "Initialising project..."
agentorg init

# -------------------------------------------------------------------
# 4. Check for objective.md
# -------------------------------------------------------------------

if [ ! -f "objective.md" ]; then
    echo ""
    warn "objective.md not found."
    echo ""
    echo "  Create your objective.md using the template as a schema reference:"
    echo "    - See objective.template.md for the required format"
    echo "    - Use any tool to generate it from an existing PRD"
    echo "    - Drop objective.md into this directory"
    echo ""
    echo "  Waiting for objective.md..."
    echo ""

    # Poll for objective.md
    while [ ! -f "objective.md" ]; do
        sleep 2
    done

    info "objective.md detected!"
    sleep 1  # brief pause for file to finish writing
fi

# -------------------------------------------------------------------
# 5. Run agentorg run
# -------------------------------------------------------------------

info "Starting run..."
echo ""
agentorg run

# -------------------------------------------------------------------
# 6. Launch Claude with CTO agent
# -------------------------------------------------------------------

echo ""
info "Launching CTO agent..."
echo ""

claude --agent cto "Read .agentorg/runs/latest/init-context.md and begin the run."
