#!/usr/bin/env bash
# SessionStart hook: checks if there are ready items in the work queue
# and outputs a reminder for Claude to dispatch them.

WORK_QUEUE="$HOME/.claude/work-queue.json"

if [ ! -f "$WORK_QUEUE" ]; then
    exit 0
fi

# Count ready items
READY_COUNT=$(jq '[.[] | select(.status == "ready")] | length' "$WORK_QUEUE" 2>/dev/null)

if [ "$READY_COUNT" -gt 0 ]; then
    echo "Work queue has $READY_COUNT ready item(s). Read ~/.claude/work-queue.json and dispatch all ready tasks now."
fi
