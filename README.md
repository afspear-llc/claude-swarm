# Claude Swarm

A Claude Code plugin that turns your main session into a multi-agent dispatcher with team support.

- **Work queue**: a simple JSON file (`~/.claude/work-queue.json`) tracks all tasks
- **Single-agent dispatch**: one task, one agent, one isolated git worktree
- **Team dispatch**: multiple specialized agents work in parallel across codebases
- **Dispatcher mode**: your main Claude session discusses and refines -- agents do the hands-on work
- **Auto-check on session start**: a SessionStart hook reminds Claude to dispatch any ready items

## Install

### From a marketplace

If claude-swarm is published to a marketplace you have configured:

```bash
claude plugin install claude-swarm
```

### From a local directory

Clone the repo and point Claude Code at it:

```bash
git clone https://github.com/afspear/claude-swarm.git
claude --plugin-dir ./claude-swarm
```

To load it automatically without `--plugin-dir`, you can add it to your user settings. Run Claude Code, then use the `/plugin` command to install from the local directory.

### Uninstall

```bash
claude plugin uninstall claude-swarm
```

Or if installed at project scope:

```bash
claude plugin uninstall claude-swarm --scope project
```

Your work queue (`~/.claude/work-queue.json`) is never deleted by uninstall.

## Plugin Structure

```
claude-swarm/
├── .claude-plugin/
│   └── plugin.json           # Plugin manifest (name, version, description)
├── skills/
│   └── dispatch/
│       └── SKILL.md          # Dispatcher instructions (the core brain)
├── hooks/
│   └── hooks.json            # SessionStart hook to auto-check the queue
├── scripts/
│   └── check-queue.sh        # Hook script that detects ready items
├── examples/
│   └── work-queue.json       # Example work queue with sample tasks
├── LICENSE
└── README.md
```

## Usage

1. Start Claude Code (with the plugin loaded)
2. Describe what you want built or fixed
3. Claude adds the task to the work queue and dispatches an agent (or team)
4. Agents work autonomously in isolated worktrees
5. When done, Claude records the branch/PR and marks the task complete

You can also edit `~/.claude/work-queue.json` directly -- Claude picks up `"ready"` items on session start.

The dispatcher skill is also available as `/claude-swarm:dispatch` if you want to invoke it explicitly.

## Queue Format

### Single Agent

For a focused task in one codebase:

```json
{
  "id": "001",
  "title": "Fix login redirect loop",
  "description": "After OAuth callback, users hit an infinite redirect. Check the callback handler and session storage logic.",
  "dispatch": "agent",
  "agent_type": "debugger",
  "project": "/home/user/code/my-app",
  "status": "ready",
  "priority": 1
}
```

### Team

For cross-cutting work spanning multiple concerns or codebases:

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
      "description": "Add GET /api/search?q=term endpoint. Return { results: [{ id, title, snippet, score }] }. Add full-text index on posts.content."
    },
    {
      "role": "frontend",
      "agent_type": "frontend-developer",
      "project": "/home/user/code/my-web",
      "description": "Add SearchComponent with debounced input. Call GET /api/search?q=term. Display results as cards with title and highlighted snippet."
    }
  ],
  "status": "ready",
  "priority": 1
}
```

### Status Values

| Status | Meaning |
|--------|---------|
| `ready` | Queued, will dispatch on next session start |
| `in-progress` | Agent(s) spawned and working |
| `done` | Complete, branch/PR recorded |
| `failed` | Agent hit an unrecoverable issue |

## Agent Types

Use whatever label fits, but here are common ones:

| Type | Use For |
|------|---------|
| `debugger` | Investigating and fixing bugs |
| `backend-architect` | APIs, services, data models |
| `frontend-developer` | UI components, pages, client logic |
| `java-pro` | Java/Spring/Maven work |
| `python-pro` | Python-specific work |
| `test-automator` | Unit, integration, and e2e tests |
| `security-auditor` | Security review and vulnerability fixes |
| `performance-engineer` | Profiling, optimization, caching |
| `devops` | CI/CD, Docker, infrastructure |
| `refactorer` | Code cleanup and restructuring |

These are hints for the agent's mindset, not hard categories. Claude adapts regardless.

## How It Works

This is a native Claude Code plugin. It provides:

1. **A skill** (`skills/dispatch/SKILL.md`) -- the full dispatcher instructions that teach Claude to manage the work queue, dispatch agents in worktrees, and track task status. Claude automatically uses this skill based on context.

2. **A SessionStart hook** (`hooks/hooks.json`) -- runs `scripts/check-queue.sh` at the beginning of every session. If there are `"ready"` items in the queue, it reminds Claude to dispatch them immediately.

The main session never does implementation work directly. It stays in dispatcher mode: discussing requirements, refining task descriptions, and managing the queue.

## Tips

- **Be specific**: good task descriptions include acceptance criteria, not just goals
- **Define contracts**: for team tasks, put the shared API schema in each agent's description so they can work independently
- **One concern per agent**: don't overload agents with unrelated work
- **Trust the agents**: give them the goal and constraints, let them figure out the implementation

## Development

To test changes locally:

```bash
claude --plugin-dir ./claude-swarm
```

Run `/reload-plugins` inside Claude Code to pick up changes without restarting.

## License

MIT
