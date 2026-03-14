# claude-swarm

Turn Claude Code into a smart multi-agent dispatcher.

claude-swarm transforms your Claude Code session into a project manager that reads your available agents, composes the right team for each task, dispatches work to isolated worktrees, and tracks everything in a persistent work queue that survives across sessions.

## What it does

- **Smart team composition** -- scans `~/.claude/agents/` to discover your installed specialists, then picks the right agents for each task like a hiring manager staffing a project
- **Persistent work queue** -- a JSON file (`~/.claude/work-queue.json`) tracks tasks across sessions, solving the problem that native Claude Code teams are session-scoped
- **Hybrid dispatch** -- uses native TeamCreate/SendMessage/TaskCreate when agents need to coordinate, plain Agent calls when they don't
- **Auto-dispatch on session start** -- a SessionStart hook checks the queue and dispatches ready items automatically
- **Agent-agnostic** -- works with whatever agents you have installed (zero or a hundred)

## Install

### From a local directory

```bash
git clone https://github.com/your-org/claude-swarm.git
claude plugin install --path ./claude-swarm
```

Or load it for a single session:

```bash
claude --plugin-dir ./claude-swarm
```

### Uninstall

```bash
claude plugin uninstall claude-swarm
```

Your work queue (`~/.claude/work-queue.json`) is never deleted by uninstall.

## How it works

1. You describe a task to Claude
2. The dispatcher scans `~/.claude/agents/` to see what specialists are available
3. It matches task requirements to agent capabilities and composes the right team
4. Work gets dispatched to background agents in isolated git worktrees
5. Results come back, the queue gets updated, and you get a report

The main session never does implementation work directly. It stays in dispatcher mode: discussing requirements, refining task descriptions, composing teams, and managing the queue.

## Work queue

The queue lives at `~/.claude/work-queue.json`. You can edit it directly or let Claude manage it.

### Single agent task

```json
{
  "id": "001",
  "title": "Fix login redirect loop",
  "description": "After OAuth callback, users hit an infinite redirect. Check the callback handler and session storage logic.",
  "dispatch": "agent",
  "project": "/home/user/code/my-app",
  "status": "ready",
  "priority": 1
}
```

### Team task

```json
{
  "id": "002",
  "title": "Add search feature",
  "description": "Full-text search across posts. Backend indexes content, frontend shows results.",
  "dispatch": "team",
  "team": [
    {
      "role": "backend",
      "agent_type": "backend-architect",
      "project": "/home/user/code/my-api",
      "description": "Add GET /api/search?q=term. Return { results: [{ id, title, snippet, score }] }."
    },
    {
      "role": "frontend",
      "agent_type": "frontend-developer",
      "project": "/home/user/code/my-web",
      "description": "Add SearchComponent with debounced input. Call GET /api/search?q=term. Display results as cards."
    }
  ],
  "status": "ready",
  "priority": 1
}
```

### Status values

| Status | Meaning |
|--------|---------|
| `ready` | Queued, will dispatch on next session start or immediately if session is active |
| `in-progress` | Agent(s) spawned and working |
| `done` | Complete, branch/PR recorded |
| `failed` | Agent hit an unrecoverable issue |

### Auto dispatch

Set `"dispatch": "auto"` (or omit the field) and the dispatcher decides whether to use a single agent or a team based on task complexity.

## How it composes teams

The dispatcher takes a "hiring manager" approach:

1. **Reads your roster** -- scans `~/.claude/agents/` and reads each agent's `.md` file to understand its name, description, model tier, and specialties
2. **Matches to the task** -- if you have a `java-specialist` agent and the task is a Spring Boot bug, it picks that agent
3. **Picks the smallest effective team** -- doesn't over-hire; a focused bug fix gets one agent, not three
4. **Considers cost** -- uses expensive Opus agents for critical work, cheaper Haiku/Sonnet agents for routine tasks
5. **Falls back gracefully** -- if no specialist fits, uses a general-purpose agent with role-specific prompts; if no agents are installed at all, dispatches with the default Agent tool

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
│   └── check-queue.sh        Hook script that detects ready items
├── examples/
│   └── work-queue.json       Example work queue with sample tasks
├── LICENSE
└── README.md
```

## Prerequisites

- Claude Code installed
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
