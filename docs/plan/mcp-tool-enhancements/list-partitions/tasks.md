# List partitions MCP tool — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted (PART-1 is investigation-only). See `prompt.md` for why the story
exists; see `stories.md` for the per-task implementation spec.

**Open: PART-1, PART-2, PART-3.**

- [ ] **PART-1** — Confirm `SHOW PARTITIONS` vs. Glue `get_partitions` as the implementation mechanism | Owner: unassigned | Model: n/a | Review: none | SHA: —
- [ ] **PART-2** — Implement `list_partitions` MCP tool | Owner: unassigned | Model: n/a | Review: none | SHA: —
- [ ] **PART-3** — Document `list_partitions` | Owner: unassigned | Model: n/a | Review: none | SHA: —

## Story done when

- **PART-1** — `stories.md`'s PART-2 section reflects the confirmed mechanism, not an assumption.
- **PART-2** — a mocked-boto3/Glue test proves `list_partitions` returns real partition values for a known table.
- **PART-3** — `docs/mcp-server-setup.md` documents the tool alongside `discover_tables`/`describe_table`.

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update this story's status in the epic `README.md` story-list, and add one line to `CONTEXT.md`'s "What
Exists" once PART-3 lands.
