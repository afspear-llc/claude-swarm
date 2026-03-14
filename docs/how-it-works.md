# How It Works

claude-swarm turns a Claude Code session into a dispatcher that manages background agents. The main session never writes code itself. It discusses requirements with you, breaks work into tasks, picks the right agents, and launches them in isolated git worktrees.

## The Dispatcher Pattern

When the plugin loads, Claude adopts a strict role: **dispatcher, not worker**. Its responsibilities are:

1. Refine task requirements through conversation with you
2. Scan `~/.claude/agents/` to discover available specialists
3. Match tasks to agents based on capabilities
4. Write tasks to the persistent work queue (`~/.claude/work-queue.json`)
5. Spawn agents in background worktrees
6. Track progress and report results

All implementation work happens in background agents. The dispatcher selects, assigns, and coordinates.

## Agent Discovery

Before dispatching any task, the dispatcher reads every `.md` file in `~/.claude/agents/`. Each file describes an agent's capabilities: name, description, model tier, tools, and specialties. The dispatcher builds a mental map of what specialists are available and uses it for every subsequent dispatch decision in the session.

If `~/.claude/agents/` is empty or missing, the dispatcher still works. It uses the default Agent tool without specialization. The dispatcher pattern is valuable even without named agents.

## Session Start Protocol

A `SessionStart` hook (`scripts/check-queue.sh`) runs every time Claude Code starts. It does two things:

1. **Ensures the agent teams flag is set.** The hook writes `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` into `~/.claude/settings.json` if it is not already present. This flag enables native team tools (TeamCreate, SendMessage, TaskCreate). If the flag was just enabled, a Claude Code restart is required for it to take effect.

2. **Checks the work queue for ready items.** If `~/.claude/work-queue.json` has tasks with `"status": "ready"`, the hook outputs a message telling the dispatcher to read the queue and dispatch them immediately.

On seeing the hook output, the dispatcher:

1. Locates the queue CLI script
2. Runs `queue.sh list ready` to see pending tasks
3. Dispatches all ready items concurrently (not one at a time)
4. Checks `queue.sh list in-progress` and reports status to the user
5. Never leaves ready items sitting

If the queue file does not exist, there is nothing to dispatch and the session proceeds normally.

## Dispatch Protocol

When dispatching a single task:

1. Read `~/.claude/agents/` to discover available specialists (if not already done this session)
2. Match the task to the best available agent using the [selection principles](agent-composition.md#selection-principles)
3. Mark the task in-progress: `queue.sh update <id> status in-progress`
4. Spawn the agent via the Agent tool with `run_in_background=true` and `isolation="worktree"`
5. Include full context in the agent's instructions: task description, acceptance criteria, project path, relevant files

## Completion Handling

When an agent finishes successfully:

1. Update the queue: `queue.sh update <id> status done` and `queue.sh update <id> branch <branch-name>`
2. Report a brief summary to the user

When an agent fails:

1. Update the queue: `queue.sh update <id> status failed` and `queue.sh update <id> error "explanation"`
2. Report the failure and discuss next steps

## Plugin Structure

```
claude-swarm/
  .claude-plugin/
    plugin.json           Plugin manifest
  skills/
    dispatch/
      SKILL.md            Dispatcher instructions (the core brain)
  hooks/
    hooks.json            SessionStart hook definition
  scripts/
    check-queue.sh        Hook script: enables teams flag, detects ready items
    queue.sh              CLI for queue operations (add, update, remove, list)
    webserver.py          Local dashboard server (real-time queue viewer)
  examples/
    work-queue.json       Example queue with sample tasks
  docs/
    how-it-works.md       This file
    work-queue.md         Queue format spec and CLI reference
    team-mode.md          Team dispatch patterns
    agent-composition.md  Agent selection and task writing
  LICENSE
  README.md
```
