# claude-swarm

Turn Claude Code into a smart multi-agent dispatcher.

claude-swarm transforms your Claude Code session into a project manager that reads your available agents, composes the right team for each task, dispatches work to isolated worktrees, and tracks everything in a persistent work queue that survives across sessions.

## What it does

- **Smart team composition** -- scans `~/.claude/agents/` to discover your installed specialists, then picks the best agents for each task based on their capabilities
- **Persistent work queue** -- a JSON file (`~/.claude/work-queue.json`) tracks tasks across sessions, solving the problem that native Claude Code teams are session-scoped
- **Hybrid dispatch** -- uses native TeamCreate/SendMessage/TaskCreate when agents need to coordinate, plain Agent calls when they don't
- **Auto-dispatch on session start** -- a SessionStart hook checks the queue and dispatches ready items automatically
- **Agent-agnostic** -- works with whatever agents you have installed (zero or a hundred)

## Install

```bash
git clone https://github.com/afspear-llc/claude-swarm.git
claude plugin install --path ./claude-swarm
```

Or load it for a single session:

```bash
claude --plugin-dir ./claude-swarm
```

Uninstall with `claude plugin uninstall claude-swarm`. Your work queue is never deleted.

## How it works

1. You describe a task to Claude
2. The dispatcher scans `~/.claude/agents/` to see what specialists are available
3. It matches task requirements to agent capabilities and composes the right team
4. Work gets dispatched to background agents in isolated git worktrees
5. Results come back, the queue gets updated, and you get a report

The main session never does implementation work directly. It stays in dispatcher mode: discussing requirements, refining task descriptions, composing teams, and managing the queue.

## Usage

### Starting a session

The plugin's SessionStart hook automatically checks the queue and dispatches any `"ready"` items. Just start Claude Code normally.

```
$ claude
Claude: Found 2 ready items in work queue. Dispatching...
  #007 → backend agent: "Add pagination to /api/posts"
  #008 → debugger agent: "Fix 500 on empty cart checkout"
```

### Adding tasks

