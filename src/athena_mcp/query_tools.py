"""Thin adapters wrapping `athena_runner`'s executor/downloader/cli_common.

No boto3 client construction or argparse here directly -- this module
composes `athena_runner.aws_clients.AwsClientFactory`,
`athena_runner.query_executor.BotoAthenaQueryExecutor`,
`athena_runner.result_downloader.S3ResultDownloader`, and
`athena_runner.cli_common.ensure_valid_sso_credentials` into the shapes
`athena_mcp.server`'s MCP tools need (see `MCP-3`), and stays unit-
testable with a fake `AwsClientFactory` (no live AWS/MCP transport).

Adoption metrics scope (resolves `story.md`'s open decision "whether
adoption metrics get their own tool pair, or fold into the same
'registered query' tools"): **not folded in here.** `AdoptionMetric`
(`aws-access-cli/scripts/athena_runner/adoption/metric.py`) has a
materially different contract from `AthenaQuery`
(`build_sql(start_date, end_date)` over a date *range*, one metric
contributing one column, orchestrated across month chunks in parallel
by `adoption/metric_runner.py` and merged by `adoption/report_store.py`)
-- it isn't a single "run one query, download one CSV" operation the
way `run_registered_athena_query` models it. Multiplexing both shapes
behind one tool would blur that difference for callers (what does
`params` mean for a metric that takes a date range and produces a
multi-day merged report, not query-specific params?). Adoption metrics
get their own dedicated tool pair in a future task, scoped and
implemented against their own contract, instead of being force-fit into
`AthenaQuery`'s shape here.
"""

import dataclasses
import os
from typing import Any, Dict, List, Mapping, Optional

from athena_runner import aws_clients
from athena_runner import cli_common
from athena_runner import config as config_lib
from athena_runner import query_executor
from athena_runner import result_downloader

from athena_mcp import result_preview
from athena_mcp import tool_config

_PREVIEW_MAX_ROWS = 20

# Fields on ProjectConfig.run_config a caller may override per tool call
# (see story.md's "MCP tools exposed" section).
_OVERRIDABLE_RUN_CONFIG_FIELDS = frozenset({
    "profile", "workgroup", "output_location", "region", "timeout_seconds",
})


@dataclasses.dataclass(frozen=True)
class RegisteredQueryDescriptor:
  """One entry in `list_athena_queries`'s result.

  Attributes:
    name: The query's registered, CLI-facing name.
    database: The Athena database/catalog it runs against.
    description: First line of the query class's docstring, if any.
  """
  name: str
  database: str
  description: str


@dataclasses.dataclass(frozen=True)
class QueryRunResult:
  """Outcome of a single `run_registered_athena_query`/`run_athena_sql` call.

  Attributes:
    query_execution_id: Athena's identifier for the query run.
    output_location: S3 URI Athena wrote the raw result to.
    data_scanned_bytes: Bytes scanned, for cost/perf visibility.
    engine_execution_ms: Query engine execution time in milliseconds.
    csv_path: Local path the result CSV was downloaded to.
    preview: Inline preview of the CSV's first rows.
  """
  query_execution_id: str
  output_location: str
  data_scanned_bytes: int
  engine_execution_ms: int
  csv_path: str
  preview: result_preview.ResultPreview


def _effective_run_config(
    project_config: tool_config.ProjectConfig,
    overrides: Optional[Mapping[str, Any]]) -> config_lib.RunConfig:
  """Applies caller `overrides` on top of `project_config.run_config`.

  Args:
    project_config: The resolved project configuration.
    overrides: Optional per-call overrides; unknown keys are rejected so
      typos fail loudly instead of being silently ignored.

  Raises:
    ValueError: If `overrides` contains a key that isn't a valid
      per-call override field.
  """
  if not overrides:
    return project_config.run_config
  unknown = set(overrides) - _OVERRIDABLE_RUN_CONFIG_FIELDS
  if unknown:
    raise ValueError(
        f"Unsupported override(s): {sorted(unknown)}. Supported: "
        f"{sorted(_OVERRIDABLE_RUN_CONFIG_FIELDS)}.")
  return dataclasses.replace(project_config.run_config, **overrides)


def _ensure_sso(run_config: config_lib.RunConfig) -> None:
  """Pre-flight SSO check, invoked before every execute call.

  Raises:
    exceptions.SsoLoginError: If credentials are invalid and can't be
      refreshed (see `athena_runner.cli_common`).
  """
  cli_common.ensure_valid_sso_credentials(run_config)


