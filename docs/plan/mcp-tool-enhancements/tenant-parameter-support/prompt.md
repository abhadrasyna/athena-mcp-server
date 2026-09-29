# Tenant parameter support for registered queries — prompt

> Lets `run_registered_athena_query`/`list_athena_queries` target a specific tenant (ZA/ZM/GH/NG), instead of every call silently using the hardcoded `DEFAULT_TENANT` (South
> Africa).

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else. Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task. Read that task's full spec in
`stories.md` (same task id) before writing any code. One task per session. Complete it fully. Stop.

## Why this story exists

`src/athena_runner/tenants.py` (ported from `aws-access-cli`) already defines a `TenantRegistry` with 4 onboarded tenants (`ZA`/`e6auj7k7`, `ZM`/`a7vli5h8`, `GH`/`is1aldzq`,
`NG`/`jsxgloje`), and `aws-access-cli`'s query classes (e.g. `PlaybackOutcomeQuery.__init__(self, tenant: TenantConfig = tenants.DEFAULT_TENANT)`) already accept a `tenant`
constructor argument — this was `aws-access-cli`'s own `DA-2` work, already done there. But `queries/registry.py`'s `default_registry()` instantiates every query with **no**
tenant argument, so it silently defaults to `DEFAULT_TENANT` (ZA) every time. `tool_config._load_mtn_registry()` calls that same `default_registry()` with no way to pass a
tenant through. Net effect: this MCP server can only ever query South Africa's data for `mtn`, even though the underlying code already supports Zambia, Ghana, and Nigeria. This
story closes that specific, already-evidenced gap — it does not build new tenant infrastructure, `tenants.py` already exists.

## Scope guard

- In bounds: `src/athena_mcp/tool_config.py` (registry loading), `src/athena_mcp/query_tools.py` (tool signatures), `src/athena_mcp/server.py` (MCP tool parameter).
- Out of bounds: `aws-access-cli`'s own `queries/registry.py`/`default_registry()` — this is read-only reference; if `default_registry()` needs a `tenant` parameter added, that
  change happens in `aws-access-cli`'s own repo/session, not here. If that's blocking, this story's first task should confirm exactly what `default_registry()`'s signature
  supports today (it may already take an optional tenant list — verify before assuming a change is needed there).
- Does not touch the `astro` project (single-tenant, no `TenantRegistry` involvement).
- Changes runtime behavior: yes, adds a `tenant` parameter to 2 existing tools' contracts (additive, optional, defaults preserve current behavior).

## Session-start load hints

- `src/athena_runner/tenants.py` — the registry this story wires through, already ported and tested.
- `src/athena_mcp/tool_config.py`'s `_load_mtn_registry`/`_mount_external_subpackage` — the cross-repo mount mechanism a tenant parameter must flow through without breaking.
- `aws-access-cli/scripts/athena_runner/queries/registry.py` and `playback_outcome.py` (read-only reference) — confirm the exact tenant-plumbing contract before changing anything
  on this side.

## Task overview

- **TENANT-1** — Confirm `aws-access-cli`'s `default_registry()`/query-class constructors' exact tenant contract (read-only investigation, no code change).
- **TENANT-2** — Add an optional `tenant: str = "ZA"` parameter to `run_registered_athena_query`/`list_athena_queries`, resolved via `tenants.default_registry().get(tenant)`.
- **TENANT-3** — Document the new parameter in `docs/mcp-server-setup.md` and note the `mtn`-only scope (tenants are an `mtn`-specific concept; `astro` has none).

## Definition of done

`run_registered_athena_query(project="mtn", name="playback-outcome", params=..., tenant="ZM")` runs against Zambia's `unified_a7vli5h8` database, verified by a mocked-boto3 test
asserting the SQL/database resolved for a non-default tenant differs from the default-tenant case.

## Perspectives not covered

This story does not add `cross_tenant_query` (running the same query across all tenants in one call) — that's a separate, lower-priority backlog item (see the epic `README.md`)
that depends on this story landing first.
