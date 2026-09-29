# MCP tool enhancements — prompt (router)

Central entry point for this epic. Your work-session entry skill loads this file, **not** a sub-story `prompt.md`. Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else,
then follow the steps below to find and run exactly one task.

**Origin:** `README.md` in this folder — the epic index. Read it if you have not this session; it carries the scope decisions, the ordered story list, and the cross-cutting
constraints this router's logic depends on.

---

## Step 1 — find the next task

Story order is fixed — it is the row order of the **Stories** table in this folder's `README.md`. Keep this list identical to that table:

1. `discover-tables/` — expose table discovery/DDL as MCP tools
2. `tenant-parameter-support/` — let registered queries target a tenant, not just `DEFAULT_TENANT`
3. `estimate-cost/` — dry-run cost estimate before executing
4. `list-partitions/` — list a table's partitions
5. `adoption-metrics-report/` — date-range/multi-metric adoption report tool pair
6. `shaka-errors-report/` — per-day Shaka-error-code report   (blocked by: `adoption-metrics-report` complete)
7. `saved-query-catalog/` — cross-project query catalog
8. `onboard-applause-project/` — register `applauseInvestigation` as a project   (blocked by: `discover-tables`, `tenant-parameter-support`, `list-partitions` complete)

Do not jump ahead even if a later story looks more urgent.

Open `discover-tables/tasks.md`. If it has any unchecked `- [ ]` line, the first one (top to bottom) is your task — stop searching, go to Step 2. Only if every box in that story's
`tasks.md` is checked: open the next story's `tasks.md` per the fixed order above, first unchecked line is your task. And so on. If every sub-story `tasks.md` is fully checked, the
epic is complete — say so and stop; do not invent new work.

## Step 2 — confirm you are the right owner

The task line carries `| Owner: … | Model: … | Review: … | SHA: …`. Read it before doing anything.

- If `Owner` does not match the agent running this session, **stop** and report: which task you found, what it is routed to, and that this session should not implement it.
- If `Model` names a model this session is not running, say so before proceeding.
- Note the `Review` gate now — if it names a review agent or step, that gate is mandatory before commit per this project's own `AGENTS.md`.

## Step 3 — load the sub-story context

Read that story's own `prompt.md` for its hard constraints (test-gate command, non-fatal contracts, coordination checks) and its `stories.md` for the task's full spec.

## Step 4 — implement, verify, record

Follow the sub-story `prompt.md`'s protocol: implement, run `make test` and `make lint` (this repo's test gate), commit via the `commit` skill (execute it, do not just draft the
message), set `SHA:` on the task line + tick the box, update this epic's `README.md` story-list status column, add one line to `CONTEXT.md`'s "What Exists" if a new module/tool
landed.

**Stop.** One task per session — do not proceed to the next unchecked item in any story.
