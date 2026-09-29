# Onboard applauseInvestigation project — story specs

> One task per session. Find the first unchecked item in `tasks.md`. That is your only task. Full implementation rules live in `AGENTS.md`/`PYTHON_DESIGN.md`.

---

## APPLAUSE-1 — Confirm schema/partitioning and tenant scoping

**Files to read first (read-only, `applauseInvestigation` is reference):**
- `applauseInvestigation/scripts/run_athena_debug_events.py` — read both query modes (`debug-events-raw`, device→session-id join) in full; note the exact SQL, parameters, and
  the `--dry-run` flag's behavior.

**What to implement:**

1. Using this repo's `discover_tables`/`describe_table` tools (from the `discover-tables` story) against the debug-events table referenced in the script, confirm its actual
   schema and partition keys.
2. Using `list_partitions` (from the `list-partitions` story), confirm what partition values exist, to inform how the ported query classes should accept date-range parameters.
3. Check whether the script's queries reference any tenant-specific database/table naming (per `tenant-parameter-support`'s `TenantRegistry`) — if `applauseInvestigation` is
   single-tenant, note this explicitly so APPLAUSE-2 doesn't add unnecessary tenant plumbing.
4. Record findings directly in this file's APPLAUSE-2 section (edit in place) before implementing.

**Tests:** none (investigation only).

**Commit:** none, unless findings warrant their own doc commit (`docs(onboard-applause-project): record APPLAUSE-1 finding`).

---

## APPLAUSE-2 — Register project and port query modes

**Files to change / create:**
- `src/athena_mcp/tool_config.py` — add an `applauseInvestigation` entry to `PROJECT_CONFIGS` (database name, region, any other fields `mtn`/`astro` entries already have).
- `src/athena_runner/queries/debug_events_raw.py`, `src/athena_runner/queries/debug_events_session_join.py` (or equivalent names, confirmed at APPLAUSE-1) — new query classes
  mirroring the `base.py` pattern from `aws-access-cli/scripts/athena_runner/queries/` (read-only reference for the pattern, not copied verbatim since these are new queries,
  not ports of existing `mtn` ones).
- `src/athena_mcp/tool_config.py`'s registry-loading path — register the two new query classes so `run_registered_athena_query(project="applauseInvestigation", ...)` resolves
  them.
- `tests/athena_runner/queries/test_debug_events_raw.py`, `test_debug_events_session_join.py`, and `tests/athena_mcp/test_tool_config.py` — cover both query modes with mocked
  boto3 responses.

**What to implement:**

1. Match the standalone script's existing SQL/parameters exactly for both modes — this is an onboarding/registration story, not a query-rewrite; behavior must match what the
   script already does.
2. Only add tenant-parameter support here if APPLAUSE-1 found it's actually needed — don't add unused plumbing.
3. Preserve the `--dry-run` semantics as evidence to route users toward `estimate_cost` (from the `estimate-cost` story) instead of duplicating a separate dry-run mechanism —
   document this pointer in code comments/docstrings, don't reimplement dry-run logic a third time in this repo.

**Tests (no network, no real external services):**
- `test_debug_events_raw_matches_standalone_script_sql` — resolved SQL matches the standalone script's query text (character-for-character or with only expected parameter
  substitution differences).
- `test_debug_events_session_join_two_step_flow` — the device→session-id join mode correctly performs its two-step lookup, matching the standalone script's logic.

**Commit:** `feat(applause): register applauseInvestigation project and port debug-events queries`

---

## APPLAUSE-3 — Document the new project/queries

**Files to change / create:**
- `docs/mcp-server-setup.md` — add `applauseInvestigation` to the documented project list, with its two registered queries, following the same format as `mtn`'s existing
  entries.

**What to implement:**

1. Mirror the existing project-documentation format exactly.
2. Note that this MCP-side registration exists alongside (not instead of) the standalone script in `applauseInvestigation`'s own repo, since retiring that script is out of
   scope here (see `prompt.md`'s Scope guard).

**Tests:** none (docs-only).

**Commit:** `docs(mcp-server-setup): document applauseInvestigation project`
