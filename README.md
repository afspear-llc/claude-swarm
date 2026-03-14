# claude-swarm

A Claude Code plugin that turns your session into a multi-agent dispatcher. It reads your installed agents from `~/.claude/agents/`, composes the right team for each task, dispatches work to isolated git worktrees, and tracks everything in a persistent work queue that survives across sessions.

## Install

```bash
git clone https://github.com/afspear-llc/claude-swarm.git
claude plugin install --path ./claude-swarm
```

Or load for a single session: `claude --plugin-dir ./claude-swarm`

Uninstall with `claude plugin uninstall claude-swarm`. Your work queue is never deleted.

## Quick Start

Describe what you want. The dispatcher picks the right agent and launches it in the background.

```
You: "The options chain endpoint is returning stale data"
Claude: Dispatched #004 → debugger: "Fix stale options chain cache TTL"

... (agent works in background worktree) ...

Claude: #004 done — reduced cache TTL from 24h to 15min, branch: fix/stale-options-cache
```

For cross-codebase work, it composes a team automatically:

```
You: "Add a search feature — backend indexes posts, frontend shows results"
Claude: Dispatched #005 as team:
  backend → java-specialist: "Add GET /api/search endpoint"
  frontend → angular-specialist: "Add SearchComponent with results"
```

You can also add tasks directly to `~/.claude/work-queue.json` with `"status": "ready"` -- they dispatch on the next session start.

## Prerequisites

- Claude Code installed
- `jq` installed (used by the queue CLI for JSON operations)
- Agent definitions in `~/.claude/agents/` (optional -- works without them using general-purpose dispatch)

The plugin auto-enables the `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` flag in `~/.claude/settings.json` on each launch.

## Docs

- **[How It Works](docs/how-it-works.md)** -- dispatcher pattern, agent discovery, session start protocol, plugin structure
- **[Work Queue](docs/work-queue.md)** -- full queue format spec, all fields, status lifecycle, CLI reference
- **[Team Mode](docs/team-mode.md)** -- when to use teams, independent vs coordinated teams, cross-codebase patterns
- **[Agent Composition](docs/agent-composition.md)** -- how agents are selected, model tier considerations, writing good tasks

## Development

```bash
claude --plugin-dir ./claude-swarm
```

Run `/reload-plugins` inside Claude Code to pick up changes without restarting.

## License

MIT
