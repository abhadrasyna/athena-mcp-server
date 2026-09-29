# Saved query catalog MCP tool — story specs

> One task per session. Find the first unchecked item in `tasks.md`. That is your only task. Full implementation rules live in `AGENTS.md`/`PYTHON_DESIGN.md`.

---

## CATALOG-1 — Confirm `QUERY_CATALOG.md`'s parseability

**Files to read first (read-only, reference):**
- `astro-events-household-report/QUERY_CATALOG.md` — read the actual markdown structure: is each query a consistently-formatted heading + description + SQL code block (regex/
  markdown-parser-friendly), or is it free-form prose that would be fragile to parse programmatically?
- `astro-events-household-report/README.md` — check for any existing structured index (YAML front-matter, a companion JSON/YAML file) that might already exist or be easy to
  add without disrupting the human-readable doc.

**What to implement:**

1. If `QUERY_CATALOG.md` is consistently structured (e.g. every query is an H2/H3 heading followed by a fenced SQL block and a one-line description), plan to parse it directly
   with a markdown parser already available in `requirements.txt` (check before adding a new dependency) or a minimal regex-based extractor.
2. If it's not consistently structured, plan for a small structured sidecar (e.g. `astro-events-household-report/QUERY_CATALOG.yaml`, generated once by hand from the existing
   doc) that this MCP server's `astro` project config points to — record explicitly that this sidecar must be kept in sync manually when queries change (same class of drift risk
   as the `tenants.py` bug), and flag this in CATALOG-3's docs.
3. Record the decision directly in this file's CATALOG-2 section (edit in place) before implementing.

**Tests:** none (investigation only).

**Commit:** none, unless the finding warrants its own doc commit (`docs(saved-query-catalog): record CATALOG-1 finding`).

---

## CATALOG-2 — Implement `list_saved_queries`/`describe_saved_query`

**Files to change / create:**
- `src/athena_mcp/tool_config.py` — extend `PROJECT_CONFIGS`/astro's config entry with a path to the catalog source (markdown or sidecar, per CATALOG-1).
- `src/athena_mcp/query_catalog.py` (new) — parsing logic for whichever source CATALOG-1 confirmed, kept separate from `query_tools.py`'s existing `mtn`-registry logic.
- `src/athena_mcp/query_tools.py` — add `list_saved_queries(project: str) -> List[Dict[str, str]]` (name + one-line description) and
  `describe_saved_query(project: str, name: str) -> Dict[str, str]` (full description + SQL text). For `mtn`, delegate to the existing `list_athena_queries`/registry rather than
  reimplementing; for `astro`, delegate to the new `query_catalog.py`.
- `src/athena_mcp/server.py` — register both as `@server.tool()`.
- `tests/athena_mcp/test_query_catalog.py` (new), `test_query_tools.py`, `test_server.py` — cover both project paths.

**What to implement:**

1. Keep `mtn`'s path a thin delegation to existing code — no duplicate registry logic.
2. `astro`'s path reads whatever CATALOG-1 confirmed (markdown or sidecar) at call time (no caching complexity needed initially) — read from disk, don't hardcode query text.

**Tests (no network, no real external services):**
- `test_list_saved_queries_mtn_delegates_to_registry` — `project="mtn"` output matches `list_athena_queries`'s existing output.
- `test_list_saved_queries_astro_reads_catalog` — `project="astro"` output matches a small fixture catalog file, not the real `astro-events-household-report` file (tests must
  not depend on files outside this repo).
- `test_describe_saved_query_unknown_name` — clear error, not a raw parse exception, for a name that doesn't exist in either project's catalog.

**Commit:** `feat(mcp): add list_saved_queries and describe_saved_query tools`

---

## CATALOG-3 — Document the new tools

**Files to change / create:**
- `docs/mcp-server-setup.md` — add both tools to the tool list. Explicitly state: `mtn`'s saved queries are runnable via `run_registered_athena_query`; `astro`'s saved queries
  are documentation-only and must still be run manually via `run_athena_sql` (this story does not make them runnable) — and flag the sidecar-sync risk if CATALOG-1 chose that
  approach.

**What to implement:**

1. Mirror the existing tool-list entries' format; add the explicit mtn/astro distinction as its own short subsection so it isn't missed.

**Tests:** none (docs-only).

**Commit:** `docs(mcp-server-setup): document saved query catalog tools`
