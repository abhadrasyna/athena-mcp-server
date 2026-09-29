# Onboard applauseInvestigation project — prompt

> Registers `applauseInvestigation` as a real project in `PROJECT_CONFIGS`, replacing its standalone `run_athena_debug_events.py` script with registered MCP queries — the last
> step in bringing all known ad-hoc Athena usage under this MCP server.

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else. Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task. Read that task's full spec in
`stories.md` (same task id) before writing any code. One task per session. Complete it fully. Stop.

## Why this story exists

`applauseInvestigation/scripts/run_athena_debug_events.py` is a manual, standalone boto3 script — not registered with this MCP server at all. It has two query modes
(`debug-events-raw` unfiltered scan, and a filtered device→session-id two-step join), a `--dry-run` flag, and hand-written date-range handling. It represents a real, currently-
unserved consumer of Athena that this MCP server should support like `mtn`/`astro` do. This story is sequenced last because it depends on capabilities the other stories add:
`discover_tables`/`describe_table` (to explore the debug-events table schema during onboarding), `tenant-parameter-support` (if `applauseInvestigation` needs tenant scoping,
confirm at Task 1), and `list_partitions` (to replace the script's hand-written date-range logic with a real partition lookup).

## Scope guard

- In bounds: add `applauseInvestigation` to `PROJECT_CONFIGS`, port its two query modes as registered query classes (mirroring `mtn`'s `queries/` pattern), expose them via
  `run_registered_athena_query`.
- Out of bounds: does not delete/deprecate the standalone script in `applauseInvestigation` itself — that's a separate repo, out of scope for edits here; this story only adds
  the MCP-side equivalent. Whether the standalone script is later retired is a decision for that repo's own maintainers.
- Depends on `discover-tables`, `tenant-parameter-support`, `list-partitions` landing first (uses their tools/capabilities during onboarding and in the ported query
  implementation).
- Changes runtime behavior: yes, adds a new project + its registered queries.

## Session-start load hints

- `applauseInvestigation/scripts/run_athena_debug_events.py` (read-only reference) — the two query modes and `--dry-run` flag to port.
- `src/athena_mcp/tool_config.py`'s `PROJECT_CONFIGS` — the registration pattern `mtn`/`astro` already follow.
- `aws-access-cli/scripts/athena_runner/queries/` (read-only reference) — the query-class pattern (`base.py`, concrete query subclasses) to mirror for the two new query modes.

## Task overview

- **APPLAUSE-1** — Confirm the debug-events table's schema/partitioning (using `discover_tables`/`describe_table`/`list_partitions` once available) and whether tenant scoping
  applies to this project.
- **APPLAUSE-2** — Register `applauseInvestigation` in `PROJECT_CONFIGS` and port the two query modes as query classes usable via `run_registered_athena_query`.
- **APPLAUSE-3** — Document the new project/queries in `docs/mcp-server-setup.md`.

## Definition of done

`run_registered_athena_query(project="applauseInvestigation", name="debug-events-raw", ...)` and the filtered device→session-id join mode both work through the MCP server,
verified by mocked-boto3 tests, matching the standalone script's existing query semantics.

## Perspectives not covered

This story does not add new query capabilities beyond what the standalone script already does — it is purely an onboarding/registration story, not a feature-expansion one for
`applauseInvestigation` itself.
