# Saved query catalog MCP tool — prompt

> Unifies `mtn`'s Python-registered queries and `astro`'s markdown-documented `QUERY_CATALOG.md` behind one cross-project `list_saved_queries`/`describe_saved_query` tool pair.

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else. Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task. Read that task's full spec in
`stories.md` (same task id) before writing any code. One task per session. Complete it fully. Stop.

## Why this story exists

`list_athena_queries` already exists for `mtn`'s registered queries (`queries/registry.py`-backed). But `astro-events-household-report/README.md` and `QUERY_CATALOG.md` show a
second, parallel "catalog" of queries that only exists as markdown documentation — described but not runnable through the MCP server; someone reads the doc, copies SQL by hand,
and runs it via `run_athena_sql`. This story closes that inconsistency: one project's queries are discoverable and runnable via MCP, the other's are discoverable only by reading
a doc file. The goal is one coherent `list_saved_queries(project)` behavior regardless of which project's queries happen to be backed by Python classes versus markdown today.

## Scope guard

- In bounds: `list_saved_queries(project)` / `describe_saved_query(project, name)` that work for both `mtn` (delegating to existing `list_athena_queries`/registry) and `astro`
  (parsing `QUERY_CATALOG.md` or an equivalent structured source — see Task overview for the exact mechanism to confirm).
- Out of bounds: does not make `astro`'s catalog queries *runnable* via `run_registered_athena_query` in this story — `astro` queries are markdown-documented SQL, not Python
  query classes; making them runnable would mean porting each one into a query class, which is a separate, larger effort not scoped here. This story only unifies *discovery*.
- Does not deprecate `list_athena_queries` — `list_saved_queries` either wraps it or coexists with it; confirm which at Task 1 rather than assuming a rename/replacement.
- Changes runtime behavior: yes, adds 2 new MCP tools; does not remove or change `list_athena_queries`.

## Session-start load hints

- `astro-events-household-report/README.md`, `QUERY_CATALOG.md` (read-only reference) — the markdown-only catalog this story needs to make MCP-discoverable.
- `src/athena_mcp/query_tools.py`'s existing `list_athena_queries` — the `mtn`-side precedent to reuse/wrap, not duplicate.
- `src/athena_mcp/tool_config.py`'s `PROJECT_CONFIGS` — where `astro`'s catalog source path would need to be registered.

## Task overview

- **CATALOG-1** — Confirm `QUERY_CATALOG.md`'s actual structure (is it consistently formatted enough to parse programmatically, or does it need a structured sidecar file, e.g.
  YAML/JSON, generated once from the markdown and kept in sync manually?).
- **CATALOG-2** — Implement `list_saved_queries(project)`/`describe_saved_query(project, name)` per CATALOG-1's finding.
- **CATALOG-3** — Document the new tools in `docs/mcp-server-setup.md`, explicit about the `mtn` (runnable) vs. `astro` (documentation-only, must still be run manually via
  `run_athena_sql`) distinction so callers aren't misled into expecting both to work identically.

## Definition of done

`list_saved_queries(project="astro")` returns the same query names/descriptions a human reading `QUERY_CATALOG.md` would see, and `list_saved_queries(project="mtn")` returns the
same set `list_athena_queries` already returns — verified by tests against both projects.

## Perspectives not covered

This story does not solve query staleness (if `QUERY_CATALOG.md` and the actual SQL drift apart, that's the same class of drift bug as the `tenants.py` gap this whole port
started from — worth flagging in `CATALOG-3`'s docs as a known risk, not solving here).
