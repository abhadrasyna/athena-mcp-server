# CONTEXT.md

> Mutable snapshot of "what's true right now." Always edited in place, never appended to — this is not a log. Read this before writing any code; state `CONTEXT.md ✓` in your first response of a
> session so there's a record this step ran.

## What Exists

- `src/athena_runner/` — generic Athena execution stack (`config`, `aws_clients`, `query_executor`, `result_downloader`, `sso_auth`, `sso_profiles`, `cli_common`, `logging_setup`, `date_utils`,
  `exceptions`, `tenants`), ported from `github_copilot/oasis-athena-mcp` (originally from `aws-access-cli/scripts/athena_runner/`). No single "god object" — each module owns one responsibility.
- `src/athena_mcp/` — the MCP server layer: `server.py` (4 registered tools: `list_athena_queries`, `run_registered_athena_query`, `run_athena_sql`, `refresh_athena_sso`), `tool_config.py`
  (`PROJECT_CONFIGS` registry for `mtn`/`astro`), `query_tools.py` (adapters over `athena_runner`), `result_preview.py` (inline CSV preview), `cli.py` (the `athena-mcp-server` console-script entry
  point).
- `scripts/athena_cli_common.py`, `scripts/discover_athena_tables.py`, `scripts/run_table_ddl_export.py` — table-discovery/DDL-export CLI tooling (see `docs/table-ddl-knowledge-guide.md`).
- `tests/` — mocked-boto3 unit tests (101 tests as of the port), no live AWS/MCP transport.
- `docs/mcp-server-setup.md` — how to register this server with Copilot CLI.
- `docs/plan/` — story/epic tracking (`_TEMPLATE/` to start a new one); `tooling/docs-plan/` enforces structure at commit time.

## Key Decisions

See `DECISIONS.md` for the append-only rationale log — created on the first real architecture decision, not before. Until that file exists, there is nothing to point to here.

## Current Constraints

- No project-specific query logic lands here (see `AGENTS.md`'s Domain conventions) — each consuming project keeps its own `AthenaQuery`/`AdoptionMetric` definitions locally.
- MCP-over-stdio hygiene: only `athena_runner.logging_setup.configure_logging` (stderr/file) may be used for logging — never the generic `logs/setup_logging.py` pattern, which writes to stdout
  (reserved for JSON-RPC frames). See `AGENTS.md`'s Python conventions exception.
- Known open item at port time: `src/athena_mcp/tool_config.py`'s `_load_mtn_registry` mounts `aws-access-cli`'s `queries/` directory as this repo's `athena_runner.queries` sub-package via a
  sibling-checkout path (`../aws-access-cli/scripts/athena_runner/queries`, overridable via `MTN_QUERY_REGISTRY_DIR`). This cross-repo namespace-package merge is inherently fragile — verify it still
  resolves cleanly (`pytest tests/athena_mcp/test_tool_config.py`) after any change to either repo's `athena_runner` module set.

## Pre-Task Protocol

See `AGENTS.md` for the Step 1–5 protocol this project follows.

<!--
Tier 3 note: once this file's "What Exists" list gets too flat to navigate, split it into CONTEXT_TREE.md (a derived file → one-line-purpose index) and leave this section as a pointer to it. -->
