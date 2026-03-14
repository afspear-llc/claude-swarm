# Team Mode

Team mode uses Claude Code's native team tools (TeamCreate, SendMessage, TaskCreate) for coordinated multi-agent work. Multiple named agents run concurrently, message each other, and share a task board. Unlike independent single-agent dispatch, team agents can negotiate API contracts and handle dependent subtasks in real time.

Requires `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in `~/.claude/settings.json`. The plugin's SessionStart hook sets this automatically. Restart Claude Code if you see the first-time enablement message.

## When to Use Teams vs Single-Agent Dispatch

| Single-agent dispatch | Team mode |
|---|---|
| Task is self-contained (one repo, one concern) | Task spans multiple codebases |
| No coordination needed -- just "go fix this" | Agents need to agree on interfaces or contracts |
| Fast, independent bug fixes or features | Subtasks have dependencies (backend before frontend) |
| Cost matters -- teams use more tokens | Real-time coordination produces better results than async handoff |

**Default to single-agent dispatch.** Most tasks are single-concern. Use teams when the work genuinely requires coordination. When in doubt, start with one agent and dispatch follow-up work if needed.

## Independent Teams

When team members can work without waiting for each other, spawn them as independent background agents. Each gets its own worktree, possibly on a different project. No coordination overhead.

The key: define the shared contract upfront and include it in every agent's instructions.

```
You: "Add a search feature -- backend indexes posts, frontend shows results"
```

The dispatcher creates a team task with two members. Both get the API contract in their description:

```json
{
  "dispatch": "team",
  "team": [
    {
      "role": "backend",
      "project": "/home/user/code/my-api",
      "description": "Add GET /api/search?q=term. Return { results: [{ id, title, excerpt, score }] }. Add SearchService with full-text query. Unit tests."
    },
    {
      "role": "frontend",
      "project": "/home/user/code/my-web",
      "description": "Add SearchComponent. Call GET /api/search?q=term. Display results as { id, title, excerpt, score }. Debounce input. Loading state."
    }
  ]
}
```

Both agents work in parallel. Because they share the same API contract, their code connects without either waiting on the other.

**Use independent teams when:**
- The interface between components can be defined before work starts
- No agent needs output from another agent to begin
- The codebases are separate (backend + frontend, service A + service B)

## Coordinated Teams

When agents must share state, hand off intermediate results, or make joint decisions, use native team coordination:

1. The dispatcher creates a team with `TeamCreate` and a shared task list
2. Sub-tasks are created with `TaskCreate`, using `blockedBy` for dependencies
3. Teammates are spawned via the Agent tool with `team_name` and `name` parameters
4. Agents coordinate through `SendMessage` and the shared `TaskList`

Example: a database migration agent must finish before the application code agent starts, and a test agent needs both to complete.

**Use coordinated teams when:**
- Sub-tasks have hard dependencies (B cannot start until A finishes)
- Agents need to make joint decisions at runtime
- The interface between components cannot be fully defined upfront

## Cross-Codebase Patterns

Cross-codebase work (backend + frontend, multiple microservices) is the most common team use case. The pattern:

1. **Define the contract explicitly.** Write out the exact API shape, data format, or shared interface.
2. **Include the contract in every relevant agent's description.** Both the producer and consumer need it.
3. **Let agents work independently.** With the contract defined, no agent blocks on another.

This works because the contract is the synchronization mechanism. If backend returns `{ widgets: [{ id, name, price }] }` and frontend expects exactly that, the integration works without the agents ever communicating.

When the contract is too complex to define upfront, or when it needs to evolve during implementation, use coordinated teams instead.

## Merging Team Work

After a team completes, each agent's changes live on a separate branch (one per worktree). The dispatcher can merge them:

```
You: "Merge #008 and #009 to main"
Claude: Merged fix/empty-cart-500 (fast-forward)
        Merged fix/stale-options-cache (clean merge)
        Branches cleaned up, queue updated.
```

For team tasks where branches might conflict (e.g., both agents touched a shared config file), review the changes before merging.
