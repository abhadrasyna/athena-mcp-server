# Discover tables / describe table MCP tools — story specs

> One task per session. Find the first unchecked item in `tasks.md`. That is your only task. Full implementation rules live in `AGENTS.md`/`PYTHON_DESIGN.md`. After each task: set
> `SHA:` on the task line + tick the box, update the story status summary in the epic `README.md`.

---

## DISC-1 — Separate table-listing logic from argparse `main()`

**Files to change / create:**
- `scripts/discover_athena_tables.py` — extract the "run `SHOW TABLES`, return the list" core into a plain function (e.g. `list_tables(run_config, database) -> List[str]`) that
  `main()` calls; no behavior change for terminal use.
- `tests/cli_scripts/test_discover_athena_tables.py` — extend to cover the extracted function directly, not only via `main()`/argv.

**What to implement:**

1. Read the current `discover_athena_tables.py` end to end; identify the exact boundary between "parse argv, print output" and "run the query, return structured data."
2. Extract the latter into a function taking a `config_lib.RunConfig` and `database: str`, returning `List[str]` (table names) — reuse `athena_runner.query_executor`/existing
   helpers, no new boto3 call sites.
3. `main()` calls the extracted function and handles printing/argv as before.

**Tests (no network, no real external services):**
- `test_list_tables_happy_path` — fake Athena client returns a few table names, function returns them in the same order.
- `test_list_tables_empty_database` — fake client returns zero rows, function returns `[]`, not an error.

**Commit:** `refactor(discover-tables): extract list_tables() from CLI main()`

---

## DISC-2 — Add `discover_tables` MCP tool

**Files to change / create:**
- `src/athena_mcp/query_tools.py` — add `discover_tables(project: str, database: Optional[str] = None) -> List[str]`, resolving `project` via `tool_config.get_project_config`
  (defaulting `database` to the project's configured database, same pattern as `run_athena_sql`), calling DISC-1's extracted function.
- `src/athena_mcp/server.py` — register `@server.tool() def discover_tables(...)`, same docstring/typing conventions as the 4 existing tools.
- `tests/athena_mcp/test_query_tools.py`, `tests/athena_mcp/test_server.py` — add coverage matching the existing tool-test pattern (fake `AwsClientFactory`, no live AWS/MCP
  transport).

**What to implement:**

1. `query_tools.discover_tables` resolves the project config, builds a client factory the same way `_execute_and_download` does, and calls DISC-1's `list_tables`.
2. `server.discover_tables` is a thin `@server.tool()` wrapper, matching `list_athena_queries`'s style (no boto3/argparse in this module).

**Tests:**
- `test_discover_tables_happy_path` — returns the fake client's table names for a known project.
- `test_discover_tables_unknown_project` — raises the same `ValueError` shape as `run_athena_sql` for an unregistered project.

**Commit:** `feat(mcp): add discover_tables tool`

---

## DISC-3 — Add `describe_table` MCP tool

**Files to change / create:**
- `scripts/run_table_ddl_export.py` — extract its per-table `SHOW CREATE TABLE` fetch into a plain function (`fetch_table_ddl(run_config, database, table) -> str`), same pattern
  as DISC-1.
- `src/athena_mcp/query_tools.py` — add `describe_table(project: str, database: str, table: str) -> str`, calling the extracted function.
- `src/athena_mcp/server.py` — register `@server.tool() def describe_table(...)`.
- `tests/cli_scripts/test_run_table_ddl_export.py`, `tests/athena_mcp/test_query_tools.py`, `tests/athena_mcp/test_server.py` — extend per DISC-1/DISC-2's pattern.

**What to implement:**

1. Same extraction discipline as DISC-1, applied to `run_table_ddl_export.py`.
2. Same thin-adapter-plus-tool-registration discipline as DISC-2, applied to the new `describe_table` function.

**Tests:**
- `test_describe_table_happy_path` — returns the fake client's `SHOW CREATE TABLE` output verbatim.
- `test_describe_table_unknown_table` — surfaces the underlying Athena error (e.g. table not found) rather than swallowing it.

**Commit:** `feat(mcp): add describe_table tool`

---

## DISC-4 — Document both tools

**Files to change / create:**
- `docs/mcp-server-setup.md` — add `discover_tables`/`describe_table` to the tool list, same level of detail (args, return shape, one-line purpose) as the existing 4 tools'
  entries.

**What to implement:**

1. Mirror the existing tool-list entries' format exactly (no new heading structure).

**Tests:** none (docs-only).

**Commit:** `docs(mcp-server-setup): document discover_tables/describe_table`