def _execute_and_download(
    run_config: config_lib.RunConfig, sql: str, database: str,
    output_filename: Optional[str] = None) -> QueryRunResult:
  """Runs `sql`, downloads its result, and builds a `QueryRunResult`.

  Args:
    run_config: Workgroup/output-location/timeout settings for this run.
    sql: The Athena SQL statement to execute.
    database: The Athena database/catalog to run `sql` against.
    output_filename: Local CSV filename to save the result as. If
      omitted (ad-hoc queries have no natural filename of their own),
      defaults to a name derived from Athena's own
      `query_execution_id`, which is already unique per run.
  """
  client_factory = aws_clients.AwsClientFactory(
      run_config.profile, run_config.region)
  executor = query_executor.BotoAthenaQueryExecutor(
      client_factory.athena_client(), run_config)
  downloader = result_downloader.S3ResultDownloader(
      client_factory.s3_client())

  result = executor.run(sql, database)
  filename = output_filename or f"athena_ad_hoc_{result.query_execution_id}.csv"
  csv_path = os.path.join(run_config.output_dir, filename)
  downloader.download(result.output_location, csv_path)
  preview = result_preview.read_preview(csv_path, _PREVIEW_MAX_ROWS)

  return QueryRunResult(
      query_execution_id=result.query_execution_id,
      output_location=result.output_location,
      data_scanned_bytes=result.data_scanned_bytes,
      engine_execution_ms=result.engine_execution_ms,
      csv_path=csv_path,
      preview=preview,
  )


def refresh_athena_sso(
    project: str, overrides: Optional[Mapping[str, Any]] = None) -> bool:
  """Pre-warms AWS SSO credentials for `project`'s profile.

  Args:
    project: Registered project name, e.g. 'mtn'.
    overrides: Optional `profile`/`region` override.

  Returns:
    True if credentials were already valid; False if a refresh was
    required (and succeeded).
  """
  project_config = tool_config.get_project_config(project)
  run_config = _effective_run_config(project_config, overrides)
  return cli_common.ensure_valid_sso_credentials(run_config)


def list_athena_queries(project: str) -> List[RegisteredQueryDescriptor]:
  """Lists `project`'s registered queries.

  Args:
    project: Registered project name, e.g. 'mtn'.

  Raises:
    ValueError: If `project` isn't registered at all.
    NotImplementedError: If `project` is registered but not fully
      configured yet (see `tool_config.get_project_config`).
    NotImplementedError: If `project` has no registered-query registry
      (ad-hoc SQL via `run_athena_sql` may still work for it).
  """
  project_config = tool_config.get_project_config(project)
  if project_config.registry_loader is None:
    raise NotImplementedError(
        f"Project '{project}' has no registered-query registry -- only "
        "run_athena_sql (ad-hoc) is available for it.")
  registry = project_config.registry_loader()
  descriptors = []
  for name in registry.names():
    query = registry.get(name)
    docstring = (type(query).__doc__ or "").strip()
    description = docstring.splitlines()[0] if docstring else ""
    descriptors.append(RegisteredQueryDescriptor(
        name=query.name, database=query.database, description=description))
  return descriptors


def run_registered_athena_query(
    project: str, name: str, params: Dict[str, str],
    overrides: Optional[Mapping[str, Any]] = None) -> QueryRunResult:
  """Runs `project`'s registered query `name` with `params`.

  Args:
    project: Registered project name, e.g. 'mtn'.
    name: The registered query's name, e.g. 'playback-outcome'.
    params: Query-specific parameters, e.g. {'date': '2026-07-08'}.
    overrides: Optional per-call `RunConfig` field overrides.

  Raises:
    ValueError: If `project` isn't registered, an override key is
      invalid, or a required query param is missing/invalid.
    NotImplementedError: If `project` is registered but not fully
      configured, or has no registered-query registry.
    KeyError: If `name` isn't registered for `project`.
  """
  project_config = tool_config.get_project_config(project)
  if project_config.registry_loader is None:
    raise NotImplementedError(
        f"Project '{project}' has no registered-query registry -- only "
        "run_athena_sql (ad-hoc) is available for it.")
  registry = project_config.registry_loader()
  query = registry.get(name)

  run_config = _effective_run_config(project_config, overrides)
  _ensure_sso(run_config)

  sql = query.build_sql(params)
  output_filename = query.output_filename(params)
  return _execute_and_download(
      run_config, sql, query.database, output_filename)


def run_athena_sql(
    project: str, sql: str, database: Optional[str] = None,
    overrides: Optional[Mapping[str, Any]] = None) -> QueryRunResult:
  """Runs ad-hoc `sql` for `project`, with no mutation or filtering.

  Args:
    project: Registered project name, e.g. 'mtn'.
    sql: The Athena SQL statement to execute, passed through verbatim.
    database: Athena database/catalog; defaults to `project`'s
      configured database if omitted.
    overrides: Optional per-call `RunConfig` field overrides.

  Raises:
    ValueError: If `project` isn't registered or an override key is
      invalid.
    NotImplementedError: If `project` is registered but not fully
      configured yet.
  """
  project_config = tool_config.get_project_config(project)
  run_config = _effective_run_config(project_config, overrides)
  _ensure_sso(run_config)

  effective_database = database or project_config.database
  return _execute_and_download(run_config, sql, effective_database)
