# Setting up the Athena MCP server

This repo ships an MCP server (`athena-mcp-server`) that exposes Athena querying — registered per-project reports plus ad-hoc SQL — as tools any MCP-capable agent (Copilot CLI, etc.) can call. See
`docs/plans/athena-mcp-server/story.md` for the full design rationale; this doc is the operational "how do I register and use it" reference.

## 1. Install this repo's virtualenv

From this repo's root:

```
make venv
```

This creates `.venv/`, installs dev dependencies, and `pip install -e .` registers the `athena-mcp-server` console script (declared in `pyproject.toml`'s `[project.scripts]`) at
`.venv/bin/athena-mcp-server`.

Verify it works standalone first:

```
.venv/bin/athena-mcp-server --help
```

## 2. Register with Copilot CLI (user/global level)

Copilot CLI loads MCP server configuration from multiple sources (confirmed via `copilot mcp --help` in this environment, not guessed):

| Scope | File |
|---|---|
| User (global, all repos/cwds) | `~/.copilot/mcp-config.json` |
| Workspace (this repo/cwd only) | `.mcp.json` or `.github/mcp.json` |
| Plugin | Installed plugins with MCP servers |

Register this server at the **user/global level** — not scoped to any one project's repo — so it's already usable from `aws-access-cli`, `applauseInvestigation`, and `astro-events-household-report`'s
cwd without per-project registration or code duplication:

```
copilot mcp add athena-mcp-server -- /Users/abhadra/myWork/myOffice/athena-mcp-server/.venv/bin/athena-mcp-server
```

(Equivalent to running `/mcp add` inside an interactive Copilot CLI session and answering its prompts with the same command.) This is a **local stdio** server: Copilot CLI spawns
`.venv/bin/athena-mcp-server` as a subprocess and talks JSON-RPC over its stdin/stdout. Use the absolute path to this repo's own `.venv` (not a bare `athena-mcp-server` on `$PATH`) so the registration
doesn't depend on this repo's venv being activated in whatever shell Copilot CLI happens to run in.

No `--env` flags are needed — `athena-mcp-server`'s own argparse flags (`--output-dir`, `--log-dir`, `--poll-interval`, `--timeout`) all default relative to *this repo's* root (see "Config defaults"
below), regardless of the caller's cwd.

Confirm registration:

```
copilot mcp list
copilot mcp get athena-mcp-server
```

or, inside an interactive session, run `/mcp` and confirm `athena-mcp-server` is listed alongside any other configured servers.

### Relationship to `synamedia-mcp-hub`

`synamedia-mcp-hub` is a **remote, org-managed** MCP endpoint (`https://mcp.ai.synamedia.com`), added centrally at the org level — there is no local file this repo's registration touches or merges
into, and no way (or need) to inject a server into someone else's remote hub. `athena-mcp-server` registers as an **additional, independent local MCP server**; it appears alongside `synamedia-mcp-hub`
and `github-mcp-server` in the same Copilot CLI session, side by side, not merged into either.

### Approval gate still applies

Registering this server via MCP does **not** loosen the workspace `AGENTS.md` hard gate: "never invoke Lightstep/Jira/GitHub Enterprise/AWS CLI/Athena without explicit per-call go-ahead." Every tool
below ultimately runs an AWS SSO refresh and/or an Athena query — state the exact tool/query you intend to run and get explicit turn-by-turn go-ahead before calling any of them, exactly as you would
for a raw script or manual console query.

## 3. Tools exposed

All 4 tools take a `project` parameter (currently registered: `mtn`; `astro` is a known-but-unconfigured placeholder — calling any tool with `project="astro"` today raises a clear
`NotImplementedError` rather than silently half-working, pending `ASTRO-4`'s account/role/ bucket/region discovery). See `src/athena_mcp/tool_config.py`'s `PROJECT_CONFIGS` for the registry.

1. **`list_athena_queries(project)`** — Returns `project`'s registered Athena queries, each as `{name, database, description}`, so an agent can discover what exists without reading source.

2. **`run_registered_athena_query(project, name, params, overrides=None)`** — Looks up query `name` in `project`'s registry, builds and runs its SQL, downloads the CSV result, and returns
   `query_execution_id`, `output_location`, `data_scanned_bytes`, `engine_execution_ms`, `csv_path`, and an inline `preview` (`columns`/`rows`/ `total_rows_previewed`/`truncated`, first ~20 rows).
   - `params`: `dict[str, str]`, query-specific (e.g. `{"date": "2026-07-08"}`).
   - `overrides`: optional per-call `RunConfig` field overrides — `profile`, `workgroup`, `output_location`, `region`, `timeout_seconds`.

3. **`run_athena_sql(project, sql, database=None, overrides=None)`** — Ad-hoc query, passed through verbatim (no SELECT-only regex, no forced LIMIT — every registered project's IAM role is already
   read-only). `database` defaults to `project`'s configured database if omitted. Same return shape and `overrides` as tool #2.

4. **`refresh_athena_sso(project, overrides=None)`** — Pre-warms AWS SSO credentials for `project`'s profile so a batch of subsequent tool calls doesn't each pay the refresh cost. Returns `True` if
   credentials were already valid, `False` if a refresh was required (and it succeeded).

Every one of tools 2–4 calls `ensure_valid_sso_credentials` as a pre-flight step first — auto-refresh-on-expiry is preserved, not bypassed, exactly as it works in the underlying `athena_runner` CLI
scripts.

## 4. Config defaults (server-wide, not project-specific)

Set via `athena-mcp-server`'s argparse flags, all resolved relative to **this repo's root**, never the caller's cwd (the server may be invoked from any project's directory once registered at the
user/global level):

| Flag | Default |
|---|---|
| `--output-dir` | `<this repo>/output` |
| `--log-dir` | `<this repo>/logs` |
| `--poll-interval` | `2` (seconds between Athena query status polls) |
| `--timeout` | `300` (seconds) |

To override, add the flags after the command in the registration, e.g.:

```
copilot mcp add athena-mcp-server -- /Users/abhadra/myWork/myOffice/athena-mcp-server/.venv/bin/athena-mcp-server --timeout 600
```

## 5. Stdio hygiene (why this matters if something looks broken)

MCP over stdio uses stdout **exclusively** for JSON-RPC protocol frames. `athena_mcp.cli` configures logging (via `athena_runner.logging_setup`) to write only to stderr/the log file before the server
starts — never stdout. If a tool call ever appears to hang or return malformed output, check `<log-dir>/*.log` first; a stray `print()` or misconfigured log handler writing to stdout would corrupt the
protocol stream. This is covered by `tests/athena_mcp/test_server.py::test_logging_never_writes_to_stdout`.

## 6. Removing / updating the registration

```
copilot mcp remove athena-mcp-server
```

then re-run `copilot mcp add` (step 2) after any code change that affects the command/args needed to start the server (e.g. moving this repo, or adding new default flags you want baked into the
registration).
