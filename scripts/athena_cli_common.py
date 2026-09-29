"""Shared boto3-wiring + line-reading helpers for this repo's standalone
Athena CLI scripts (`discover_athena_tables.py`, `run_table_ddl_export.py`).

Kept separate from either script (SRP/DRY) so neither reimplements how to
build an executor/downloader pair, how to read Athena's plain-text
(`SHOW TABLES`/`SHOW CREATE TABLE`) query results as lines, or the
standard SSO pre-flight check.
"""

import logging
import os
import tempfile
from typing import List, Tuple

from athena_runner import aws_clients
from athena_runner import cli_common
from athena_runner import config as config_lib
from athena_runner import exceptions
from athena_runner import query_executor
from athena_runner import result_downloader


def build_executor(run_config: config_lib.RunConfig) -> Tuple[
    query_executor.AthenaQueryExecutor, result_downloader.ResultDownloader]:
  """Builds the Athena executor/downloader pair for `run_config`."""
  clients = aws_clients.AwsClientFactory(run_config.profile, run_config.region)
  executor = query_executor.BotoAthenaQueryExecutor(
      clients.athena_client(), run_config)
  downloader = result_downloader.S3ResultDownloader(clients.s3_client())
  return executor, downloader


def run_and_read_lines(
    executor: query_executor.AthenaQueryExecutor,
    downloader: result_downloader.ResultDownloader,
    sql: str, database: str) -> List[str]:
  """Runs `sql`, downloads its result, and returns it as a list of lines.

  Athena's `SHOW TABLES` / `SHOW CREATE TABLE` results are plain text
  (one value per line), unlike a `SELECT`'s comma-separated CSV --
  reading raw lines (rather than parsing as CSV) is what both callers of
  this helper need.
  """
  result = executor.run(sql, database)
  with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp_file:
    tmp_path = tmp_file.name
  try:
    downloader.download(result.output_location, tmp_path)
    with open(tmp_path, "r", encoding="utf-8") as handle:
      return [line.rstrip("\n") for line in handle]
  finally:
    os.remove(tmp_path)


def ensure_sso_or_log_failure(
    run_config: config_lib.RunConfig, logger: logging.Logger) -> bool:
  """Runs the standard SSO pre-flight check, logging via `logger`.

  Args:
    run_config: Supplies the profile/region to check.
    logger: Logger the check/refresh outcome is reported through.

  Returns:
    True if it's safe to proceed (credentials were already valid, or a
    refresh via `aws-sso` just succeeded); False if the refresh failed
    and the caller should abort rather than run queries with stale
    credentials.
  """
  try:
    was_already_valid = cli_common.ensure_valid_sso_credentials(run_config)
  except exceptions.SsoLoginError as exc:
    logger.exception("SSO credential check/refresh failed: %s", exc)
    return False
  if not was_already_valid:
    logger.info(
        "Refreshed SSO credentials for profile '%s' via aws-sso.",
        run_config.profile)
  return True
