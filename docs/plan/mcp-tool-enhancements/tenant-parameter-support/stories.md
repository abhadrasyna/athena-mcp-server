# Tenant parameter support for registered queries — story specs

> One task per session. Find the first unchecked item in `tasks.md`. That is your only task. Full implementation rules live in `AGENTS.md`/`PYTHON_DESIGN.md`.

---

## TENANT-1 — Confirm the tenant-plumbing contract

**Files to read (read-only, `aws-access-cli` is reference — no edits there):**
- `aws-access-cli/scripts/athena_runner/queries/registry.py` — does `default_registry()` accept any tenant-related argument today, or does it hardcode `DEFAULT_TENANT` via each
  query class's own constructor default with no override path?
- `aws-access-cli/scripts/athena_runner/queries/playback_outcome.py`, `session_debug_events.py`, `incomplete_no_destroy_session_ids.py` — do all three query classes accept a
  `tenant` constructor argument, or only some?

**What to implement:**

1. Read the three query classes' `__init__` signatures; confirm each accepts `tenant: TenantConfig = tenants.DEFAULT_TENANT`.
2. Read `default_registry()`; confirm it calls each constructor with zero arguments (i.e. always `DEFAULT_TENANT`).
3. Record the finding in this file (edit this section directly) — if `default_registry()` already accepts a tenant list/mapping, TENANT-2's plan below needs to change to use
   that mechanism instead of instantiating queries directly.

**Tests:** none (investigation only).

**Commit:** none, unless the finding changes TENANT-2's plan enough to warrant updating this doc as its own commit (`docs(tenant-parameter-support): record TENANT-1 finding`).

---

## TENANT-2 — Add `tenant` parameter to registered-query tools

**Files to change / create:**
- `src/athena_mcp/tool_config.py` — `_load_mtn_registry()` currently returns a `QueryRegistryProtocol` built via `default_registry()` with no tenant awareness. Add a way to
  build a tenant-scoped registry: if `default_registry()` supports a tenant argument (per TENANT-1), pass it through; if not, instantiate the query classes directly here with the
  resolved `TenantConfig`, bypassing `default_registry()` for the tenant-specific case only (Open/Closed: don't change `aws-access-cli`'s registry, adapt on this side).
- `src/athena_mcp/query_tools.py` — `run_registered_athena_query`/`list_athena_queries` gain an optional `tenant: str = "ZA"` parameter, resolved via
  `athena_runner.tenants.default_registry().get(tenant)` into a `TenantConfig`, passed down to the registry-loading path above.
- `src/athena_mcp/server.py` — both `@server.tool()` wrappers gain the same optional `tenant: str = "ZA"` parameter, documented in their docstrings.
- `tests/athena_mcp/test_tool_config.py`, `test_query_tools.py`, `test_server.py` — extend to cover a non-default tenant resolving to a different database (e.g. `ZM` →
  `unified_a7vli5h8`), and an unknown tenant code raising the same `KeyError` shape `TenantRegistry.get()` already raises.

**What to implement:**

1. Resolve `tenant` to a `TenantConfig` once, early, in `query_tools.py` — reuse `athena_runner.tenants.default_registry()` and its existing `KeyError` message, don't
   reimplement tenant lookup.
2. Thread the resolved `TenantConfig` into whichever registry-loading path TENANT-1 confirmed (either `default_registry(tenant=...)` if that exists, or direct instantiation).
3. Do not change `project` resolution (`tool_config.get_project_config`) — `tenant` is a sub-selector *within* `mtn`, orthogonal to `project`.

**Tests (no network, no real external services):**
- `test_run_registered_query_default_tenant_unchanged` — omitting `tenant` still resolves to `ZA`/`unified_e6auj7k7`, proving no behavior change for existing callers.
- `test_run_registered_query_non_default_tenant` — `tenant="ZM"` resolves to `unified_a7vli5h8` in the built SQL/database passed to the fake executor.
- `test_run_registered_query_unknown_tenant` — `tenant="XX"` raises `KeyError` with the same "Unknown tenant" message `TenantRegistry.get()` produces.

**Commit:** `feat(mcp): add tenant parameter to registered-query tools`

---

## TENANT-3 — Document the `tenant` parameter

**Files to change / create:**
- `docs/mcp-server-setup.md` — update `run_registered_athena_query`/`list_athena_queries`'s entries with the new `tenant` parameter, its default (`"ZA"`), and an explicit note
  that it is `mtn`-specific (no effect for `astro`, which has no `TenantRegistry`).

**What to implement:**

1. Mirror the existing tool-list entries' format exactly.

**Tests:** none (docs-only).

**Commit:** `docs(mcp-server-setup): document tenant parameter`
