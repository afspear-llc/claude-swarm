# Claude Swarm

Turn Claude Code into a multi-agent dispatcher with team support.

- **Work queue**: a simple JSON file (`~/.claude/work-queue.json`) tracks all tasks
- **Single-agent dispatch**: one task, one agent, one isolated git worktree
- **Team dispatch**: multiple specialized agents work in parallel across codebases
- **Dispatcher mode**: your main Claude session discusses and refines -- agents do the hands-on work

## Install

```bash
git clone https://github.com/your-user/claude-swarm.git
cd claude-swarm
./install.sh
```

This appends dispatcher instructions to `~/.claude/CLAUDE.md` (creates it if needed) and initializes an empty work queue. Safe to run multiple times.

## Uninstall

```bash
./uninstall.sh
```

Removes the swarm config from `~/.claude/CLAUDE.md`. Your work queue is left intact.

## Usage

1. Start Claude Code in any project
2. Describe what you want built or fixed
3. Claude adds the task to the work queue and dispatches an agent (or team)
4. Agents work autonomously in isolated worktrees
5. When done, Claude records the branch/PR and marks the task complete

You can also edit `~/.claude/work-queue.json` directly -- Claude picks up `"ready"` items on session start.

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

The install script appends instructions to `~/.claude/CLAUDE.md` -- the file Claude Code reads on every session start. These instructions tell Claude to:

1. Check the work queue for `"ready"` items
2. Dispatch each one in an isolated git worktree (using Claude Code's built-in worktree agent support)
3. Track status transitions: `ready` -> `in-progress` -> `done` | `failed`
4. Record the resulting branch or PR URL

The main session never does implementation work directly. It stays in dispatcher mode: discussing requirements, refining task descriptions, and managing the queue.

## Tips

- **Be specific**: good task descriptions include acceptance criteria, not just goals
- **Define contracts**: for team tasks, put the shared API schema in each agent's description so they can work independently
- **One concern per agent**: don't overload agents with unrelated work
- **Trust the agents**: give them the goal and constraints, let them figure out the implementation

## License

MIT
