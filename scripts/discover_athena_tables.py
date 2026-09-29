#!/usr/bin/env python3
"""CLI to discover every table in an Athena database via `SHOW TABLES`.

Project-agnostic infra usable by any registered project (MTN, Astro,
future ones) via this repo's shared `athena_runner` execution
stack -- unlike its `aws-access-cli` predecessor, no project's SSO
profile/output-bucket/region is hardcoded as a default; every AWS-facing
flag must be supplied explicitly (see Usage).

Writes a one-column `table_name` CSV -- the input for a knowledge doc's
table-inventory/categorization section, and for
`run_table_ddl_export.py --tables-csv`'s batch DDL export.

Usage:
  python3 discover_athena_tables.py \
      --database default --profile astro-insights-product \
      --workgroup primary \
      --output-location s3://aws-athena-query-results-.../ \
      --region ap-southeast-1 \
      --output ../output/astro_default_tables.csv
"""

import argparse
import csv
import logging
import os
import sys

import athena_cli_common

from athena_runner import config as config_lib
from athena_runner import logging_setup, query_executor, result_downloader

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_OUTPUT_DIR = os.path.join(_SCRIPT_DIR, "..", "output")
_DEFAULT_LOG_DIR = os.path.join(_SCRIPT_DIR, "..", "logs")
_DEFAULT_POLL_INTERVAL_SECONDS = 2
_DEFAULT_TIMEOUT_SECONDS = 300

_logger = logging.getLogger("athena_runner.discover_athena_tables")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
  """Parses command-line arguments for the table-discovery CLI."""
  parser = argparse.ArgumentParser(
      description=__doc__,
      formatter_class=argparse.RawDescriptionHelpFormatter)
  parser.add_argument(
      "--database", required=True,
      help="Athena database/catalog to discover tables in, e.g. 'default'")
  parser.add_argument(
      "--profile", required=True, help="AWS SSO profile to run the query as")
  parser.add_argument(
      "--workgroup", required=True, help="Athena workgroup to run under")
  parser.add_argument(
      "--output-location", required=True,
      help="S3 URI for Athena's raw query results")
  parser.add_argument(
      "--region", default=None,
      help="AWS region override; defaults to the profile's own region")
  parser.add_argument(
      "--output-dir", default=_DEFAULT_OUTPUT_DIR,
      help=f"Local directory for the CSV when --output is omitted "
           f"(default: {_DEFAULT_OUTPUT_DIR})")
  parser.add_argument(
      "--log-dir", default=_DEFAULT_LOG_DIR,
      help=f"Directory for the rotating DEBUG log file "
           f"(default: {_DEFAULT_LOG_DIR})")
  parser.add_argument(
      "--output", default=None,
      help="CSV path to write (table_name); defaults to "
           "<output-dir>/<database>_tables.csv")
  parser.add_argument(
      "--skip-auth-check", action="store_true",
      help="Skip the pre-flight SSO credential check/auto-refresh")
  return parser.parse_args(argv)


def discover_tables(
    executor: query_executor.AthenaQueryExecutor,
    downloader: result_downloader.ResultDownloader,
    database: str) -> list[str]:
  """Returns every table name in `database` via `SHOW TABLES`."""
  lines = athena_cli_common.run_and_read_lines(
      executor, downloader, f"SHOW TABLES IN {database}", database)
  return [line.strip() for line in lines if line.strip()]


def write_tables_csv(tables: list[str], output_path: str) -> None:
  """Writes `tables` as a one-column (`table_name`) CSV to `output_path`."""
  os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
  with open(output_path, "w", newline="", encoding="utf-8") as handle:
    writer = csv.writer(handle)
    writer.writerow(["table_name"])
    for table in tables:
      writer.writerow([table])


def main(argv: list[str] | None = None) -> int:
  """Discovers every table in `--database` and writes it to a CSV.

  Args:
    argv: Command-line arguments; defaults to sys.argv[1:] via argparse.

  Returns:
    Process exit code: 0 on success, 1 on error.
  """
  args = _parse_args(argv)
  logging_setup.configure_logging(args.log_dir, "discover_athena_tables")

  run_config = config_lib.RunConfig(
      profile=args.profile,
      workgroup=args.workgroup,
      output_location=args.output_location,
      output_dir=args.output_dir,
      region=args.region,
      poll_interval_seconds=_DEFAULT_POLL_INTERVAL_SECONDS,
      timeout_seconds=_DEFAULT_TIMEOUT_SECONDS,
  )

  if not args.skip_auth_check and not (
      athena_cli_common.ensure_sso_or_log_failure(run_config, _logger)):
    return 1

  executor, downloader = athena_cli_common.build_executor(run_config)
  tables = discover_tables(executor, downloader, args.database)
  _logger.info("Discovered %d table(s) in %s", len(tables), args.database)

  output_path = args.output or os.path.join(
      args.output_dir, f"{args.database}_tables.csv")
  write_tables_csv(tables, output_path)
  _logger.info("Wrote %d table name(s) to %s", len(tables), output_path)
  return 0


if __name__ == "__main__":
  sys.exit(main())
