# List partitions MCP tool — story specs

> One task per session. Find the first unchecked item in `tasks.md`. That is your only task. Full implementation rules live in `AGENTS.md`/`PYTHON_DESIGN.md`.

---

## PART-1 — Confirm `SHOW PARTITIONS` vs. Glue `get_partitions`

**What to implement:**

1. Check whether this codebase already has a Glue client wired anywhere (`src/athena_runner/`) — if not, using Glue means adding a new AWS client/permission surface, which
   `SHOW PARTITIONS` (reusing the existing Athena `StartQueryExecution` client) would avoid.
2. Confirm whether `SHOW PARTITIONS` counts as billed Athena query time (it typically scans metadata only, not data, but still runs as a query execution with its own
   `QueryExecutionId` and needs the same polling/result-fetch code path already in `query_executor.py`) versus Glue's `get_partitions`, which is a direct metadata API call with
   no query execution/billing semantics at all.
3. Record the decision directly in this file's PART-2 section (edit in place) with the reasoning, before implementing.

**Tests:** none (investigation only).

**Commit:** none, unless the finding is substantial enough to warrant its own doc commit (`docs(list-partitions): record PART-1 finding`).

---

## PART-2 — Implement `list_partitions` MCP tool

**Files to change / create:**
- `src/athena_runner/query_executor.py` (if `SHOW PARTITIONS` chosen) or a new `src/athena_runner/glue_client.py` (if Glue chosen) — implement the confirmed mechanism.
- `src/athena_mcp/query_tools.py` — add `list_partitions(project: str, table: str, database: Optional[str] = None, limit: int = 100) -> Dict[str, Any]` returning partition
  values (each as a dict of partition-key → value) and a `truncated: bool` flag if `limit` was hit.
- `src/athena_mcp/server.py` — register `@server.tool() def list_partitions(...)`.
- `tests/athena_mcp/test_query_tools.py`, `test_server.py`, and either `tests/athena_runner/test_query_executor.py` or a new `test_glue_client.py` — extend per the existing
  mocked-boto3 pattern (mock Athena or Glue client responses, not real AWS calls).

**What to implement:**

1. Reuse `tool_config.get_project_config`/database resolution exactly as `discover_tables`/`describe_table` do (once that story lands) — do not duplicate project→database
   mapping logic.
2. Cap results at `limit` (default 100) and set `truncated: True` if more partitions exist than returned, so callers aren't misled into thinking a table has few partitions when
   it was actually cut off.

**Tests (no network, no real external services):**
- `test_list_partitions_happy_path` — fake client returns 3 partitions for a known table; tool returns all 3, `truncated: False`.
- `test_list_partitions_truncated` — fake client returns more than `limit`; tool returns exactly `limit` entries, `truncated: True`.
- `test_list_partitions_unknown_table` — fake client raises the table-not-found error Athena/Glue actually raises; tool surfaces a clear error, not a raw boto3 traceback.

**Commit:** `feat(mcp): add list_partitions tool`

---

## PART-3 — Document `list_partitions`

**Files to change / create:**
- `docs/mcp-server-setup.md` — add `list_partitions` to the tool list, next to `discover_tables`/`describe_table`, noting the `limit`/`truncated` behavior.

**What to implement:**

1. Mirror the existing tool-list entries' format exactly.

**Tests:** none (docs-only).

**Commit:** `docs(mcp-server-setup): document list_partitions`
