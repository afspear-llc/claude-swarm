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

## Usage

### Starting a session

Open Claude Code in any project. The plugin's SessionStart hook automatically checks `~/.claude/work-queue.json` and dispatches any items with `"status": "ready"`. You don't need to do anything — just start working.

```
$ claude
Claude: Found 2 ready items in work queue. Dispatching...
  #007 → backend agent: "Add pagination to /api/posts"
  #008 → debugger agent: "Fix 500 on empty cart checkout"
```

### Adding tasks conversationally

Describe what you want done in plain language. The dispatcher writes it to the queue, picks the right agent(s), and launches them in background worktrees.

```
You: "The options chain endpoint is returning stale data — looks like
      the cache TTL is too long. Can you fix it?"
Claude: Dispatched #009 → debugger: "Fix stale options chain cache TTL"
        Working in worktree on branch fix/stale-options-cache

... (agent investigates, fixes, tests in background) ...

Claude: #009 done — reduced cache TTL from 24h to 15min in
        OptionsChainService.java, branch: fix/stale-options-cache
```

For cross-cutting work, the dispatcher composes a team automatically:

```
You: "Add a search feature — backend should index posts, frontend
      should show results with a search bar"
Claude: Dispatched #010 as team:
  backend → java-specialist: "Add GET /api/search endpoint"
  frontend → angular-specialist: "Add SearchComponent with results"
```

### Adding tasks manually

Edit `~/.claude/work-queue.json` directly. Add an entry with `"status": "ready"` and it will be picked up on the next session start or when you ask the dispatcher to check the queue.

```json
{
  "id": "011",
  "title": "Add rate limiting to public endpoints",
  "description": "Apply 60 req/min per IP to all /api/public/** endpoints. Return 429 with Retry-After header.",
  "project": "/home/user/code/my-api",
  "status": "ready",
  "priority": 1
}
```

### Checking status

Ask the dispatcher what's happening. It reads the queue and reports back.

```
You: "What's the status of everything?"
Claude: Work queue status:
  #007 in-progress — "Add pagination to /api/posts" (backend agent working)
  #008 done — "Fix 500 on empty cart checkout" → branch: fix/empty-cart-500
  #009 done — "Fix stale options chain cache TTL" → branch: fix/stale-options-cache
  #010 in-progress — "Add search feature" (team: backend done, frontend working)
  #011 ready — "Add rate limiting to public endpoints" (queued, not yet dispatched)
```

### Reviewing results

When agents finish, they report back with what they changed and which branch holds the work. You can review diffs, run tests, or ask follow-up questions.

```
You: "Show me what #008 changed"
Claude: Branch fix/empty-cart-500 has 1 commit:
  - CartController.java: added null check for empty cart items
  - CartControllerTest.java: added test for empty cart edge case
  All 47 tests passing.
```

### Merging work

Ask the dispatcher to merge completed branches. It handles the git operations.

```
You: "Merge #008 and #009 to main"
Claude: Merged fix/empty-cart-500 into main (fast-forward)
        Merged fix/stale-options-cache into main (clean merge)
        Both branches cleaned up. Queue updated to reflect merge.
```

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
      "project": "/home/user/code/my-api",
      "description": "Add GET /api/search?q=term. Return { results: [{ id, title, snippet, score }] }."
    },
    {
      "role": "frontend",
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

The dispatcher selects agents by matching capabilities to tasks:

1. **Scans available agents** -- reads `~/.claude/agents/` and each agent's `.md` file to understand its name, description, model tier, and specialties
2. **Matches to the task** -- if you have a `java-specialist` agent and the task is a Spring Boot bug, it picks that agent
3. **Picks the smallest effective team** -- doesn't over-assign; a focused bug fix gets one agent, not three
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
- **Agent teams experimental flag** -- native team tools (TeamCreate, SendMessage, TaskCreate) require `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in your Claude Code settings (`~/.claude/settings.json`). The plugin handles this automatically: the SessionStart hook checks for the flag on every launch and adds it if missing, merging safely into your existing settings. If you see a message about the flag being auto-enabled, restart Claude Code for it to take effect.
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
