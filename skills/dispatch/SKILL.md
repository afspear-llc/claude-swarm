---
name: dispatch
description: Multi-agent work queue dispatcher. Manages background agents in isolated git worktrees. Reads ~/.claude/work-queue.json, dispatches ready tasks as single agents or teams, tracks status lifecycle. Use when managing tasks, dispatching work, or checking queue status.
---

# Claude Swarm -- Multi-Agent Dispatcher

On session start -- and whenever a new item is added -- read `~/.claude/work-queue.json`. For each item with `"status": "ready"`, immediately dispatch it (agent or team) in background worktrees and set its status to `"in-progress"`. When all agents for an item complete, set status to `"done"` and record the branch or PR URL. Always dispatch -- never leave ready items sitting. Dispatch ALL ready items concurrently.

**You are the dispatcher, not the worker.** Do not implement fixes or features directly. Discuss with the user, refine the task, write it to the queue, and dispatch. All hands-on work goes to agents.

Dispatched agents should work autonomously -- investigate, fix, test, and verify on their own. They should only escalate back if something is genuinely ambiguous or risky. Give them full context and trust them to figure it out.

## Dispatch Modes

### Single Agent (`"dispatch": "agent"`)

One agent, one worktree. The agent gets the task description and works independently in an isolated git worktree on the specified project.

### Team (`"dispatch": "team"`)

Multiple agents launched in parallel, each in its own worktree. Each team member gets its role-specific description plus the shared task-level description for context. Use teams for cross-cutting features that span multiple concerns (backend + frontend, code + tests, etc.).

### Cross-Codebase Teams

When a team spans multiple projects (e.g., a backend API and a frontend app), give each agent the shared API contract or interface so they can work independently without waiting for each other. For example, if the backend agent is building `GET /api/widgets`, include the response schema in the frontend agent's description so it can code against it immediately.

## Queue Format

The work queue lives at `~/.claude/work-queue.json`. It is a JSON array of task objects.

### Single Agent Task

```json
{
  "id": "001",
  "title": "Short description of the task",
  "description": "Detailed description with acceptance criteria. Be specific about what done looks like.",
  "dispatch": "agent",
  "agent_type": "debugger",
  "project": "/absolute/path/to/project",
  "status": "ready",
  "priority": 1
}
```

### Team Task

```json
{
  "id": "002",
  "title": "Full-stack feature",
  "description": "High-level description shared with all team members for context.",
  "dispatch": "team",
  "team": [
    {
      "role": "backend",
      "agent_type": "backend-architect",
      "project": "/absolute/path/to/backend",
      "description": "Role-specific instructions. What this agent should build, test, and verify."
    },
    {
      "role": "frontend",
      "agent_type": "frontend-developer",
      "project": "/absolute/path/to/frontend",
      "description": "Role-specific instructions. Include the API contract from the backend so this agent can work independently."
    }
  ],
  "status": "ready",
  "priority": 1
}
```

### Fields

| Field | Required | Description |
|-------|----------|-------------|
| `id` | Yes | Unique identifier (e.g., "001", "fix-auth", "feature-profile") |
| `title` | Yes | Short human-readable summary |
| `description` | Yes | Detailed instructions and acceptance criteria |
| `dispatch` | No | `"agent"` (default) or `"team"` |
| `agent_type` | Yes* | Type hint for the agent (e.g., "debugger", "java-pro"). *Required for agent dispatch; for teams, set on each member. |
| `project` | Yes* | Absolute path to the project root. *Required for agent dispatch; for teams, set on each member. |
| `team` | Yes* | Array of team members. *Required for team dispatch. |
| `status` | Yes | `"ready"`, `"in-progress"`, `"done"`, or `"failed"` |
| `priority` | No | Lower number = higher priority. Informational only -- all ready items dispatch concurrently. |
| `branch` | No | Set by dispatcher when done. The git branch or PR URL for the completed work. |

### Team Member Fields

| Field | Required | Description |
|-------|----------|-------------|
| `role` | Yes | Short label (e.g., "backend", "frontend", "tests", "infra") |
| `agent_type` | Yes | Type hint for this agent |
| `project` | Yes | Absolute path to the project this agent works in |
| `description` | Yes | Role-specific instructions for this agent |

## Dispatch Rules

1. **On session start**, read the queue and dispatch every `"ready"` item immediately.
2. **Multiple tasks in parallel**: all ready items dispatch concurrently. Each task runs independently.
3. **Legacy format**: if a queue item has `"agent_type"` but no `"dispatch"` field, treat it as `"dispatch": "agent"`.
4. **Set status to `"in-progress"`** as soon as you dispatch.
5. **When an agent finishes**, set status to `"done"` and record the branch name or PR URL in the `"branch"` field.
6. **If an agent fails**, set status to `"failed"` and add a `"error"` field with a brief explanation.

## Status Lifecycle

```
ready --> in-progress --> done
                     \-> failed
```

- `ready`: queued, waiting for dispatch
- `in-progress`: agent(s) spawned and working
- `done`: work complete, branch/PR recorded
- `failed`: agent hit an unrecoverable issue

## Agent Types

These are suggestions -- use whatever label makes the task clear:

| Agent Type | Typical Use |
|-----------|-------------|
| `debugger` | Investigate and fix bugs |
| `backend-architect` | Design and build backend services, APIs, data models |
| `frontend-developer` | Build UI components, pages, client-side logic |
| `java-pro` | Java/Spring/Maven-specific work |
| `python-pro` | Python-specific work |
| `test-automator` | Write and fix tests (unit, integration, e2e) |
| `security-auditor` | Security review, vulnerability fixes |
| `performance-engineer` | Profiling, optimization, caching |
| `devops` | CI/CD, Docker, deployment configs |
| `refactorer` | Code cleanup, restructuring, dependency updates |

## Tips for Writing Good Tasks

- **Be specific about "done"**: include acceptance criteria, not just a vague goal.
- **Include context**: mention relevant files, error messages, or design decisions.
- **For teams, define the contract**: if backend and frontend agents need to agree on an API shape, put the schema in both descriptions.
- **One concern per agent**: don't overload a single agent with unrelated work.
- **Trust the agent**: give it the goal and constraints, not step-by-step instructions. Let it investigate and decide how to implement.
