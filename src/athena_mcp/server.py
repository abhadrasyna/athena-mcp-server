"""The MCP server instance and its 4 tool registrations.

See `story.md`'s "MCP tools exposed" and "Critical implementation
constraint: stdio hygiene" sections. This module only wires
`mcp.server.mcpserver.MCPServer` tools to `query_tools.py`'s pure
functions -- no boto3/argparse here, and no logging configuration
(that's `athena_mcp.cli`'s job, added in `MCP-4`, since it owns the
`--log-dir` flag).

Stdio hygiene: MCP over stdio uses stdout exclusively for JSON-RPC
frames. Every dependency this module (transitively) touches --
`athena_runner.logging_setup`'s `StreamHandler` included -- must only
ever write to stderr or a log file, never stdout. This is verified by
`tests/athena_mcp/test_server.py::test_logging_never_writes_to_stdout`
rather than assumed.
"""

import dataclasses
from typing import Any

from mcp.server.mcpserver import MCPServer

from athena_mcp import query_tools

server = MCPServer(
    name="athena-mcp-server",
    description=(
        "Exposes Athena querying (registered per-project reports + "
        "ad-hoc SQL) as MCP tools, backed by a shared, project-agnostic "
        "execution stack (AWS SSO auto-refresh, query executor, result "
        "downloader). See docs/mcp-server-setup.md."
    ),
)


@server.tool()
def list_athena_queries(project: str) -> list[dict[str, str]]:
  """Lists `project`'s registered Athena queries.

  Args:
    project: Registered project name, e.g. 'mtn'.

  Returns:
    One dict per registered query, each with `name`, `database`, and
    `description` keys.
  """
  descriptors = query_tools.list_athena_queries(project)
  return [dataclasses.asdict(descriptor) for descriptor in descriptors]


@server.tool()
def run_registered_athena_query(
    project: str,
    name: str,
    params: dict[str, str],
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
  """Runs `project`'s registered query `name` with `params`.

  Args:
    project: Registered project name, e.g. 'mtn'.
    name: The registered query's name, e.g. 'playback-outcome'.
    params: Query-specific parameters, e.g. {'date': '2026-07-08'}.
    overrides: Optional per-call `RunConfig` field overrides (`profile`,
      `workgroup`, `output_location`, `region`, `timeout_seconds`).

  Returns:
    A dict with `query_execution_id`, `output_location`,
    `data_scanned_bytes`, `engine_execution_ms`, `csv_path`, and
    `preview` (itself a dict with `columns`/`rows`/
    `total_rows_previewed`/`truncated`).
  """
  result = query_tools.run_registered_athena_query(
      project, name, params, overrides)
  return dataclasses.asdict(result)


@server.tool()
def run_athena_sql(
    project: str,
    sql: str,
    database: str | None = None,
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
  """Runs ad-hoc `sql` for `project`, with no mutation or filtering.

  Args:
    project: Registered project name, e.g. 'mtn'.
    sql: The Athena SQL statement to execute, passed through verbatim.
    database: Athena database/catalog; defaults to `project`'s
      configured database if omitted.
    overrides: Optional per-call `RunConfig` field overrides (`profile`,
      `workgroup`, `output_location`, `region`, `timeout_seconds`).

  Returns:
    Same shape as `run_registered_athena_query`'s return value.
  """
  result = query_tools.run_athena_sql(project, sql, database, overrides)
  return dataclasses.asdict(result)


@server.tool()
def refresh_athena_sso(
    project: str, overrides: dict[str, Any] | None = None) -> bool:
  """Pre-warms AWS SSO credentials for `project`'s profile.

  Args:
    project: Registered project name, e.g. 'mtn'.
    overrides: Optional `profile`/`region` override.

  Returns:
    True if credentials were already valid; False if a refresh was
    required (and succeeded).
  """
  return query_tools.refresh_athena_sso(project, overrides)


def run() -> None:
  """Starts `server` over stdio. Called by `athena_mcp.cli.main` (MCP-4)."""
  server.run(transport="stdio")
