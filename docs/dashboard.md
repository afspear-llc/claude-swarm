# Dashboard

A local webserver that displays real-time status of your work queue, teams, and agents in a browser.

## Quick Start

```bash
python3 scripts/webserver.py
```

Open [http://localhost:8377](http://localhost:8377) in your browser.

## What It Shows

- **Stats bar** — counts of ready, in-progress, done, and failed tasks at a glance, plus total event count
- **Agent Output stream** — global live feed of all agent events with type filters (dispatched, output, completed, failed, info) and auto-scroll
- **Task cards** — each task with its status, dispatch type, project path, branch (when done), and error (when failed)
- **Per-task events** — expandable event log on each task card showing that task's agent output
- **Team members** — expandable detail showing each role, project, and instructions for team-dispatched tasks
- **Real-time updates** — the page updates instantly when the work queue or event log changes (via Server-Sent Events)

## Adding Tasks from the Browser

The dashboard includes a tabbed prompt section at the bottom:

- **New Task** tab — add any task with title, description, project path, and dispatch type
- **Per-role tabs** — when team tasks exist, tabs appear for each role (e.g. `backend`, `frontend`) letting you target tasks to specific team roles

Tasks added through the dashboard are written to the queue using `queue.sh` (same atomic updates as the CLI).

## Options

```
python3 scripts/webserver.py [--port PORT] [--queue PATH]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--port` | `8377` | Port to listen on |
| `--queue` | `~/.claude/work-queue.json` | Path to the queue file |

## Agent Output Streaming

The dispatcher logs agent events to `~/.claude/swarm-events.jsonl` using:

```bash
queue.sh log <task-id> <type> "<message>"
```

Event types: `dispatched`, `output`, `completed`, `failed`, `info`.

The dashboard streams these events in real time. They appear in two places:
- **Global Agent Output panel** — all events from all tasks, filterable by type
- **Per-task event log** — expandable section on each task card showing only that task's events

## Architecture

- **Zero dependencies** — uses only Python stdlib (`http.server`, `json`, `threading`)
- **SSE streaming** — a background thread polls both the queue file and events log (1s interval) and pushes changes to all connected browsers
- **Single file** — the entire server, dashboard HTML, CSS, and JS are in `scripts/webserver.py`
- **Append-only events** — agent output is stored in `~/.claude/swarm-events.jsonl` (one JSON object per line)
- **Reads only** — the server never modifies queue state directly; it delegates to `queue.sh` for atomic writes
