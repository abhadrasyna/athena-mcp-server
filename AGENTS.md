# athena-mcp-server — AI Assistant Pre-Task Protocol

> Auto-loaded at session start. Keep this file thin — push bulky detail into a lazily-loaded skill once there's enough of it to warrant one, once this file stops fitting on one screen.

## Step 1 — Read CONTEXT.md first

Read `CONTEXT.md` before writing any code. State `CONTEXT.md ✓` verbatim in your first user-facing response — reading the file without the visible acknowledgment leaves no record this step ran.

<!--
Add a module-AGENTS.md index row here once the project has multiple modules each with their own auto-loaded AGENTS.md. Not needed at Tier 0.

Add a DB_REGISTRY.md pointer here once the project writes to a database with more than one or two tables, or once "which table holds X" stops being obvious from the code. Not needed at Tier 0. -->

No module-level `AGENTS.md` files or `DB_REGISTRY.md` exist yet — this repo has a single flat module set (`athena_runner`, `athena_mcp`) and doesn't own/write application tables in Athena (it only
queries existing tenant tables registered in `src/athena_runner/tenants.py`), so neither trigger has fired.

## Step 2 — Confirm scope

If the prompt does not name specific files, ask before starting. One clarifying question beats building the wrong thing.

**Before assuming code is wanted at all:** a project idea that sounds like software doesn't mean code should be written yet. Confirm whether this session wants an implementation (a real `src/`, a
chosen language/storage/ framework), or is still in design/planning (markdown notes, a `docs/` folder, a story to write up) — do not default to scaffolding a package just because the prompt named a
project idea. If code is confirmed wanted: confirm which files change, and tests required (default: yes).

<!--
Add a Step 2b council checkpoint here once a decision surfaces that is (1) load-bearing and costly to reverse, (2) has two defensible approaches with materially different outcomes, and (3) spans
multiple disciplines at once — this can fire on day one for a high-stakes small project (e.g. tax-bracket logic), it is not gated on project size. Until then, skip straight to Step 3. -->

