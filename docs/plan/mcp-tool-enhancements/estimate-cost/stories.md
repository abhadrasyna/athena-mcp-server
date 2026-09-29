# Estimate cost (dry-run) MCP tool — story specs

> One task per session. Find the first unchecked item in `tasks.md`. That is your only task. Full implementation rules live in `AGENTS.md`/`PYTHON_DESIGN.md`.

---

## COST-1 — Investigate Athena's actual cost-estimation mechanism

**What to implement:**

1. Research (web search or AWS docs) whether `boto3`'s Athena client exposes any pre-execution cost/scan-size estimate (e.g. a query-planning API) that does not start billed
   query execution.
2. If no true dry-run exists: confirm the fallback approach — `start_query_execution`, poll briefly, read `Statistics.DataScannedInBytes` as soon as it's populated (Athena
   populates scan stats once the query plan is built, sometimes before full completion for large queries — confirm this timing claim rather than assuming it), then
   `stop_query_execution` to cancel further billed execution if the query hasn't already finished.
3. Record the confirmed mechanism directly in this file's COST-2 section below (edit it in place) before implementing anything.

**Tests:** none (investigation only).

**Commit:** none, unless the finding changes COST-2's plan (`docs(estimate-cost): record COST-1 finding`).

---

## COST-2 — Implement `estimate_cost` MCP tool

**Files to change / create:**
- `src/athena_runner/query_executor.py` — add a method (e.g. `AthenaQueryExecutor.estimate` or a new small class) implementing whichever mechanism COST-1 confirmed, reusing
  `BotoAthenaQueryExecutor`'s `_start`/polling helpers rather than duplicating them.
- `src/athena_mcp/query_tools.py` — add `estimate_cost(project: str, sql: str, database: Optional[str] = None, overrides: Optional[Mapping] = None) -> Dict[str, Any]` returning
  at least `data_scanned_bytes` and whichever other fields COST-1's mechanism naturally produces (e.g. `query_execution_id` if a query was actually started, so the caller can
  trace it in the AWS console).
- `src/athena_mcp/server.py` — register `@server.tool() def estimate_cost(...)`.
- `tests/athena_runner/test_query_executor.py`, `tests/athena_mcp/test_query_tools.py`, `tests/athena_mcp/test_server.py` — extend per the existing mocked-boto3 pattern.

**What to implement:**

1. Follow COST-1's confirmed mechanism exactly — do not silently fall back to "just call `run_athena_sql` and report its stats," which defeats this story's purpose (avoiding a
   full, billed run for exploratory queries).
2. If cancellation (`stop_query_execution`) is part of the mechanism, ensure it's called in a `finally`-equivalent path so a slow/hung query doesn't leave an uncancelled,
   fully-billed execution behind on an error.

**Tests (no network, no real external services):**
- `test_estimate_cost_happy_path` — fake Athena client returns scan stats after `start_query_execution`; tool returns them without downloading a result CSV.
- `test_estimate_cost_cancels_on_read` — if cancellation is part of the mechanism, assert the fake client's `stop_query_execution` was called.

**Commit:** `feat(mcp): add estimate_cost tool`

---

## COST-3 — Document `estimate_cost`'s real semantics

**Files to change / create:**
- `docs/mcp-server-setup.md` — add `estimate_cost` to the tool list, stating plainly (per COST-1's finding) whether/how much billed execution actually happens, so callers don't
  assume this is a zero-cost operation if it isn't.

**What to implement:**

1. Mirror the existing tool-list entries' format; add an explicit "cost/risk" note distinct from the other entries' format if COST-1 found execution is unavoidable.

**Tests:** none (docs-only).

**Commit:** `docs(mcp-server-setup): document estimate_cost`
