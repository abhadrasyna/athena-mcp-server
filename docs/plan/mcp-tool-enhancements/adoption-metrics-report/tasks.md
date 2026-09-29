# Adoption metrics report MCP tool — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit. See `prompt.md` for why the story exists; see `stories.md` for the per-task
implementation spec.

**Open: ADOPT-1, ADOPT-2, ADOPT-3.**

- [ ] **ADOPT-1** — Port `adoption/` modules into `src/athena_runner/adoption/` | Owner: unassigned | Model: n/a | Review: none | SHA: —
- [ ] **ADOPT-2** — Add `run_adoption_report`/`list_adoption_metrics` MCP tools | Owner: unassigned | Model: n/a | Review: none | SHA: —
- [ ] **ADOPT-3** — Document adoption-report tools | Owner: unassigned | Model: n/a | Review: none | SHA: —

## Story done when

- **ADOPT-1** — the ported modules pass a straight-port equivalence check (same public functions/classes, same signatures, tests green) with no behavior change.
- **ADOPT-2** — a mocked-boto3 test proves a multi-month date range produces month-chunked results matching the source subsystem's chunking behavior.
- **ADOPT-3** — `docs/mcp-server-setup.md` documents both tools, including the chunking behavior.

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update this story's status in the epic `README.md` story-list, and add one line to `CONTEXT.md`'s "What
Exists" once ADOPT-3 lands.
