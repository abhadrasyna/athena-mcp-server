#!/usr/bin/env python3
"""CLI to export `SHOW CREATE TABLE` DDL for every table in an Athena
database as a single CSV (table_name, ddl).

Built so a database's full schema can be captured once, locally, instead
of re-querying Athena (or the athena-mcp-server MCP tool) once per table
whenever a table's structure needs to be checked. Reuses this project's
shared `athena_runner` execution stack rather than talking to boto3
directly. Project-agnostic: usable for any registered project's Athena
database, so every AWS-facing flag must be supplied explicitly -- no
project's SSO profile/output-bucket/region is hardcoded as a default.

Tables are processed in `--batch-size`-sized chunks (default 10),
re-checking/refreshing SSO credentials before each batch after the
first, and flushing the output CSV to disk after each batch. This means
an interruption partway through a large export (e.g. an SSO token
expiring mid-run) loses at most one in-flight batch's DDL, not the
whole run's.

Usage:
  # Discover every table in the database via `SHOW TABLES`, export all:
  python3 run_table_ddl_export.py --database default \
      --profile astro-insights-product --workgroup primary \
      --output-location s3://aws-athena-query-results-.../ \
      --region ap-southeast-1 \
      --output ../output/astro_default_table_ddl.csv

  # Export only the tables listed in discover_athena_tables.py's output:
  python3 run_table_ddl_export.py --database default \
      --tables-csv ../output/astro_default_tables.csv \
      --profile astro-insights-product --workgroup primary \
      --output-location s3://aws-athena-query-results-.../ \
      --region ap-southeast-1

  # Export only specific tables:
  python3 run_table_ddl_export.py --database unified_e6auj7k7 \
      --tables unified_sessions,e6auj7k7_ccl_debug_events \
      --profile clarissa-insights-product --workgroup primary \
      --output-location s3://clarissaprod-apps-athena-query-results/ \
      --region eu-central-1

  # Preview which tables would be exported without touching Athena:
  python3 run_table_ddl_export.py --database unified_e6auj7k7 \
      --tables unified_sessions --profile clarissa-insights-product \
      --workgroup primary \
      --output-location s3://clarissaprod-apps-athena-query-results/ \
      --dry-run
"""

import argparse
import csv
import dataclasses
import logging
import os
import sys
from collections.abc import Iterator, Sequence

import athena_cli_common

from athena_runner import config as config_lib
from athena_runner import (
  exceptions,
  logging_setup,
  query_executor,
  result_downloader,
)

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_OUTPUT_DIR = os.path.join(_SCRIPT_DIR, "..", "output")
_DEFAULT_LOG_DIR = os.path.join(_SCRIPT_DIR, "..", "logs")
_DEFAULT_BATCH_SIZE = 10

_logger = logging.getLogger("athena_runner.run_table_ddl_export")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
  """Parses command-line arguments for the table-DDL exporter."""
  parser = argparse.ArgumentParser(
      description=__doc__,
      formatter_class=argparse.RawDescriptionHelpFormatter)
  parser.add_argument(
      "--database", required=True,
      help="Athena database/catalog to export DDL from, e.g. "
           "'unified_e6auj7k7'")
  tables_group = parser.add_mutually_exclusive_group()
  tables_group.add_argument(
      "--tables", default=None,
      help="Comma-separated table names to export; if omitted (and "
           "--tables-csv is also omitted), every table in --database is "
           "discovered via 'SHOW TABLES' and exported")
  tables_group.add_argument(
      "--tables-csv", default=None,
      help="Path to a one-column 'table_name' CSV (as written by "
           "discover_athena_tables.py) listing the tables to export")
  parser.add_argument(
      "--batch-size", type=int, default=_DEFAULT_BATCH_SIZE,
      help="Number of tables to fetch DDL for per batch, re-checking SSO "
           f"and flushing the CSV between batches (default: "
           f"{_DEFAULT_BATCH_SIZE})")
  parser.add_argument(
      "--output", default=None,
      help="CSV path to write (table_name, ddl); defaults to "
           "<output-dir>/<database>_table_ddl.csv")
  parser.add_argument(
      "--profile", required=True, help="AWS SSO profile to run queries as")
  parser.add_argument(
      "--workgroup", required=True, help="Athena workgroup to run under")
  parser.add_argument(
      "--output-location", required=True,
      help="S3 URI for Athena's raw query results")
  parser.add_argument(
      "--output-dir", default=_DEFAULT_OUTPUT_DIR,
      help=f"Local directory for the CSV when --output is omitted "
           f"(default: {_DEFAULT_OUTPUT_DIR})")
  parser.add_argument(
      "--log-dir", default=_DEFAULT_LOG_DIR,
      help="Directory for the rotating DEBUG log file "
           f"(default: {_DEFAULT_LOG_DIR})")
  parser.add_argument(
      "--region", default=None,
      help="AWS region override; defaults to the profile's own region")
  parser.add_argument(
      "--poll-interval", type=int, default=2,
      help="Seconds between status polls (default: 2)")
  parser.add_argument(
      "--timeout", type=int, default=300,
      help="Max seconds to wait for each query's completion (default: 300)")
  parser.add_argument(
      "--dry-run", action="store_true",
      help="List the tables that would be exported and exit, without "
           "touching Athena")
  parser.add_argument(
      "--skip-auth-check", action="store_true",
      help="Skip the pre-flight SSO credential check/auto-refresh")
  return parser.parse_args(argv)


