# Estimate cost (dry-run) MCP tool — prompt

> Adds an `estimate_cost` MCP tool that previews a query's data-scanned/cost impact without executing it.

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else. Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task. Read that task's full spec in
`stories.md` (same task id) before writing any code. One task per session. Complete it fully. Stop.

## Why this story exists

`applauseInvestigation/scripts/run_athena_debug_events.py` (a live, manual boto3 runner, not yet on the MCP server) has a `--dry-run` flag specifically because one of its query
modes (`debug-events-raw`, an unfiltered `SELECT *` against a debug-events table) can scan a large, expensive volume of data — its own docstring recommends running that mode
"first to eyeball what's actually in the table before narrowing." That is direct, real evidence that whoever is running ad-hoc Athena SQL through this MCP server wants a way to
see the cost/scan-size impact before committing to a full run, not just after (which is all `run_athena_sql`'s current `data_scanned_bytes` return value offers — after the fact).

## Scope guard

- In bounds: a new `estimate_cost(project, sql, database=None, overrides=None)` MCP tool, built on Athena's `StartQueryExecution` + immediate cancellation once bytes are known,
  or (preferred, if it works without executing) `GetQueryExecution` after an `EXPLAIN`-style plan call — confirm which Athena API actually supports pre-execution cost estimation
  before committing to an implementation approach (see Task overview).
- Out of bounds: automatically blocking/warning inside `run_athena_sql` itself based on a cost threshold — this story only adds a separate, opt-in preview tool; it does not change
  `run_athena_sql`'s existing contract.
- Changes runtime behavior: yes, adds 1 new MCP tool; no changes to existing tools.

## Session-start load hints

- `applauseInvestigation/scripts/run_athena_debug_events.py` — the concrete evidenced need (read-only reference).
- `src/athena_runner/query_executor.py` — the existing `AthenaQueryExecutor`/`BotoAthenaQueryExecutor` this tool must not duplicate wholesale; reuse `_start`/status-polling
  patterns where the estimate approach still requires starting (and then cancelling) a query.
- AWS Athena API docs (not in this workspace) — confirm whether `StartQueryExecution` supports a dry-run/plan-only mode, or whether "start + immediately
  `StopQueryExecution` once `Statistics.DataScannedInBytes` is available" is the only real option. Record the finding as this story's first task.

## Task overview

- **COST-1** — Investigate and record the actual Athena API mechanism available for pre-execution cost estimation (no code yet).
- **COST-2** — Implement `estimate_cost` per COST-1's finding.
- **COST-3** — Document the tool in `docs/mcp-server-setup.md`, including its actual semantics (e.g. "starts and cancels the query early" vs. "true dry-run, no query started" —
  whichever COST-1 found to be true) so callers aren't misled about what "estimate" means here.

## Definition of done

`estimate_cost` returns a data-scanned-bytes estimate (or the best approximation Athena's API actually supports) without leaving the caller with a fully-executed, fully-billed
query when a cheaper option exists.

## Perspectives not covered

If Athena's API genuinely has no true dry-run and the only option is "start, poll briefly, cancel," this tool cannot promise zero cost — it can only promise *lower* cost than
letting the query run to completion + downloading results. COST-3 must state this limitation explicitly rather than implying a free preview.
