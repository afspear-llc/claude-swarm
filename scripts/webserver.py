#!/usr/bin/env python3
"""claude-swarm dashboard — lightweight local webserver.

Zero external dependencies. Uses only Python stdlib.

Usage:
    python3 scripts/webserver.py [--port 8377] [--queue ~/.claude/work-queue.json]

Endpoints:
    GET  /              Dashboard (single-page HTML)
    GET  /api/tasks     JSON snapshot of the queue
    GET  /api/stream    SSE stream — pushes queue changes in real time
    POST /api/tasks     Add a new task (accepts JSON body)
"""

import argparse
import json
import os
import subprocess
import sys
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

# ---------------------------------------------------------------------------
# Globals set once at startup
# ---------------------------------------------------------------------------
QUEUE_PATH: Path = Path.home() / ".claude" / "work-queue.json"
QUEUE_SH: Path = Path(__file__).resolve().parent / "queue.sh"
SSE_CLIENTS: list = []
SSE_LOCK = threading.Lock()
LAST_MTIME: float = 0.0
LAST_SNAPSHOT: str = "[]"

# ---------------------------------------------------------------------------
# Queue helpers
# ---------------------------------------------------------------------------

def read_queue() -> str:
    """Return raw JSON string of the queue file."""
    try:
        return QUEUE_PATH.read_text()
    except FileNotFoundError:
        return "[]"


def queue_stats(tasks: list) -> dict:
    """Compute summary stats from parsed task list."""
    counts = {"ready": 0, "in-progress": 0, "done": 0, "failed": 0}
    teams = {}
    for t in tasks:
        status = t.get("status", "ready")
        counts[status] = counts.get(status, 0) + 1
        # Group by dispatch type or team role
        if t.get("dispatch") == "team" and t.get("team"):
            for member in t["team"]:
                role = member.get("role", "unknown")
                teams.setdefault(role, []).append(t["id"])
    return {"counts": counts, "total": len(tasks), "team_roles": teams}


# ---------------------------------------------------------------------------
# SSE watcher thread
# ---------------------------------------------------------------------------

def watch_queue():
    """Poll queue file for changes and broadcast to SSE clients."""
    global LAST_MTIME, LAST_SNAPSHOT
    while True:
        try:
            mtime = QUEUE_PATH.stat().st_mtime if QUEUE_PATH.exists() else 0.0
            if mtime != LAST_MTIME:
                LAST_MTIME = mtime
                raw = read_queue()
                LAST_SNAPSHOT = raw
                broadcast(raw)
        except Exception:
            pass
        time.sleep(1)


def broadcast(data: str):
    """Send an SSE event to every connected client."""
    msg = f"data: {data}\n\n".encode()
    dead = []
    with SSE_LOCK:
        for wfile in SSE_CLIENTS:
            try:
                wfile.write(msg)
                wfile.flush()
            except Exception:
                dead.append(wfile)
        for d in dead:
            SSE_CLIENTS.remove(d)


