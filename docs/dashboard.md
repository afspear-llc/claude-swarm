# Dashboard

A local webserver that displays real-time status of your work queue, teams, and agents in a browser.

## Quick Start

```bash
python3 scripts/webserver.py
```

Open [http://localhost:8377](http://localhost:8377) in your browser.

## What It Shows

- **Stats bar** — counts of ready, in-progress, done, and failed tasks at a glance
- **Task cards** — each task with its status, dispatch type, project path, branch (when done), and error (when failed)
- **Team members** — expandable detail showing each role, project, and instructions for team-dispatched tasks
- **Real-time updates** — the page updates instantly when the work queue changes (via Server-Sent Events)

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

## Architecture

- **Zero dependencies** — uses only Python stdlib (`http.server`, `json`, `threading`)
- **SSE streaming** — a background thread polls the queue file (1s interval) and pushes changes to all connected browsers
- **Single file** — the entire server, dashboard HTML, CSS, and JS are in `scripts/webserver.py`
- **Reads only** — the server never modifies queue state directly; it delegates to `queue.sh` for atomic writes
