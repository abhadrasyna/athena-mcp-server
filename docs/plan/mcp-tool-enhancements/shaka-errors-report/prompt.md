# Shaka errors report MCP tool — prompt

> Ports `aws-access-cli`'s `shaka_errors/` subsystem (simpler per-day error-count report) into a registered MCP tool, reusing the `adoption-metrics-report` story's scaffolding.

Read `CONTEXT.md` and state `CONTEXT.md ✓` before anything else. Then read `tasks.md`, find the first unchecked `- [ ]`, and do **only** that task. Read that task's full spec in
`stories.md` (same task id) before writing any code. One task per session. Complete it fully. Stop.

## Why this story exists

Same class of gap as `adoption-metrics-report`: `shaka_errors/` is real, working, currently un-ported code providing a simpler per-day Shaka (video-player) error-count report.
It is deliberately sequenced after `adoption-metrics-report` in this epic because it is structurally simpler (single metric, per-day granularity, no month-chunking) and can reuse
that story's report-store/month-chunking scaffolding rather than re-deriving its own — this story should be materially smaller than `adoption-metrics-report` as a result.

## Scope guard

- In bounds: port `shaka_errors/`'s modules into `src/athena_runner/shaka_errors/`, expose a `run_shaka_errors_report(project, start_date, end_date)` MCP tool.
- Out of bounds: does not generalize `shaka_errors` and `adoption` into one unified "report" abstraction — if `adoption-metrics-report`'s scaffolding turns out reusable as-is,
  reuse it directly; do not refactor `adoption`'s code to accommodate this story unless it's a trivial, clearly-justified extraction (note any such extraction explicitly in the
  commit message).
- Depends on `adoption-metrics-report` landing first (shares report-store/chunking scaffolding).
- Changes runtime behavior: yes, adds 1 new MCP tool.

## Session-start load hints

- `aws-access-cli/scripts/athena_runner/shaka_errors/` (read-only reference) — the subsystem to port.
- `src/athena_runner/adoption/` (once `adoption-metrics-report` lands) — the scaffolding this story should reuse (report-store, date-range handling) rather than duplicate.

## Task overview

- **SHAKA-1** — Inventory the real `shaka_errors/` module list and confirm what, if anything, it shares structurally with `adoption/`'s already-ported scaffolding.
- **SHAKA-2** — Add `run_shaka_errors_report` MCP tool wrapping the ported module(s).
- **SHAKA-3** — Document the tool in `docs/mcp-server-setup.md`.

## Definition of done

`run_shaka_errors_report(project="mtn", start_date=..., end_date=...)` produces the same per-day error-count shape the standalone script produces today, verified by a
mocked-boto3 test.

## Perspectives not covered

This story does not add alerting/threshold logic on top of the error counts — it only exposes the existing report generation as a tool, matching current script behavior.
