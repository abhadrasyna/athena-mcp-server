# Onboard applauseInvestigation project — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted (APPLAUSE-1 is investigation-only). See `prompt.md` for why the story
exists; see `stories.md` for the per-task implementation spec.

**Open: APPLAUSE-1, APPLAUSE-2, APPLAUSE-3.**

- [ ] **APPLAUSE-1** — Confirm debug-events table schema/partitioning and tenant scoping | Owner: unassigned | Model: n/a | Review: none | SHA: —
- [ ] **APPLAUSE-2** — Register project and port the two query modes | Owner: unassigned | Model: n/a | Review: none | SHA: —
- [ ] **APPLAUSE-3** — Document the new project/queries | Owner: unassigned | Model: n/a | Review: none | SHA: —

## Story done when

- **APPLAUSE-1** — `stories.md`'s APPLAUSE-2 section reflects confirmed schema/tenant findings, not assumptions.
- **APPLAUSE-2** — both query modes work through `run_registered_athena_query`, verified by mocked-boto3 tests matching the standalone script's semantics.
- **APPLAUSE-3** — `docs/mcp-server-setup.md` documents the new project and its queries.

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update this story's status in the epic `README.md` story-list, and add one line to `CONTEXT.md`'s "What
Exists" once APPLAUSE-3 lands.
