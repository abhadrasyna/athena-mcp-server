# Discover tables / describe table MCP tools — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted. See `prompt.md` for why the story exists; see `stories.md` for the
per-task implementation spec.

**Open: DISC-1, DISC-2, DISC-3, DISC-4.**

- [ ] **DISC-1** — Separate `discover_athena_tables.py`'s table-listing logic from its argparse `main()` | Owner: unassigned | Model: claude-sonnet-5 | Review: none | SHA: —
- [ ] **DISC-2** — Add `discover_tables` MCP tool | Owner: unassigned | Model: claude-sonnet-5 | Review: none | SHA: —
- [ ] **DISC-3** — Add `describe_table` MCP tool | Owner: unassigned | Model: claude-sonnet-5 | Review: none | SHA: —
- [ ] **DISC-4** — Document both tools in `docs/mcp-server-setup.md` | Owner: unassigned | Model: claude-haiku-4.5 | Review: none | SHA: —

## Story done when

- **DISC-1** — the table-listing logic is callable as a plain function, independent of argparse, and the CLI script still works unchanged when invoked from the terminal.
- **DISC-2** — `discover_tables(project, database=None)` is a registered MCP tool, unit-tested with a fake `AwsClientFactory`.
- **DISC-3** — `describe_table(project, database, table)` is a registered MCP tool, unit-tested with a fake `AwsClientFactory`.
- **DISC-4** — `docs/mcp-server-setup.md`'s tool list includes both new tools with the same level of detail as the existing 4.

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update this story's status in the epic `README.md` story-list, and add one line to `CONTEXT.md`'s "What
Exists" once DISC-4 lands.