def _read_tables_csv(csv_path: str) -> list[str]:
  """Reads a one-column `table_name` CSV, as written by
  `discover_athena_tables.py`.
  """
  with open(csv_path, newline="", encoding="utf-8") as handle:
    reader = csv.DictReader(handle)
    if reader.fieldnames is None or "table_name" not in reader.fieldnames:
      raise ValueError(
          f"{csv_path} must have a 'table_name' column, got "
          f"{reader.fieldnames}")
    return [row["table_name"] for row in reader if row["table_name"].strip()]


def discover_tables(
    executor: query_executor.AthenaQueryExecutor,
    downloader: result_downloader.ResultDownloader,
    database: str) -> list[str]:
  """Returns every table name in `database` via `SHOW TABLES`."""
  lines = athena_cli_common.run_and_read_lines(
      executor, downloader, f"SHOW TABLES IN {database}", database)
  return [line.strip() for line in lines if line.strip()]


def fetch_table_ddl(
    executor: query_executor.AthenaQueryExecutor,
    downloader: result_downloader.ResultDownloader,
    database: str, table: str) -> str:
  """Returns the full `SHOW CREATE TABLE` DDL text for `database.table`."""
  lines = athena_cli_common.run_and_read_lines(
      executor, downloader, f"SHOW CREATE TABLE {database}.{table}", database)
  return "\n".join(lines)


def _chunked(items: Sequence[str], batch_size: int) -> Iterator[list[str]]:
  """Yields `items` split into consecutive lists of at most `batch_size`."""
  for start in range(0, len(items), batch_size):
    yield list(items[start:start + batch_size])


@dataclasses.dataclass(frozen=True)
class ExportContext:
  """Bundles the AWS-facing dependencies shared across every batch of one
  `export_table_ddl` call, so that function's own signature stays within
  a sane number of parameters.

  Attributes:
    executor: Runs each table's `SHOW CREATE TABLE` query.
    downloader: Downloads each query's result to read as DDL text.
    run_config: Supplies the profile/region for inter-batch SSO checks.
    database: Athena database the tables belong to.
  """
  executor: query_executor.AthenaQueryExecutor
  downloader: result_downloader.ResultDownloader
  run_config: config_lib.RunConfig
  database: str


