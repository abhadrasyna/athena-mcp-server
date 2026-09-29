# Tenant parameter support for registered queries — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted (TENANT-1 is investigation-only, no commit expected unless it produces
a doc update). See `prompt.md` for why the story exists; see `stories.md` for the per-task implementation spec.

**Open: TENANT-1, TENANT-2, TENANT-3.**

- [ ] **TENANT-1** — Confirm `aws-access-cli`'s tenant-plumbing contract (read-only investigation) | Owner: unassigned | Model: claude-opus-5.5 | Review: none | SHA: —
- [ ] **TENANT-2** — Add `tenant` parameter to `run_registered_athena_query`/`list_athena_queries` | Owner: unassigned | Model: claude-sonnet-5 | Review: none | SHA: —
- [ ] **TENANT-3** — Document the `tenant` parameter | Owner: unassigned | Model: claude-haiku-4.5 | Review: none | SHA: —

## Story done when

- **TENANT-1** — the exact mechanism by which `default_registry()`/query classes accept a tenant is written down in `stories.md`'s TENANT-2 spec (updated if the investigation
  finds it differs from this story's assumption), with no code changed in `aws-access-cli`.
- **TENANT-2** — a mocked-boto3 test proves a non-default `tenant` argument changes the resolved database/SQL.
- **TENANT-3** — `docs/mcp-server-setup.md` documents the parameter, including that it only applies to `mtn`.

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update this story's status in the epic `README.md` story-list, and add one line to `CONTEXT.md`'s "What
Exists" once TENANT-3 lands.
