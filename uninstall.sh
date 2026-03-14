#!/usr/bin/env bash
set -euo pipefail

CLAUDE_MD="$HOME/.claude/CLAUDE.md"
WORK_QUEUE="$HOME/.claude/work-queue.json"

BEGIN_MARKER="<!-- CLAUDE-SWARM-BEGIN -->"
END_MARKER="<!-- CLAUDE-SWARM-END -->"

if [ ! -f "$CLAUDE_MD" ]; then
    echo "Nothing to uninstall: $CLAUDE_MD does not exist."
    exit 0
fi

if ! grep -q "$BEGIN_MARKER" "$CLAUDE_MD" 2>/dev/null; then
    echo "Nothing to uninstall: no Claude Swarm config found in $CLAUDE_MD"
    exit 0
fi

# Remove the block between markers (inclusive) and any trailing blank line
TMPFILE=$(mktemp)
awk -v begin="$BEGIN_MARKER" -v end="$END_MARKER" '
    $0 == begin { skip=1; next }
    $0 == end { skip=0; next }
    !skip { print }
' "$CLAUDE_MD" > "$TMPFILE"
mv "$TMPFILE" "$CLAUDE_MD"

# Clean up any leftover empty lines at end of file
sed -i -e :a -e '/^\n*$/{$d;N;ba' -e '}' "$CLAUDE_MD"

echo "Claude Swarm config removed from $CLAUDE_MD"
echo ""

if [ -f "$WORK_QUEUE" ]; then
    echo "Note: $WORK_QUEUE was left in place (it contains your task data)."
    echo "      Delete it manually if you no longer need it: rm $WORK_QUEUE"
fi

echo ""
echo "Claude Swarm uninstalled successfully."
