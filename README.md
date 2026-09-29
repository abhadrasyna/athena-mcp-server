# athena-mcp-server

An MCP server exposing Athena querying (registered per-project reports + ad-hoc SQL) as tools for any MCP-capable agent (Copilot CLI, etc.), backed by a shared, project-agnostic Athena execution stack
(AWS SSO auto-refresh, query executor, result downloader) — the one shared dependency multiple investigation/reporting projects (`aws-access-cli`, `astro-events-household-report`, future
`applauseInvestigation`) draw from instead of each reimplementing their own boto3/Athena boilerplate.

## Status

Active. Ported from `github_copilot/oasis-athena-mcp` (a staged "plain folder" prototype) into its own independent repo — see `CONTEXT.md` for what's carried over and what's still open.

## Setup

```bash
make venv   # creates .venv, installs dev deps, editable-installs this package
make test   # runs the pytest suite
make lint   # runs pylint over src/ and scripts/
make run-server   # starts the MCP stdio server (see docs/mcp-server-setup.md for registration)
```
