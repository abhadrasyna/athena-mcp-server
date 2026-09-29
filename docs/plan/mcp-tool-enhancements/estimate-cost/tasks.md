# Estimate cost (dry-run) MCP tool — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted (COST-1 is investigation-only). See `prompt.md` for why the story
exists; see `stories.md` for the per-task implementation spec.

**Open: COST-1, COST-2, COST-3.**

- [ ] **COST-1** — Investigate Athena's actual pre-execution cost-estimation mechanism | Owner: unassigned | Model: n/a | Review: none | SHA: —
- [ ] **COST-2** — Implement `estimate_cost` MCP tool | Owner: unassigned | Model: n/a | Review: none | SHA: —
- [ ] **COST-3** — Document `estimate_cost`'s real semantics/limitations | Owner: unassigned | Model: n/a | Review: none | SHA: —

## Story done when

- **COST-1** — this story's `stories.md` COST-2 section is updated (if needed) to reflect the actual, confirmed Athena API mechanism, not an assumption.
- **COST-2** — a mocked-boto3 test proves `estimate_cost` returns a scan-size estimate for a known query, distinct from `run_athena_sql`'s full-execution path.
- **COST-3** — `docs/mcp-server-setup.md` states plainly whether this tool executes any part of the query, so callers know the actual cost/risk before calling it.

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update this story's status in the epic `README.md` story-list, and add one line to `CONTEXT.md`'s "What
Exists" once COST-3 lands.
