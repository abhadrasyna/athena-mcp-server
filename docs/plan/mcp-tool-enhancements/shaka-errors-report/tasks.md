# Shaka errors report MCP tool — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit. See `prompt.md` for why the story exists; see `stories.md` for the per-task
implementation spec.

**Open: SHAKA-1, SHAKA-2, SHAKA-3.**

- [ ] **SHAKA-1** — Port `shaka_errors/` modules, reusing `adoption/` scaffolding where possible | Owner: unassigned | Model: claude-sonnet-5 | Review: none | SHA: —
- [ ] **SHAKA-2** — Add `run_shaka_errors_report` MCP tool | Owner: unassigned | Model: claude-sonnet-5 | Review: none | SHA: —
- [ ] **SHAKA-3** — Document `run_shaka_errors_report` | Owner: unassigned | Model: claude-haiku-4.5 | Review: none | SHA: —

## Story done when

- **SHAKA-1** — ported module(s) pass a straight-port equivalence check with no behavior change; any reuse of `adoption/` scaffolding is intentional, not coincidental.
- **SHAKA-2** — a mocked-boto3 test proves the tool returns a per-day error-count report matching the source subsystem's shape.
- **SHAKA-3** — `docs/mcp-server-setup.md` documents the tool.

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update this story's status in the epic `README.md` story-list, and add one line to `CONTEXT.md`'s "What
Exists" once SHAKA-3 lands.