# ---------------------------------------------------------------------------
# HTML Dashboard (embedded)
# ---------------------------------------------------------------------------

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>claude-swarm dashboard</title>
<style>
  :root {
    --bg: #0d1117; --surface: #161b22; --border: #30363d;
    --text: #e6edf3; --muted: #8b949e; --accent: #58a6ff;
    --green: #3fb950; --yellow: #d29922; --red: #f85149; --blue: #58a6ff;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
    background: var(--bg); color: var(--text); line-height: 1.5;
    padding: 1.5rem; max-width: 1200px; margin: 0 auto;
  }
  h1 { font-size: 1.4rem; margin-bottom: 0.25rem; }
  h1 span { color: var(--accent); }
  .subtitle { color: var(--muted); font-size: 0.85rem; margin-bottom: 1.5rem; }

  /* Stats bar */
  .stats {
    display: flex; gap: 1rem; margin-bottom: 1.5rem; flex-wrap: wrap;
  }
  .stat {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 8px; padding: 0.75rem 1.25rem; min-width: 120px;
    text-align: center;
  }
  .stat .num { font-size: 1.8rem; font-weight: 700; }
  .stat .label { font-size: 0.75rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em; }
  .stat.ready .num { color: var(--blue); }
  .stat.in-progress .num { color: var(--yellow); }
  .stat.done .num { color: var(--green); }
  .stat.failed .num { color: var(--red); }

  /* Task cards */
  .tasks { display: flex; flex-direction: column; gap: 0.75rem; margin-bottom: 2rem; }
  .task {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 8px; padding: 1rem 1.25rem;
    border-left: 4px solid var(--border);
    transition: border-color 0.2s;
  }
  .task.status-ready       { border-left-color: var(--blue); }
  .task.status-in-progress { border-left-color: var(--yellow); }
  .task.status-done        { border-left-color: var(--green); }
  .task.status-failed      { border-left-color: var(--red); }

  .task-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.35rem; }
  .task-id { color: var(--muted); font-size: 0.8rem; font-family: monospace; }
  .task-title { font-weight: 600; font-size: 1rem; }
  .task-desc { color: var(--muted); font-size: 0.85rem; margin-bottom: 0.5rem;
    max-height: 3rem; overflow: hidden; text-overflow: ellipsis; }
  .task-meta { display: flex; gap: 0.75rem; font-size: 0.78rem; flex-wrap: wrap; }
  .badge {
    display: inline-block; padding: 0.15rem 0.55rem; border-radius: 12px;
    font-size: 0.72rem; font-weight: 600; text-transform: uppercase;
  }
  .badge-ready       { background: #1f3a5f; color: var(--blue); }
  .badge-in-progress { background: #3d2e00; color: var(--yellow); }
  .badge-done        { background: #1a3a1a; color: var(--green); }
  .badge-failed      { background: #3d1a1a; color: var(--red); }
  .badge-dispatch    { background: #2a1f3d; color: #bc8cff; }
  .badge-role        { background: #1f2d3d; color: #79c0ff; }

  .team-members { margin-top: 0.5rem; padding-top: 0.5rem; border-top: 1px solid var(--border); }
  .team-members summary { color: var(--muted); cursor: pointer; font-size: 0.82rem; }
  .member { padding: 0.35rem 0 0.35rem 1rem; font-size: 0.82rem; border-left: 2px solid var(--border); margin: 0.3rem 0; }
  .member-role { font-weight: 600; color: var(--accent); }
  .member-proj { color: var(--muted); font-family: monospace; font-size: 0.75rem; }

  .branch { font-family: monospace; color: var(--green); font-size: 0.78rem; }
  .error  { font-family: monospace; color: var(--red); font-size: 0.78rem; }

  /* Prompt form */
  .prompt-section {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 8px; padding: 1.25rem; margin-bottom: 1.5rem;
  }
  .prompt-section h2 { font-size: 1rem; margin-bottom: 0.75rem; }
  .form-row { display: flex; gap: 0.5rem; margin-bottom: 0.5rem; flex-wrap: wrap; }
  .form-row input, .form-row select, .form-row textarea {
    background: var(--bg); border: 1px solid var(--border); color: var(--text);
    border-radius: 6px; padding: 0.5rem 0.75rem; font-size: 0.85rem;
    font-family: inherit;
  }
  .form-row input:focus, .form-row select:focus, .form-row textarea:focus {
    outline: none; border-color: var(--accent);
  }
  .form-row input { flex: 1; min-width: 200px; }
  .form-row textarea { flex: 1; min-width: 200px; min-height: 60px; resize: vertical; }
  .form-row select { min-width: 100px; }
  button {
    background: var(--accent); color: #fff; border: none; border-radius: 6px;
    padding: 0.5rem 1.25rem; font-weight: 600; cursor: pointer; font-size: 0.85rem;
  }
  button:hover { opacity: 0.9; }
  .toast {
    position: fixed; bottom: 1.5rem; right: 1.5rem; background: var(--green);
    color: #fff; padding: 0.6rem 1.2rem; border-radius: 8px; font-size: 0.85rem;
    opacity: 0; transition: opacity 0.3s; pointer-events: none;
  }
  .toast.show { opacity: 1; }

  /* Team prompt tabs */
  .team-tabs { display: flex; gap: 0; margin-bottom: 0; }
  .team-tab {
    padding: 0.45rem 1rem; background: var(--bg); border: 1px solid var(--border);
    border-bottom: none; border-radius: 8px 8px 0 0; cursor: pointer;
    font-size: 0.82rem; color: var(--muted);
  }
  .team-tab.active { background: var(--surface); color: var(--text); font-weight: 600; }
  .team-prompt-body { border-top: none; border-radius: 0 8px 8px 8px; }

  .connected { color: var(--green); }
  .disconnected { color: var(--red); }
  #status-dot { font-size: 0.65rem; vertical-align: middle; }

  .empty-state { text-align: center; padding: 3rem; color: var(--muted); }
</style>
</head>
<body>

<h1><span>claude-swarm</span> dashboard</h1>
<p class="subtitle">
  <span id="status-dot" class="connected">&#9679;</span>
  <span id="conn-label">connected</span>
  &mdash; watching work queue
</p>

<div class="stats" id="stats"></div>

<div id="prompts"></div>

<div class="tasks" id="tasks"></div>

<div class="toast" id="toast"></div>

<script>
// ---- State ----
let tasks = [];
let teamGroups = {};

// ---- SSE ----
function connect() {
  const src = new EventSource('/api/stream');
  src.onmessage = (e) => {
    try { tasks = JSON.parse(e.data); } catch { return; }
    render();
  };
  src.onopen = () => {
    document.getElementById('status-dot').className = 'connected';
    document.getElementById('conn-label').textContent = 'connected';
  };
  src.onerror = () => {
    document.getElementById('status-dot').className = 'disconnected';
    document.getElementById('conn-label').textContent = 'reconnecting...';
  };
}

// ---- Render ----
function render() {
  renderStats();
  renderTasks();
  renderPrompts();
}

function renderStats() {
  const c = { ready: 0, 'in-progress': 0, done: 0, failed: 0 };
  tasks.forEach(t => c[t.status] = (c[t.status] || 0) + 1);
  document.getElementById('stats').innerHTML =
    ['ready', 'in-progress', 'done', 'failed'].map(s =>
      `<div class="stat ${s}"><div class="num">${c[s]}</div><div class="label">${s}</div></div>`
    ).join('') +
    `<div class="stat"><div class="num">${tasks.length}</div><div class="label">total</div></div>`;
}

function renderTasks() {
  const el = document.getElementById('tasks');
  if (!tasks.length) {
    el.innerHTML = '<div class="empty-state">No tasks in queue. Add one below.</div>';
    return;
  }
  el.innerHTML = tasks.map(t => {
    const statusCls = `status-${t.status}`;
    const badgeCls = `badge-${t.status}`;
    let teamHtml = '';
    if (t.dispatch === 'team' && t.team && t.team.length) {
      teamHtml = `<div class="team-members"><details><summary>${t.team.length} team member(s)</summary>` +
        t.team.map(m =>
          `<div class="member"><span class="member-role">${esc(m.role)}</span>` +
          `<div class="member-proj">${esc(m.project || '')}</div>` +
          `<div style="color:var(--muted);font-size:0.78rem">${esc(m.description || '')}</div></div>`
        ).join('') + '</details></div>';
    }
    const branchHtml = t.branch ? `<span class="branch">${esc(t.branch)}</span>` : '';
    const errorHtml = t.error ? `<span class="error">${esc(t.error)}</span>` : '';
    return `<div class="task ${statusCls}">
      <div class="task-header">
        <span class="task-title">${esc(t.title)}</span>
        <span class="task-id">#${esc(t.id)}</span>
      </div>
      <div class="task-desc">${esc(t.description || '')}</div>
      <div class="task-meta">
        <span class="badge ${badgeCls}">${t.status}</span>
        <span class="badge badge-dispatch">${t.dispatch || 'auto'}</span>
        ${t.project ? `<span style="font-family:monospace;color:var(--muted);font-size:0.78rem">${esc(t.project)}</span>` : ''}
        ${branchHtml} ${errorHtml}
      </div>
      ${teamHtml}
    </div>`;
  }).join('');
}

function renderPrompts() {
  // Build per-team groups + a general prompt
  const groups = {};
  tasks.forEach(t => {
    if (t.dispatch === 'team' && t.team) {
      t.team.forEach(m => {
        const r = m.role || 'unknown';
        if (!groups[r]) groups[r] = [];
        groups[r].push({ id: t.id, project: m.project });
      });
    }
  });

  const tabs = ['new-task', ...Object.keys(groups)];
  const el = document.getElementById('prompts');

  el.innerHTML = `
    <div class="prompt-section">
      <h2>Add Task</h2>
      <div class="team-tabs" id="prompt-tabs">
        ${tabs.map((t, i) => `<div class="team-tab${i === 0 ? ' active' : ''}" data-tab="${t}">${t === 'new-task' ? 'New Task' : t}</div>`).join('')}
      </div>
      <div id="prompt-body"></div>
    </div>`;

  // Tab switching
  document.querySelectorAll('.team-tab').forEach(tab => {
    tab.onclick = () => {
      document.querySelectorAll('.team-tab').forEach(x => x.classList.remove('active'));
      tab.classList.add('active');
      renderPromptBody(tab.dataset.tab, groups);
    };
  });
  renderPromptBody('new-task', groups);
}

function renderPromptBody(tab, groups) {
  const body = document.getElementById('prompt-body');
  if (tab === 'new-task') {
    body.innerHTML = `
      <form id="add-form" style="margin-top:0.75rem">
        <div class="form-row">
          <input name="title" placeholder="Task title" required>
          <select name="dispatch"><option value="auto">auto</option><option value="agent">agent</option><option value="team">team</option></select>
        </div>
        <div class="form-row">
          <textarea name="description" placeholder="Describe the task — acceptance criteria, context, etc." required></textarea>
        </div>
        <div class="form-row">
          <input name="project" placeholder="Project path (e.g. /home/user/code/my-app)">
          <button type="submit">Add Task</button>
        </div>
      </form>`;
    document.getElementById('add-form').onsubmit = async (e) => {
      e.preventDefault();
      const fd = new FormData(e.target);
      const payload = Object.fromEntries(fd);
      const res = await fetch('/api/tasks', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
      });
      if (res.ok) { toast('Task added!'); e.target.reset(); }
      else toast('Failed: ' + await res.text());
    };
  } else {
    const members = groups[tab] || [];
    body.innerHTML = `
      <div style="margin-top:0.75rem">
        <p style="color:var(--muted);font-size:0.82rem;margin-bottom:0.5rem">
          Send a task targeting the <strong>${esc(tab)}</strong> role
          (${members.length} active member${members.length !== 1 ? 's' : ''})
        </p>
        <form id="team-form">
          <div class="form-row">
            <input name="title" placeholder="Task title for ${esc(tab)}" required>
          </div>
          <div class="form-row">
            <textarea name="description" placeholder="Instructions for ${esc(tab)} agents..." required></textarea>
          </div>
          <div class="form-row">
            <input name="project" placeholder="Project path" value="${esc(members[0]?.project || '')}">
            <button type="submit">Add to ${esc(tab)}</button>
          </div>
        </form>
      </div>`;
    document.getElementById('team-form').onsubmit = async (e) => {
      e.preventDefault();
      const fd = new FormData(e.target);
      const payload = Object.fromEntries(fd);
      payload.dispatch = 'agent';
      const res = await fetch('/api/tasks', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
      });
      if (res.ok) { toast('Task added for ' + tab + '!'); e.target.reset(); }
      else toast('Failed: ' + await res.text());
    };
  }
}

function esc(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }

function toast(msg) {
  const el = document.getElementById('toast');
  el.textContent = msg; el.classList.add('show');
  setTimeout(() => el.classList.remove('show'), 2500);
}

// ---- Init ----
connect();
// Fetch initial state
fetch('/api/tasks').then(r => r.json()).then(d => { tasks = d; render(); });
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        # Compact log
        sys.stderr.write(f"[dashboard] {args[0]} {args[1]}\n")

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        if self.path == "/":
            self._serve_dashboard()
        elif self.path == "/api/tasks":
            self._serve_tasks()
        elif self.path == "/api/stream":
            self._serve_sse()
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == "/api/tasks":
            self._add_task()
        else:
            self.send_error(404)

    # -- Routes --

    def _serve_dashboard(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(DASHBOARD_HTML.encode())

    def _serve_tasks(self):
        raw = read_queue()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self._cors()
        self.end_headers()
        self.wfile.write(raw.encode())

    def _serve_sse(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self._cors()
        self.end_headers()
        # Send current state immediately
        self.wfile.write(f"data: {LAST_SNAPSHOT}\n\n".encode())
        self.wfile.flush()
        with SSE_LOCK:
            SSE_CLIENTS.append(self.wfile)
        # Keep connection alive
        try:
            while True:
                time.sleep(30)
                self.wfile.write(b": keepalive\n\n")
                self.wfile.flush()
        except Exception:
            pass
        finally:
            with SSE_LOCK:
                if self.wfile in SSE_CLIENTS:
                    SSE_CLIENTS.remove(self.wfile)

    def _add_task(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
        except Exception:
            self.send_error(400, "Invalid JSON")
            return

        title = body.get("title", "").strip()
        desc = body.get("description", "").strip()
        project = body.get("project", "").strip()
        dispatch = body.get("dispatch", "auto").strip()

        if not title or not desc:
            self.send_error(400, "title and description required")
            return

        # Use queue.sh to add atomically
        if QUEUE_SH.exists():
            cmd = [str(QUEUE_SH), "add", title, desc, project or "/tmp", dispatch]
            result = subprocess.run(cmd, capture_output=True, text=True)
            msg = result.stdout.strip() or "added"
        else:
            # Fallback: direct JSON manipulation
            try:
                tasks = json.loads(read_queue())
            except Exception:
                tasks = []
            ids = [int(t["id"]) for t in tasks if t.get("id", "").isdigit()]
            next_id = f"{(max(ids, default=0) + 1):03d}"
            tasks.append({
                "id": next_id, "title": title, "description": desc,
                "dispatch": dispatch, "project": project or "/tmp",
                "status": "ready", "priority": 1,
            })
            QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
            QUEUE_PATH.write_text(json.dumps(tasks, indent=2))
            msg = f"Added #{next_id}: {title}"

        self.send_response(201)
        self.send_header("Content-Type", "application/json")
        self._cors()
        self.end_headers()
        self.wfile.write(json.dumps({"ok": True, "message": msg}).encode())


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="claude-swarm dashboard server")
    parser.add_argument("--port", type=int, default=8377, help="Port (default: 8377)")
    parser.add_argument("--queue", type=str, default=None, help="Path to work-queue.json")
    args = parser.parse_args()

    global QUEUE_PATH
    if args.queue:
        QUEUE_PATH = Path(args.queue)

    # Ensure queue dir exists
    QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not QUEUE_PATH.exists():
        QUEUE_PATH.write_text("[]")

    # Initial read
    global LAST_SNAPSHOT, LAST_MTIME
    LAST_SNAPSHOT = read_queue()
    LAST_MTIME = QUEUE_PATH.stat().st_mtime if QUEUE_PATH.exists() else 0.0

    # Start watcher thread
    watcher = threading.Thread(target=watch_queue, daemon=True)
    watcher.start()

    server = HTTPServer(("127.0.0.1", args.port), Handler)
    print(f"\n  claude-swarm dashboard")
    print(f"  ----------------------")
    print(f"  http://localhost:{args.port}")
    print(f"  watching: {QUEUE_PATH}")
    print(f"  press Ctrl+C to stop\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nshutting down.")
        server.shutdown()


if __name__ == "__main__":
    main()
