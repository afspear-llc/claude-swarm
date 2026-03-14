# Work Queue

The work queue is a JSON file at `~/.claude/work-queue.json`. It is the persistent, cross-session source of truth for all tasks. Native Claude Code teams are session-scoped and disappear when you close the terminal. The work queue survives.

## Queue CLI

All queue reads and writes go through `scripts/queue.sh`. Never edit `work-queue.json` directly with a text editor or the Write/Edit tools -- the script handles atomic writes and validation.

### Locating the Script

The dispatcher finds the script at its plugin install path:

```bash
QUEUE_SH="$(dirname "$(find ~/.claude/skills -name queue.sh -path '*/claude-swarm/*' 2>/dev/null | head -1)")/queue.sh"
```

### Commands

```bash
# List all tasks (tab-separated: id, status, title)
$QUEUE_SH list

# List tasks filtered by status
$QUEUE_SH list ready
$QUEUE_SH list in-progress
$QUEUE_SH list done

# Add a single-agent task
$QUEUE_SH add "Fix login bug" "JWT refresh not triggering after 5min" "/home/user/code/my-app"

# Add with explicit dispatch mode and priority
$QUEUE_SH add "Fix login bug" "JWT refresh not triggering" "/home/user/code/my-app" agent 1

# Add a team task
$QUEUE_SH add-team "Add search" "Full-text search" '[{"role":"backend","project":"/home/user/code/api","description":"Add GET /api/search"}]'

# Update a field on a task
$QUEUE_SH update 001 status in-progress
$QUEUE_SH update 001 status done
$QUEUE_SH update 001 branch fix/login-bug
$QUEUE_SH update 001 error "Build failed on test suite"

# Remove a task
$QUEUE_SH remove 001

# Get the next available numeric ID
$QUEUE_SH next-id
```

Output is always a one-liner: `✓ #001 status -> done`. The script never dumps the full JSON file.

Requires `jq` for all operations.

## Task Format

### Single-Agent Task

```json
{
  "id": "001",
  "title": "Fix authentication timeout",
  "description": "Users getting logged out after 5 minutes. JWT refresh not triggering. Check token expiry handling in AuthService. Acceptance criteria: users stay logged in for 1 hour of activity, refresh fires before expiry, unit tests for refresh logic.",
  "dispatch": "agent",
  "project": "/home/user/code/my-app",
  "status": "ready",
  "priority": 1
}
```

### Team Task

Replace `project` with a `team` array. Each member gets its own project path and role-specific instructions.

```json
{
  "id": "002",
  "title": "Add user profile page",
  "description": "Full-stack feature: backend API + frontend page.",
  "dispatch": "team",
  "team": [
    {
      "role": "backend",
      "project": "/home/user/code/my-api",
      "description": "Add GET/PUT /api/profile. Return { name, email, avatar_url, preferences: { theme, notifications } }. Unit tests for service and controller."
    },
    {
      "role": "frontend",
      "project": "/home/user/code/my-web",
      "description": "Add ProfileComponent at /profile. Call GET /api/profile on load, PUT on save. API contract: { name, email, avatar_url, preferences: { theme, notifications } }."
    }
  ],
  "status": "ready",
  "priority": 2
}
```

### Field Reference

| Field | Required | Description |
|-------|----------|-------------|
| `id` | Yes | Unique identifier. Numeric IDs are zero-padded (`"001"`). Free-form strings also work (`"fix-auth"`). |
| `title` | Yes | Short human-readable summary. |
| `description` | Yes | Detailed instructions and acceptance criteria. This is what the agent sees. |
| `dispatch` | No | `"agent"`, `"team"`, or `"auto"`. Default: `"auto"` -- the dispatcher decides. |
| `project` | Yes* | Absolute path to the project root. *Not used when `dispatch` is `"team"` -- set on each team member instead. |
| `team` | Yes* | Array of team members. *Required when `dispatch` is `"team"`. |
| `status` | Yes | One of: `"ready"`, `"in-progress"`, `"done"`, `"failed"`. |
| `priority` | No | Lower number = higher priority. Informational only -- all ready items dispatch concurrently. |
| `branch` | No | Set by the dispatcher on completion. Git branch name or PR URL. |
| `error` | No | Set by the dispatcher on failure. Brief explanation of what went wrong. |
| `agent_type` | No | Legacy field. If present, used as a hint. The dispatcher picks the best agent regardless. |

### Team Member Fields

| Field | Required | Description |
|-------|----------|-------------|
| `role` | Yes | Short label: `"backend"`, `"frontend"`, `"tests"`, etc. |
| `project` | Yes | Absolute path to the project this agent works in. |
| `description` | Yes | Role-specific instructions for this agent. Include shared contracts here. |

## Status Lifecycle

```
ready --> in-progress --> done
                     \-> failed
```

- **ready** -- Queued, waiting for dispatch. Picked up on session start or dispatched immediately during an active session.
- **in-progress** -- Agent(s) spawned and working in background worktrees.
- **done** -- Work complete. The `branch` field records where the changes live.
- **failed** -- Agent hit an unrecoverable issue. The `error` field explains what happened.

## Legacy Compatibility

Old-format queue items still work:

- If a task has `agent_type` but no `dispatch` field, it is treated as `dispatch: "agent"`.
- If a task has a `team` array but no `dispatch` field, it is treated as `dispatch: "team"`.
- No migration needed for existing queues.

## Manual Queue Editing

You can add tasks by editing `~/.claude/work-queue.json` directly (outside of Claude). Add an entry with `"status": "ready"` and it will be picked up on the next session start. This is useful for scripting or CI integration.
