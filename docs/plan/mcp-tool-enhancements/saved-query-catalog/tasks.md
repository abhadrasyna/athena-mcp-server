# Saved query catalog MCP tool — tasks

Work top-down. Find the first unchecked `- [ ]` and do only that task. Each task = one commit unless noted (CATALOG-1 is investigation-only). See `prompt.md` for why the story
exists; see `stories.md` for the per-task implementation spec.

**Open: CATALOG-1, CATALOG-2, CATALOG-3.**

- [ ] **CATALOG-1** — Confirm `QUERY_CATALOG.md`'s parseability / need for a structured sidecar | Owner: unassigned | Model: claude-sonnet-5 | Review: none | SHA: —
- [ ] **CATALOG-2** — Implement `list_saved_queries`/`describe_saved_query` | Owner: unassigned | Model: claude-sonnet-5 | Review: none | SHA: —
- [ ] **CATALOG-3** — Document the new tools, including the mtn/astro distinction | Owner: unassigned | Model: claude-haiku-4.5 | Review: none | SHA: —

## Story done when

- **CATALOG-1** — `stories.md`'s CATALOG-2 section reflects the confirmed parsing approach (markdown-parsing vs. sidecar file), not an assumption.
- **CATALOG-2** — tests prove both `mtn` and `astro` project catalogs are listable/describable through the same tool pair.
- **CATALOG-3** — `docs/mcp-server-setup.md` documents both tools and the runnable-vs-documentation-only distinction between projects.

## After each task

Set `SHA:` to the real commit SHA on the task line and tick the box. Then update this story's status in the epic `README.md` story-list, and add one line to `CONTEXT.md`'s "What
Exists" once CATALOG-3 lands.