No Step 2b council checkpoint has fired yet — no decision so far has been both load-bearing/hard-to-reverse and split across materially different approaches spanning multiple disciplines. The
cross-repo `_load_mtn_registry` sibling-checkout mount (see `CONTEXT.md`'s Current Constraints) is the closest candidate to watch if it ever needs a structural alternative.

## Step 3 — State plan, wait for go-ahead

> Plan: [one sentence] → touches [file1, file2] → tests in [test file] → commit. Proceed?

If the plan touches more than 2 files, wait for explicit go-ahead.

No additional multi-surface checkpoint beyond the 2-file threshold is defined yet; Step 3's rule (wait for explicit go-ahead past 2 files) is the only gate currently in force.

<!-- marker: tier1 -->
## Story/epic planning (`docs/plan/`)

Work above a single-sitting fix is tracked as a story (one coherent goal) or epic (2+ related stories) under `docs/plan/<slug>/` — see `docs/plan/README.md` for the file-set conventions and
`docs/plan/_TEMPLATE/README.md` for how to start one (`cp -r docs/plan/_TEMPLATE/story docs/plan/<slug>`). Structure and checkbox consistency are enforced at commit time by the
`docs-plan-story-structure`/`docs-plan-checkbox-consistency` pre-commit hooks (see `tooling/docs-plan/`) — a malformed plan folder fails the commit, not a later review.
No further tier1-level overlay content beyond the story/epic conventions above is pending.

## Step 4 — Tests are mandatory

Every public function needs one happy-path test + one error/edge-case test. No network in tests.

Run `make test` (wraps `pytest`) for the full suite, or `pytest tests/<path>` to target a module. `pytest tests/athena_mcp/test_tool_config.py` specifically re-verifies the cross-repo
`aws-access-cli` query-registry mount noted in `CONTEXT.md` — run it after any change to either repo's `athena_runner` module set.

## Step 5 — Close the phase (docs → tests → commit)

A phase is not complete until all three are done.

**5a — Update docs:** `CONTEXT.md` "What Exists" if new files were added.

Also check `docs/table-ddl-knowledge-guide.md` and `docs/mcp-server-setup.md` for staleness whenever `PROJECT_CONFIGS`, tenant registrations, or the registered MCP tool list change.

New root-level `.md` files are reserved for protocol/status docs (`AGENTS.md`, `CONTEXT.md`, `README.md`, `PYTHON_DESIGN.md`, `suggestions.md`); everything else (setup guides, knowledge guides,
story/epic tracking) goes under `docs/` or `docs/plan/`.

**5b — Verify tests green** before committing.

**5c — Commit:** use the `commit` skill's message format. The commit must be executed, not drafted — a written-out message is not a commit.

<!--
Add a mandatory code-reviewer subagent gate here once the project is large or high-stakes enough to warrant an isolated review pass before every commit (Tier 2). Until then, review the diff yourself
before committing. -->

No recurring audit cadence is set up yet — revisit once the `session-close` skill's `suggestions.md` entries have accumulated enough history to review in aggregate rather than session-by-session.

## Python conventions

<!--
Delete this whole section if the project isn't Python. If it is, keep only what's actually true for this project — do not carry over Decimal/asyncio-daemon specifics unless the project actually
touches money or runs a long-lived concurrent service. -->

- Python 3.10+, type hints on all public function signatures.
- Functions 10–20 lines typical. Split only when it improves clarity.
- `Decimal` for all monetary values, never `float` — only if this project touches money.
- Offline-first tests: zero network, zero real tokens, zero real DBs by default.

<!-- marker: python -->
- Type hints on **all** public function signatures, not just new/touched ones.
- `(str, Enum)` for string enums — never `StrEnum` (py3.11+ only, this overlay targets 3.10+).
- `Decimal` for monetary values, opt in only if this project actually touches money — do not add it speculatively.
- `pyproject.toml` + `requirements.txt`/`requirements-dev.txt` (not a `pyproject.toml`-only dependency model).
- Call `setup_logging()` from `logs/setup_logging.py` once at process start; never `logging.basicConfig` elsewhere, never bare `logging.getLogger(__name__)` in `scripts/` (loses module context when
  run as `__main__`). **Exception, this project:** this is an MCP server over stdio, where stdout is reserved exclusively for JSON-RPC frames (see `docs/mcp-server-setup.md`). Use
  `athena_runner.logging_setup.configure_logging` instead — it only ever writes to stderr or a log file, never stdout, and that invariant is enforced by
  `tests/athena_mcp/test_server.py::test_logging_never_writes_to_stdout`. `logs/setup_logging.py` (stdout + file) is intentionally not used here.
- Every new package directory under `src/`, `scripts/`, or `tests/` needs an `__init__.py`, even a one-line comment. **Exception:** `src/athena_runner/` is deliberately a PEP 420 namespace package (no
  `__init__.py`) — see its module docstrings and `tool_config.py`'s registered-query-registry loading mechanism for why.
- Design principles beyond the basics (SOLID as checkable triggers, named patterns): `PYTHON_DESIGN.md`, load on trigger only — not resident here.
No further python-tier overlay content beyond the conventions above is pending.

## Domain conventions

- This repo hosts only the generic Athena SSO/execution stack (`src/athena_runner/`) and the MCP server layer around it (`src/athena_mcp/`). No project-specific query logic lands here — each consuming
  project (`aws-access-cli`, `astro-events-household-report`, `applauseInvestigation`) keeps its own domain-specific `AthenaQuery`/`AdoptionMetric` definitions locally.
- `src/athena_mcp/tool_config.py`'s `PROJECT_CONFIGS` is the only place a `project` name (e.g. `mtn`, `astro`) resolves to a profile/database/bucket/region — MCP tools never accept raw AWS config from
  a caller.
- `src/athena_runner/tenants.py` is a tenant → Athena database/table naming registry, ported from `aws-access-cli`. Onboard a new tenant by registering a `TenantConfig`, never by hardcoding a
  database/table literal in a query class.
- Every MCP tool call must go through `cli_common.ensure_valid_sso_credentials` before executing — never assume a cached AWS SSO session is still valid.

## Git conventions

- Commit messages: imperative mood, ≤60 char subject. Body explains why, not what.
- Never amend pushed commits. New commit to fix, not force-push.
- Stage specific files — never `git add .` blindly.

## Markdown formatting

Write prose paragraphs filled to ≤200 characters per line, not hard-wrapped at ~80. A paragraph is one logical block of text with no mid-sentence line breaks up to the 200-char cap — reflow it as a
single flowing block, don't hand-wrap at whatever width happens to look right in this editor. This applies to every markdown file in this project (`AGENTS.md`, `CONTEXT.md`, `README.md`, skill files,
any future `docs/`), from the first file written. Code blocks, tables, and list-item structure are unaffected — this is a prose-wrapping rule, not a whole-file reformat.

<!--
Once this project is identified as Python (see Python conventions above), add a reflow/check tool + pre-commit hook to enforce this automatically instead of relying on manual discipline. Not needed at
Tier 0 — the written rule above is the whole mechanism until then. -->

## No throwaway code in production folders

A quick POC or exploration always starts in `scratch/` first (see `scratch/SCRATCH.md`) and only graduates to `src/`/`scripts/` once it's proven, via the convergence rule documented there. This is a
hard requirement, not just an available option.