def export_table_ddl(
    context: ExportContext, tables: list[str], output_path: str,
    batch_size: int, skip_auth_check: bool) -> None:
  """Fetches DDL for every entry in `tables` and writes it to `output_path`.

  Tables are processed in `batch_size`-sized batches: the output CSV is
  flushed to disk after each batch (so an interruption loses at most one
  in-flight batch, not the whole run), and -- unless `skip_auth_check` --
  SSO credentials are re-checked/refreshed before every batch after the
  first, since a long export can outlive a single SSO token's lifetime.

  Failures on individual tables are logged and recorded as an `ERROR:`
  placeholder DDL rather than aborting the whole export -- one
  unreadable/permission-denied table (e.g. a stale view) shouldn't lose
  every other table's already-fetched DDL.

  Raises:
    exceptions.SsoLoginError: If an inter-batch SSO refresh fails; the
      CSV still contains every batch successfully flushed before that
      point.
  """
  os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
  with open(output_path, "w", newline="", encoding="utf-8") as handle:
    writer = csv.writer(handle)
    writer.writerow(["table_name", "ddl"])
    handle.flush()
    processed = 0
    for batch_index, batch in enumerate(_chunked(tables, batch_size)):
      if batch_index > 0 and not skip_auth_check:
        _reauth_or_raise(context.run_config, processed, len(tables),
                          output_path)
      processed = _export_batch(context, batch, writer, processed,
                                 len(tables))
      handle.flush()


def _reauth_or_raise(
    run_config: config_lib.RunConfig, processed: int, total: int,
    output_path: str) -> None:
  """Re-checks/refreshes SSO before a batch; raises if that fails."""
  if not athena_cli_common.ensure_sso_or_log_failure(run_config, _logger):
    raise exceptions.SsoLoginError(
        "SSO credential refresh failed between batches -- "
        f"{processed}/{total} table(s) already saved to {output_path}")


def _export_batch(
    context: ExportContext, batch: list[str], writer, processed: int,
    total: int) -> int:
  """Fetches DDL for one batch of tables, writing each row as it goes.

  Returns:
    The running count of tables processed so far (across all batches).
  """
  for table in batch:
    processed += 1
    _logger.info(
        "[%d/%d] Fetching DDL for %s.%s", processed, total, context.database,
        table)
    try:
      ddl = fetch_table_ddl(
          context.executor, context.downloader, context.database, table)
    except (exceptions.QueryExecutionError,
            exceptions.QueryTimeoutError) as exc:
      _logger.error("Failed to fetch DDL for %s: %s", table, exc)
      ddl = f"ERROR: {exc}"
    writer.writerow([table, ddl])
  return processed


def main(argv: list[str] | None = None) -> int:
  """Exports every requested table's DDL as a CSV.

  Args:
    argv: Command-line arguments; defaults to sys.argv[1:] via argparse.

  Returns:
    Process exit code: 0 on success, 1 on error.
  """
  args = _parse_args(argv)
  logging_setup.configure_logging(args.log_dir, "run_table_ddl_export")

  run_config = config_lib.RunConfig(
      profile=args.profile,
      workgroup=args.workgroup,
      output_location=args.output_location,
      output_dir=args.output_dir,
      region=args.region,
      poll_interval_seconds=args.poll_interval,
      timeout_seconds=args.timeout,
  )

  if args.tables_csv:
    requested_tables = _read_tables_csv(args.tables_csv)
  elif args.tables:
    requested_tables = [
        name.strip() for name in args.tables.split(",") if name.strip()]
  else:
    requested_tables = None

  if args.dry_run and requested_tables is not None:
    for table in requested_tables:
      print(table)
    return 0

  if not args.skip_auth_check and not (
      athena_cli_common.ensure_sso_or_log_failure(run_config, _logger)):
    return 1

  executor, downloader = athena_cli_common.build_executor(run_config)

  tables = requested_tables
  if tables is None:
    tables = discover_tables(executor, downloader, args.database)
    _logger.info("Discovered %d tables in %s", len(tables), args.database)

  if args.dry_run:
    for table in tables:
      print(table)
    return 0

  output_path = args.output or os.path.join(
      args.output_dir, f"{args.database}_table_ddl.csv")
  context = ExportContext(
      executor=executor, downloader=downloader, run_config=run_config,
      database=args.database)
  try:
    export_table_ddl(
        context, tables, output_path, args.batch_size, args.skip_auth_check)
  except exceptions.SsoLoginError as exc:
    _logger.exception("Export aborted: %s", exc)
    return 1
  _logger.info("Wrote %d table(s) DDL to %s", len(tables), output_path)
  return 0


if __name__ == "__main__":
  sys.exit(main())
