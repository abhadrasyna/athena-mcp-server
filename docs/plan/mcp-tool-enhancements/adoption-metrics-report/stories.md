# Adoption metrics report MCP tool — story specs

> One task per session. Find the first unchecked item in `tasks.md`. That is your only task. Full implementation rules live in `AGENTS.md`/`PYTHON_DESIGN.md`.

---

## ADOPT-1 — Port `adoption/` modules

**Files to read first (read-only, `aws-access-cli` is reference):**
- `aws-access-cli/scripts/athena_runner/adoption/*.py` — read every module; list the actual file names/public API (this file's plan uses placeholder names —
  `metric_runner`/`month_chunks`/`period_report_store` — confirm the real names and update this section if they differ).
- `aws-access-cli/scripts/athena_runner/adoption/`'s own tests (if any exist there) — port these test files too, don't just port implementation without coverage.

**Files to change / create:**
- `src/athena_runner/adoption/__init__.py` and the ported module files (mirroring the real names found above).
- `tests/athena_runner/adoption/` — ported tests, adjusted for this repo's import paths.

**What to implement:**

1. Copy each module with minimal changes — only adjust imports (e.g. `from athena_runner.tenants import ...` if the source used a different relative path) and anything that
   assumed the old sibling-checkout layout (same class of fix as `tool_config.py`'s `_DEFAULT_MTN_QUERIES_DIR`, per `AGENTS.md`'s documented precedent).
2. Confirm whether adoption metrics are tenant-aware (do any ported modules accept/require a `TenantConfig`?). If yes, note in this file whether this story should now be
   resequenced after `tenant-parameter-support` — update the epic `README.md`'s dependency table if so, rather than silently working around it.
3. Do not change metric SQL/business logic — this is a straight port, same as `tenants.py`.

**Tests:** port the source subsystem's own tests if they exist; otherwise write minimal coverage proving each ported module imports and runs against a mocked boto3 client
without error.

**Commit:** `feat(adoption): port adoption metrics subsystem from aws-access-cli`

---

## ADOPT-2 — Add `run_adoption_report`/`list_adoption_metrics` MCP tools

**Files to change / create:**
- `src/athena_mcp/query_tools.py` — add `list_adoption_metrics(project: str) -> List[str]` (returns known metric names) and
  `run_adoption_report(project: str, metrics: List[str], start_date: str, end_date: str) -> Dict[str, Any]` (returns the chunked report).
- `src/athena_mcp/server.py` — register both as `@server.tool()`.
- `tests/athena_mcp/test_query_tools.py`, `test_server.py` — extend per the existing mocked-boto3 pattern.

**What to implement:**

1. Wrap ADOPT-1's ported modules directly — this layer is a thin MCP-tool adapter, not new report logic.
2. Preserve the source subsystem's month-chunking behavior exactly (a 4-month range must produce 4 chunked sub-results, not one merged blob, unless the source itself merges them
   — confirm and match, don't guess).

**Tests (no network, no real external services):**
- `test_run_adoption_report_single_month` — one-month range produces one chunk.
- `test_run_adoption_report_multi_month` — multi-month range produces the same chunk count/boundaries the source subsystem would produce (assert against `month_chunks`'
  ported logic directly, not a hardcoded guess).
- `test_list_adoption_metrics_returns_known_metrics` — matches the source subsystem's metric registry.

**Commit:** `feat(mcp): add run_adoption_report and list_adoption_metrics tools`

---

## ADOPT-3 — Document adoption-report tools

**Files to change / create:**
- `docs/mcp-server-setup.md` — add both tools to the tool list, explaining the month-chunking behavior so callers aren't surprised by a chunked response shape.

**What to implement:**

1. Mirror the existing tool-list entries' format; include an example of a multi-month call and its chunked response shape.

**Tests:** none (docs-only).

**Commit:** `docs(mcp-server-setup): document adoption-report tools`