Describe what you want in plain language. The dispatcher writes it to the queue (see [Work queue](#work-queue) for format), picks the right agent(s), and launches them.

```
You: "The options chain endpoint is returning stale data"
Claude: Dispatched #009 → debugger: "Fix stale options chain cache TTL"

... (agent investigates, fixes, tests in background) ...

Claude: #009 done — reduced cache TTL from 24h to 15min, branch: fix/stale-options-cache
```

For cross-cutting work, the dispatcher composes a team automatically:

```
You: "Add a search feature — backend indexes posts, frontend shows results"
Claude: Dispatched #010 as team:
  backend → java-specialist: "Add GET /api/search endpoint"
  frontend → angular-specialist: "Add SearchComponent with results"
```

You can also edit `~/.claude/work-queue.json` directly -- add an entry with `"status": "ready"` and it will be picked up on the next session start.

### Checking status and reviewing results

```
You: "What's the status?"
Claude: #008 done — branch: fix/empty-cart-500
        #009 in-progress — debugger working
        #010 ready — queued, not yet dispatched

You: "Show me what #008 changed"
Claude: Branch fix/empty-cart-500: added null check in CartController,
        added test for empty cart edge case. All 47 tests passing.
```

### Quick dispatch with `/queue`

Create a skill at `~/.claude/skills/queue/SKILL.md` for fire-and-forget dispatch:

```markdown
# /queue — Quick task dispatch
When the user runs `/queue <description>`:
1. Read ~/.claude/work-queue.json (create as [] if missing)
2. Assign next ID, infer title and agent_type from description
3. Add with status "in-progress", dispatch immediately
4. Report task ID and agent in one line. No confirmation needed.
```

```
You: /queue fix the login redirect bug in auth
Claude: Dispatched #004 → debugger: "Fix login redirect loop"
```

### Merging work

```
You: "Merge #008 and #009 to main"
Claude: Merged fix/empty-cart-500 (fast-forward)
        Merged fix/stale-options-cache (clean merge)
        Branches cleaned up, queue updated.
```

## Team mode

Native Claude Code teams for coordinated multi-agent work. Multiple named agents run concurrently, message each other via `SendMessage`, and share a task board via `TaskCreate`/`TaskUpdate`. Unlike independent dispatch, team agents can agree on API contracts and handle dependent subtasks in real time.

### When to use teams vs single-agent dispatch

| Use single-agent dispatch when... | Use team mode when... |
|---|---|
| The task is self-contained (one repo, one concern) | The task spans multiple codebases |
| No coordination is needed — just "go fix this" | Agents need to agree on interfaces or contracts |
| You want fast, independent bug fixes or features | Subtasks have dependencies (backend must finish before frontend) |
| Cost matters — teams use more tokens | Real-time coordination produces better results than async handoff |

Requires the experimental flag `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`. The plugin's SessionStart hook auto-enables this in `~/.claude/settings.json` on every launch. Restart Claude Code if you see the first-time enablement message.

## Work queue

The queue lives at `~/.claude/work-queue.json`. The dispatcher manages it through `scripts/queue.sh`, a jq-based CLI that keeps queue updates compact (one-line confirmations instead of dumping the full JSON file).

### Queue CLI

The dispatcher uses this automatically. You can also run it directly:

```bash
# From the plugin directory
./scripts/queue.sh list                     # All tasks (id, status, title)
./scripts/queue.sh list ready               # Filter by status
./scripts/queue.sh add "Title" "Description" "/project/path"
./scripts/queue.sh add-team "Title" "Desc" '[{"role":"be","project":"/path","description":"..."}]'
./scripts/queue.sh update 001 status done
./scripts/queue.sh update 001 branch fix/my-branch
./scripts/queue.sh remove 001
```

Requires `jq`. Output is always a one-liner: `✓ #001 status → done`.

### Task format

```json
{
  "id": "001",
  "title": "Fix login redirect loop",
  "description": "After OAuth callback, users hit an infinite redirect.",
  "dispatch": "agent",
  "project": "/home/user/code/my-app",
  "status": "ready",
  "priority": 1
}
```

For team tasks, replace `project` with a `team` array:

```json
{
  "id": "002",
  "title": "Add search feature",
  "description": "Full-text search across posts.",
  "dispatch": "team",
  "team": [
    { "role": "backend", "project": "/home/user/code/my-api", "description": "Add GET /api/search?q=term." },
    { "role": "frontend", "project": "/home/user/code/my-web", "description": "Add SearchComponent, call /api/search." }
  ],
  "status": "ready",
  "priority": 1
}
```

Set `"dispatch": "auto"` (or omit it) and the dispatcher decides single vs team based on task complexity.

### Status values

| Status | Meaning |
|--------|---------|
| `ready` | Queued, dispatches on next session start or immediately if active |
| `in-progress` | Agent(s) spawned and working |
| `done` | Complete, branch/PR recorded |
| `failed` | Agent hit an unrecoverable issue |

## How it composes teams

The dispatcher scans `~/.claude/agents/` to read each agent's capabilities, matches them to the task, and picks the smallest effective team. It uses expensive Opus agents for critical work and cheaper Haiku/Sonnet agents for routine tasks. If no specialist fits, it falls back to a general-purpose agent; if no agents are installed at all, it dispatches with the default Agent tool.

## Plugin structure

```
claude-swarm/
├── .claude-plugin/
│   └── plugin.json           Plugin manifest
├── skills/
│   └── dispatch/
│       └── SKILL.md          Dispatcher instructions (the core brain)
├── hooks/
│   └── hooks.json            SessionStart hook to auto-check the queue
├── scripts/
│   ├── check-queue.sh        Hook script that detects ready items
│   └── queue.sh              CLI for queue operations (add, update, remove, list)
├── examples/
│   └── work-queue.json       Example work queue with sample tasks
├── LICENSE
└── README.md
```

## Prerequisites

- Claude Code installed
- `jq` installed (used by `queue.sh` for JSON manipulation)
- **Agent teams flag** -- the plugin auto-enables `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in `~/.claude/settings.json` on each launch
- Optionally, agent definitions in `~/.claude/agents/` (works without them using general-purpose dispatch)

## Development

To test changes locally:

```bash
claude --plugin-dir ./claude-swarm
```

Run `/reload-plugins` inside Claude Code to pick up changes without restarting.

## Tips

- **Be specific about "done"** -- include acceptance criteria, not just goals
- **Define contracts for teams** -- put the shared API schema in each agent's description so they can work independently
- **One concern per agent** -- don't overload agents with unrelated work
- **Trust the agents** -- give them the goal and constraints, let them figure out the implementation

## License

MIT
