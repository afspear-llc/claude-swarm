# Agent Composition

The dispatcher scans `~/.claude/agents/` to discover installed specialists, then picks the best agents for each task. This page covers how that selection works and how to write tasks that agents execute well.

## Discovery

Agent definitions live as `.md` files in `~/.claude/agents/`. Each file describes one agent: its name, what it does, which model it runs on, what tools it has access to, and what it specializes in.

The dispatcher reads all of these at the start of a session and builds a mental map. It does not re-scan on every dispatch -- the map is built once per session.

If `~/.claude/agents/` is empty or does not exist, everything still works. The dispatcher uses the default Agent tool and provides task-specific instructions directly.

## Selection Principles

1. **Match task requirements to agent capabilities.** A Java bug fix goes to `java-specialist` if you have one. A security review goes to `security-auditor`. Straightforward matching.

2. **Compose the smallest effective team.** A focused bug fix needs one agent. Do not assign three agents to a one-agent task.

3. **Prefer specialists over generalists** when a good match exists. A security-focused agent will do a better job on a security audit than a general-purpose agent with a security-related prompt.

4. **Consider model tiers.** Opus agents are expensive. Save them for critical, complex, or high-stakes work. Use Haiku or Sonnet agents for routine bug fixes, test writing, and straightforward features.

5. **Fall back to general-purpose agents.** If no specialist fits the task, use a general-purpose agent with role-specific instructions in the prompt. You do not need a perfect match -- any agent can be guided.

6. **No agents installed is fine.** The dispatcher pattern works without named agents. It dispatches using the default Agent tool and provides all context in the task description.

## Model Tier Considerations

| Tier | Cost | Best for |
|------|------|----------|
| Haiku | Low | Routine fixes, simple tests, grep-and-replace tasks, research |
| Sonnet | Medium | Features, refactors, code review, moderate complexity |
| Opus | High | Architectural decisions, complex multi-file refactors, security audits, anything where getting it wrong is costly |

The dispatcher factors this in automatically. You do not need to specify which model to use -- it picks based on task complexity and available agents.

## What to Include in Agent Instructions

When the dispatcher spawns an agent, it includes:

- **Task title and full description** -- what to do and what "done" looks like
- **Project path** -- where to work
- **A note to read the project's CLAUDE.md** if one exists -- agents should discover project conventions themselves
- **Relevant file paths** -- specific files to investigate, error locations, changed files
- **Error messages or stack traces** -- if the task is a bug fix, include the actual error
- **For team members: the shared contract** -- the API schema, interface, or data format that other agents are coding against

The dispatcher does NOT include step-by-step implementation instructions. It gives goals and constraints. Agents decide how to implement.

## Tips for Writing Good Tasks

**Be specific about "done."** Include acceptance criteria, not just a vague goal.

Bad: "Fix the auth bug"
Good: "Fix the JWT refresh timeout. Users are getting logged out after 5 minutes of activity. The refresh token call should fire before expiry. Add unit tests for the refresh logic."

**Include context.** Mention relevant files, error messages, and design decisions the agent needs to know about.

Bad: "Add pagination"
Good: "Add pagination to GET /api/posts. Currently returns all rows. Use cursor-based pagination with `?cursor=<id>&limit=20`. The PostRepository already has a `findByIdGreaterThan` method. Update the controller and add integration tests."

**For teams, define the contract.** If backend and frontend agents need to agree on an API shape, write out the exact schema in both agents' descriptions.

**One concern per agent.** Do not overload a single agent with unrelated work. "Fix the login bug and also add the settings page" is two tasks.

**Trust the agent.** Give it the goal and constraints, not a numbered list of implementation steps. The agent will investigate the codebase and figure out the approach. Over-specifying the implementation leads to rigid, worse results.

**Include the project path.** Agents need to know where to work. Always use absolute paths.

**Mention tests explicitly.** If you want tests, say so in the acceptance criteria. Agents will not add tests unless asked.
