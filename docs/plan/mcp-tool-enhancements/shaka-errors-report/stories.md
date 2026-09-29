# Shaka errors report MCP tool — story specs

> One task per session. Find the first unchecked item in `tasks.md`. That is your only task. Full implementation rules live in `AGENTS.md`/`PYTHON_DESIGN.md`.

---

## SHAKA-1 — Port `shaka_errors/` modules

**Files to read first (read-only, `aws-access-cli` is reference):**
- `aws-access-cli/scripts/athena_runner/shaka_errors/*.py` — read every module; list the real file names/public API.
- `src/athena_runner/adoption/` (already ported by the prior story) — identify what's directly reusable (date-range handling, report-store shape) versus what `shaka_errors`
  does independently.

**Files to change / create:**
- `src/athena_runner/shaka_errors/__init__.py` and ported module file(s).
- `tests/athena_runner/shaka_errors/` — ported/adapted tests.

**What to implement:**

1. Copy modules with minimal changes, same approach as `adoption-metrics-report`'s ADOPT-1.
2. Where `shaka_errors` genuinely reuses `adoption/`'s date-range or report-store code (not just structurally similar, but the same source utility), import it directly rather
   than copying it a second time — check the source repo first: does `shaka_errors/` already import from `adoption/` there, or are they fully independent? Match the source's own
   coupling, don't introduce new coupling that doesn't exist upstream.

**Tests:** port source tests if they exist; otherwise minimal coverage proving the module imports and runs against a mocked boto3 client without error.

**Commit:** `feat(shaka-errors): port shaka errors report subsystem from aws-access-cli`

---

## SHAKA-2 — Add `run_shaka_errors_report` MCP tool

**Files to change / create:**
- `src/athena_mcp/query_tools.py` — add `run_shaka_errors_report(project: str, start_date: str, end_date: str) -> Dict[str, Any]`.
- `src/athena_mcp/server.py` — register as `@server.tool()`.
- `tests/athena_mcp/test_query_tools.py`, `test_server.py` — extend per the existing mocked-boto3 pattern.

**What to implement:**

1. Thin adapter over SHAKA-1's ported module — no new report logic here.

**Tests (no network, no real external services):**
- `test_run_shaka_errors_report_happy_path` — known date range produces a per-day error-count report matching the source subsystem's shape.
- `test_run_shaka_errors_report_empty_range` — a range with zero matching rows returns an empty/zero report, not an error.

**Commit:** `feat(mcp): add run_shaka_errors_report tool`

---

## SHAKA-3 — Document `run_shaka_errors_report`

**Files to change / create:**
- `docs/mcp-server-setup.md` — add the tool to the tool list, next to `run_adoption_report` since they're structurally related.

**What to implement:**

1. Mirror the existing tool-list entries' format.

**Tests:** none (docs-only).

**Commit:** `docs(mcp-server-setup): document run_shaka_errors_report`
