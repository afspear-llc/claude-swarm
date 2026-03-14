#!/usr/bin/env bash
# SessionStart hook: checks if there are ready items in the work queue
# and reminds Claude to dispatch them.
# Also ensures the CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS flag is enabled
# in ~/.claude/settings.json (required for native team tools).

WORK_QUEUE="$HOME/.claude/work-queue.json"
SETTINGS_FILE="$HOME/.claude/settings.json"

# --- Ensure agent teams flag is enabled in Claude Code settings ---
ensure_teams_flag() {
    # If settings file doesn't exist, create it with the flag
    if [ ! -f "$SETTINGS_FILE" ]; then
        mkdir -p "$HOME/.claude"
        cat > "$SETTINGS_FILE" <<'ENDJSON'
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  }
}
ENDJSON
        echo "claude-swarm: Created $SETTINGS_FILE with CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1. Restart Claude Code for it to take effect."
        return
    fi

    # Check if the flag is already set to "1"
    if command -v jq &>/dev/null; then
        CURRENT_VALUE=$(jq -r '.env.CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS // ""' "$SETTINGS_FILE" 2>/dev/null)
        if [ "$CURRENT_VALUE" = "1" ]; then
            return  # Already set, nothing to do
        fi
        # Merge the flag into existing settings (preserves all other keys)
        UPDATED=$(jq '.env = (.env // {}) + {"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"}' "$SETTINGS_FILE" 2>/dev/null)
        if [ $? -eq 0 ] && [ -n "$UPDATED" ]; then
            echo "$UPDATED" > "$SETTINGS_FILE"
            echo "claude-swarm: Enabled CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 in $SETTINGS_FILE. Restart Claude Code for it to take effect."
        fi
    else
        # Fallback without jq: check with grep, update with python or sed
        if grep -q '"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS"[[:space:]]*:[[:space:]]*"1"' "$SETTINGS_FILE" 2>/dev/null; then
            return  # Already set
        fi

        # Try python3 first (safe JSON merge)
        if command -v python3 &>/dev/null; then
            python3 -c "
import json, sys
with open('$SETTINGS_FILE', 'r') as f:
    data = json.load(f)
data.setdefault('env', {})['CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS'] = '1'
with open('$SETTINGS_FILE', 'w') as f:
    json.dump(data, f, indent=2)
" 2>/dev/null
            if [ $? -eq 0 ]; then
                echo "claude-swarm: Enabled CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 in $SETTINGS_FILE. Restart Claude Code for it to take effect."
                return
            fi
        fi

        # Last resort: if "env" key exists, insert the flag into it with sed
        if grep -q '"env"' "$SETTINGS_FILE" 2>/dev/null; then
            sed -i 's/"env"[[:space:]]*:[[:space:]]*{/"env": {\n    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1",/' "$SETTINGS_FILE" 2>/dev/null
            echo "claude-swarm: Enabled CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 in $SETTINGS_FILE (sed fallback). Restart Claude Code for it to take effect."
        else
            echo "claude-swarm: WARNING -- Could not auto-enable CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS. Please add '\"env\": {\"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS\": \"1\"}' to $SETTINGS_FILE manually."
        fi
    fi
}

ensure_teams_flag

# --- Check work queue for ready items ---
if [ ! -f "$WORK_QUEUE" ]; then
    exit 0
fi

# Count ready items (requires jq)
if ! command -v jq &>/dev/null; then
    # Fallback: simple grep check if jq is not installed
    if grep -q '"status"[[:space:]]*:[[:space:]]*"ready"' "$WORK_QUEUE" 2>/dev/null; then
        echo "Work queue has ready items. Read ~/.claude/work-queue.json and dispatch all ready tasks now."
    fi
    exit 0
fi

READY_COUNT=$(jq '[.[] | select(.status == "ready")] | length' "$WORK_QUEUE" 2>/dev/null)

if [ "$READY_COUNT" -gt 0 ]; then
    echo "Work queue has $READY_COUNT ready item(s). Read ~/.claude/work-queue.json and dispatch all ready tasks now."
fi
