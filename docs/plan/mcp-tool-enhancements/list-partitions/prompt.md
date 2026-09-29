# List partitions MCP tool — prompt

> Adds a `list_partitions` MCP tool so callers can see a table's available partitions (e.g. date/tenant ranges) before writing a query against it.

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else. Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task. Read that task's full spec in
`stories.md` (same task id) before writing any code. One task per session. Complete it fully. Stop.

## Why this story exists

This was already an identified gap in `ih-project-scaffold/athena/docs/athena-conventions.md`'s backlog before this epic existed. It gets sharper evidence from
`aws-access-cli/scripts/athena_runner/adoption/`'s month-chunked query pattern (real code walks a date range in monthly chunks specifically to keep each Athena query's scanned
partition set bounded) and from `applauseInvestigation/scripts/run_athena_debug_events.py`'s manual, hand-written date-range handling — both are workarounds for not being able
to first ask "what partitions actually exist for this table" before deciding how to chunk a query. `discover_tables`/`describe_table` (the other story in this epic) tell you a
table's schema and partition *keys*; this story tells you the partition *values* that actually exist.

## Scope guard

- In bounds: one new MCP tool, `list_partitions(project, table, database=None, limit=100)`, backed by Athena's `SHOW PARTITIONS` or Glue's `get_partitions` API (confirm which is
  more appropriate — see Task overview).
- Out of bounds: does not add partition *filtering* to `run_athena_sql`/`run_registered_athena_query` — this tool is read-only discovery, same spirit as `discover_tables`.
- Depends on `discover-tables` landing first only loosely (shares the "table discovery" tool family and doc section, not code) — can be built independently if needed, but should
  be documented alongside `discover_tables`/`describe_table` in `docs/mcp-server-setup.md` for a coherent tool-family narrative.
- Changes runtime behavior: yes, adds 1 new MCP tool.

## Session-start load hints

- `ih-project-scaffold/athena/docs/athena-conventions.md` — original backlog mention (read-only reference).
- `aws-access-cli/scripts/athena_runner/adoption/month_chunks.py` (or equivalent) — the manual chunking workaround this tool would let callers replace with an actual partition
  lookup (read-only reference).
- `src/athena_mcp/query_tools.py`'s `discover_tables`/`describe_table` (once the `discover-tables` story lands) — reuse the same boto3 client wiring and error-handling shape.

## Task overview

- **PART-1** — Confirm whether `SHOW PARTITIONS <table>` (via Athena `StartQueryExecution`, billed as a normal query) or Glue's `get_partitions` (via `boto3` Glue client, not
  billed as Athena query time) is the better-fitting mechanism for this codebase's existing client wiring.
- **PART-2** — Implement `list_partitions(project, table, database=None, limit=100)` per PART-1's finding.
- **PART-3** — Document the tool in `docs/mcp-server-setup.md`.

## Definition of done

`list_partitions(project="mtn", table="events")` returns the actual partition values present for that table (e.g. distinct `dt=`/tenant values), verified via a mocked-boto3 test,
without requiring the caller to already know or guess partition boundaries.

## Perspectives not covered

This story does not add partition-count/size statistics per partition (that would overlap with `estimate-cost`); it only lists which partition values exist.
