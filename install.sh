#!/usr/bin/env bash
set -euo pipefail

CLAUDE_DIR="$HOME/.claude"
CLAUDE_MD="$CLAUDE_DIR/CLAUDE.md"
WORK_QUEUE="$CLAUDE_DIR/work-queue.json"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SWARM_CONTENT="$SCRIPT_DIR/swarm.md"

BEGIN_MARKER="<!-- CLAUDE-SWARM-BEGIN -->"
END_MARKER="<!-- CLAUDE-SWARM-END -->"

# Ensure ~/.claude/ exists
mkdir -p "$CLAUDE_DIR"

# Ensure CLAUDE.md exists
if [ ! -f "$CLAUDE_MD" ]; then
    touch "$CLAUDE_MD"
fi

# Read swarm.md content
CONTENT=$(cat "$SWARM_CONTENT")

# Build the block to inject
BLOCK="${BEGIN_MARKER}
${CONTENT}
${END_MARKER}"

# Check if markers already exist
if grep -q "$BEGIN_MARKER" "$CLAUDE_MD" 2>/dev/null; then
    # Replace existing content between markers (inclusive)
    TMPFILE=$(mktemp)
    BLOCKFILE=$(mktemp)
    printf '%s\n' "$BLOCK" > "$BLOCKFILE"
    awk -v begin="$BEGIN_MARKER" -v end="$END_MARKER" -v blockfile="$BLOCKFILE" '
        $0 == begin { while ((getline line < blockfile) > 0) print line; skip=1; next }
        $0 == end { skip=0; next }
        !skip { print }
    ' "$CLAUDE_MD" > "$TMPFILE"
    mv "$TMPFILE" "$CLAUDE_MD"
    rm -f "$BLOCKFILE"
    echo "Updated existing Claude Swarm config in $CLAUDE_MD"
else
    # Append to file
    printf "\n%s\n" "$BLOCK" >> "$CLAUDE_MD"
    echo "Added Claude Swarm config to $CLAUDE_MD"
fi

# Create empty work queue if it doesn't exist
if [ ! -f "$WORK_QUEUE" ]; then
    echo "[]" > "$WORK_QUEUE"
    echo "Created empty work queue at $WORK_QUEUE"
else
    echo "Work queue already exists at $WORK_QUEUE (left unchanged)"
fi

echo ""
echo "Claude Swarm installed successfully."
echo ""
echo "Usage:"
echo "  1. Add tasks to ~/.claude/work-queue.json (or ask Claude to add them)"
echo "  2. Start Claude Code -- it will auto-dispatch all 'ready' tasks"
echo "  3. Claude becomes the dispatcher: it discusses, refines, and dispatches"
echo "     but never does hands-on implementation itself"
echo ""
echo "To uninstall: ./uninstall.sh"
