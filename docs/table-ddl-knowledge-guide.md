# Building a table-inventory knowledge doc for a new project

How to go from "a new project's Athena database" to a committed `knowledge/<project>-athena-<database>-tables.md` file, using the project-agnostic scripts added in `MCP-10`. Mirrors the style of
`knowledge/mtn-athena-unified_e6auj7k7-tables.md`.

None of these scripts hardcode any project's SSO profile, output bucket, or region -- every AWS-facing flag below must be supplied explicitly, so the same steps work for `mtn`, `astro`, or any future
project.

## Prerequisites

- An AWS SSO profile that can query the project's Athena database/workgroup (see `../../docs/aws-sso-setup.md` and `src/athena_runner/sso_profiles.py` if it needs registering there for the MCP server
  too).
- This repo's venv set up (`make venv`).
- `SHOW TABLES` / `SHOW CREATE TABLE` are metadata-only queries -- they scan 0 bytes and are unbilled in Athena. The only real cost of a big export is wall-clock time (roughly 1-2s per table), not AWS
  spend.

All commands below run from `athena-mcp-server/`.

## Step 1 -- Discover every table in the database

```bash
PYTHONPATH=src:scripts .venv/bin/python scripts/discover_athena_tables.py \
  --database <database> \
  --profile <sso-profile> \
  --workgroup <workgroup> \
  --output-location s3://<query-results-bucket>/ \
  --region <region> \
  --output ../output/<project>_<database>_tables.csv
```

Writes a one-column `table_name` CSV listing every table.

## Step 2 -- Decide DDL scope, filter the CSV

Not every table needs full `SHOW CREATE TABLE` DDL in the knowledge doc -- production/canonical tables do; ad-hoc views, dated snapshots, and personal scratch tables (`temp_*`, `*_backup`, etc.)
usually don't.

Open `../output/<project>_<database>_tables.csv`, categorize the tables, and save a second CSV (same `table_name` header) containing only the ones you want DDL for, e.g.
`../output/<project>_<database>_tables_canonical.csv`.

## Step 3 -- Export DDL for the filtered tables

```bash
PYTHONPATH=src:scripts .venv/bin/python scripts/run_table_ddl_export.py \
  --database <database> \
  --tables-csv ../output/<project>_<database>_tables_canonical.csv \
  --profile <sso-profile> \
  --workgroup <workgroup> \
  --output-location s3://<query-results-bucket>/ \
  --region <region> \
  --batch-size 10 \
  --output ../output/<project>_<database>_table_ddl.csv
```

- `--dry-run` first if you just want to double-check which tables would be exported, without touching Athena.
- Tables are fetched in `--batch-size`-sized batches (default 10); SSO credentials are re-checked/refreshed and the CSV is flushed to disk after every batch, so an interruption (e.g. an SSO token
  expiring mid-run) loses at most one in-flight batch, not the whole export.
- A failing/permission-denied table doesn't abort the run -- its `ddl` column is recorded as `ERROR: <reason>` and the export continues.

## Step 4 -- Compose the knowledge doc

```bash
cd ..   # workspace root
python3 scripts/update_athena_table_ddl_knowledge.py \
  --csv athena-mcp-server/output/<project>_<database>_table_ddl.csv \
  --markdown knowledge/<project>-athena-<database>-tables.md
```

This inserts (or replaces, on a re-run) a `## DDL reference` section -- one `###` heading + fenced ```sql``` block per table -- between fixed `<!-- DDL_SECTION:BEGIN/END -->` marker comments, so
re-running it after a later re-export only touches that section and leaves any hand-written notes elsewhere in the file untouched.

Before/after that generated section, hand-write (or have an LLM draft from Step 1's full table list) the rest of the doc: a short intro, and a categorized inventory of every *other* table (views,
scratch tables, etc.) by name/category only -- no DDL needed for those.

## Worked example

`ASTRO-5` in `docs/plans/athena-mcp-server/tasks.md` is a concrete, already-scoped instance of this exact workflow (Astro's `default` database, ~20 canonical tables DDL'd out of 215 total) -- read it
for a full real-world example, including how the table categories were decided.
