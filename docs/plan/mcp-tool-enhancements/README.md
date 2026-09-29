# MCP tool enhancements — epic index

Grows `athena-mcp-server`'s MCP tool surface (currently 4 tools: `list_athena_queries`, `run_registered_athena_query`, `run_athena_sql`, `refresh_athena_sso`) to cover capabilities
already needed by real, observed usage in `~/github_copilot`'s consumer projects (`aws-access-cli`, `astro-events-household-report`, `applauseInvestigation`) — not speculative
features. Each story below cites the specific evidence that motivated it.

## Why this epic exists

Origin: a 2026-09-29 evaluation session that audited `oasis-athena-mcp` (this repo's predecessor), ported it into this independent repo, then reviewed the consumer projects'
actual Athena usage to find gaps between what the MCP server exposes today and what those projects already do manually or via duplicated one-off scripts. Every story here traces
to a concrete file in the reference workspace, not a hypothetical need.

## Scope decisions

- One epic, not 8 standalone stories, because several stories share technical scaffolding (`shaka-errors-report` reuses `adoption-metrics-report`'s date-range/report-store
  pattern) or a fixed build order matters (`onboard-applause-project` is easiest once discovery/tenant/partition tooling exists to replace its manual equivalents).
- `PYTHON_DESIGN.md`'s "don't build preemptively" rule still applies per-story: each story's `prompt.md` names the concrete consumer need it satisfies, not "might be useful
  someday."
- Tenant-level cross-cutting (`tenant-parameter-support`) is scoped separately from project-level cross-cutting (`onboard-applause-project`) — `project` (mtn/astro) and `tenant`
  (ZA/ZM/GH/NG, all under `mtn`) are different registries (`tool_config.PROJECT_CONFIGS` vs. `athena_runner.tenants.TenantRegistry`) and must not be conflated.

## Stories

| Story | Purpose | Status | Depends on | Closing SHA |
|---|---|---|---|---|
| `discover-tables/` | Expose the existing `discover_athena_tables.py`/`run_table_ddl_export.py` CLI logic as `discover_tables`/`describe_table` MCP tools. | ⬜ Not started | — | — |
| `tenant-parameter-support/` | Let `run_registered_athena_query` target a tenant (ZA/ZM/GH/NG), not just the hardcoded `DEFAULT_TENANT`. | ⬜ Not started | — | — |
| `estimate-cost/` | Add an `estimate_cost` (dry-run) MCP tool, previewing data-scanned/cost before executing. | ⬜ Not started | — | — |
| `list-partitions/` | Add a `list_partitions` MCP tool for correctly windowing time-based queries. | ⬜ Not started | — | — |
| `adoption-metrics-report/` | Port `aws-access-cli`'s date-range/month-chunked/multi-metric adoption-report subsystem as a dedicated tool pair. | ⬜ Not started | — | — |
| `shaka-errors-report/` | Port `aws-access-cli`'s per-day Shaka-error report; reuses `adoption-metrics-report`'s scaffolding. | ⬜ Not started | `adoption-metrics-report` | — |
| `saved-query-catalog/` | Unify Python-registered queries (mtn) and markdown-documented queries (astro's `QUERY_CATALOG.md`) behind one cross-project catalog tool. | ⬜ Not started | — | — |
| `onboard-applause-project/` | Register `applauseInvestigation`, port `run_athena_debug_events.py`'s queries. | ⬜ Not started | `discover-tables`, `tenant-parameter-support`, `list-partitions` | — |

Status: ⬜ Not started · 🔄 In progress · ✅ Done. This column is the epic's progress view — per-task checkboxes live only in each sub-story's `tasks.md`.

## Cross-cutting constraints

- No project-specific query logic lands in this repo (see `AGENTS.md`'s Domain conventions) — every story below adds *generic* tool surface, never a hardcoded `mtn`/`astro`/
  `applause` query body.
- Every new MCP tool must preserve stdio hygiene: no `print`, no `logging` to stdout, only `athena_runner.logging_setup.configure_logging` (stderr/file). See `AGENTS.md`'s
  Python-conventions exception and `tests/athena_mcp/test_server.py::test_logging_never_writes_to_stdout`.
- Every new tool needs a corresponding entry in `docs/mcp-server-setup.md`'s tool list and at least one mocked-boto3 unit test (no live AWS), matching the existing 101-test
  suite's convention.

## Supersession / coordination

None yet — this is the first epic in this repo.

## Epic done when

- **discover-tables** — `discover_tables`/`describe_table` MCP tools exist, tested, documented; `scripts/discover_athena_tables.py`/`run_table_ddl_export.py` either call into the
  same shared code or are marked superseded.
- **tenant-parameter-support** — `run_registered_athena_query`/`list_athena_queries` accept an optional `tenant` parameter; MTN's `default_registry()` instantiation path supports
  it end to end.
- **estimate-cost** — `estimate_cost` MCP tool returns a data-scanned/cost estimate without executing the query.
- **list-partitions** — `list_partitions` MCP tool lists a table's partitions.
- **adoption-metrics-report** — a tool pair covers `aws-access-cli`'s adoption-report date-range/multi-metric use case end to end.
- **shaka-errors-report** — a tool covers the Shaka-error-code per-day report use case, reusing `adoption-metrics-report`'s scaffolding.
- **saved-query-catalog** — one tool call lists every known query (Python-registered + markdown-documented) across all registered projects, with descriptions.
- **onboard-applause-project** — `applauseInvestigation` is a `PROJECT_CONFIGS` entry; its manual `run_athena_debug_events.py` two-step workflow is a registered query with
  `params`, not a standalone script.
