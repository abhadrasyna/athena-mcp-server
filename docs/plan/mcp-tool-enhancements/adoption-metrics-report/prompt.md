# Adoption metrics report MCP tool — prompt

> Ports `aws-access-cli`'s `adoption/` subsystem (date-range, month-chunked, multi-metric report generation) into a registered MCP tool pair, instead of leaving it a manual,
> un-ported script family.

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else. Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task. Read that task's full spec in
`stories.md` (same task id) before writing any code. One task per session. Complete it fully. Stop.

## Why this story exists

`aws-access-cli/scripts/athena_runner/adoption/` is real, working, currently-used code — a metric runner, month-chunking helper, and period-report store — that generates
multi-metric adoption reports over arbitrary date ranges. `query_tools.py`'s own docstring in that repo explicitly says this subsystem is deferred/not-yet-ported to the MCP
server. That means today, running an adoption report requires someone to run raw Python scripts directly against `aws-access-cli`, bypassing the MCP server entirely — the exact
kind of workflow this MCP server exists to standardize.

## Scope guard

- In bounds: port `metric_runner`, `month_chunks`, `period_report_store` (or whatever the actual 3-4 module names are — confirm at Task 1) into `src/athena_runner/adoption/`,
  and expose a `run_adoption_report(project, metrics, start_date, end_date)` MCP tool.
- Out of bounds: does not port `shaka_errors/` (separate story, `shaka-errors-report`, deliberately sequenced after this one so it can reuse this story's month-chunking/report-
  store scaffolding instead of duplicating it).
- Does not change the underlying metric SQL/logic — straight port, same spirit as the `tenants.py` port already done for this repo.
- Changes runtime behavior: yes, adds new tool(s); does not touch existing tools.

## Session-start load hints

- `aws-access-cli/scripts/athena_runner/adoption/` (read-only reference) — the full subsystem to port; read every module here before starting Task 1.
- `src/athena_runner/tenants.py` — the precedent for how a prior port from this same source tree was done in this repo (structure, tests, docstring conventions to match).
- `src/athena_mcp/tool_config.py` — where the ported subsystem's project/tenant config needs to plug in, if it needs tenant awareness (check whether adoption metrics are
  per-tenant; if so, this story may need `tenant-parameter-support` landed first — confirm at Task 1 and update this file's "depends on" note if so).

## Task overview

- **ADOPT-1** — Inventory the real `adoption/` module list, its public API, and whether it's tenant-aware; port module files with minimal changes (mirroring the `tenants.py`
  port precedent).
- **ADOPT-2** — Add `run_adoption_report`/`list_adoption_metrics` MCP tools wrapping the ported modules.
- **ADOPT-3** — Document the new tools in `docs/mcp-server-setup.md`, including the month-chunking behavior (why a multi-month range returns chunked results, not a single blob).

## Definition of done

`run_adoption_report(project="mtn", metrics=[...], start_date=..., end_date=...)` produces the same shape of report the standalone `aws-access-cli` scripts produce today, verified
by a mocked-boto3 test against a known multi-month date range (proving the month-chunking logic survived the port intact).

## Perspectives not covered

This story does not add a scheduling/cron mechanism for recurring adoption reports — it only exposes on-demand report generation via MCP tool call, matching how the source
scripts are actually invoked today (manually, on demand).
