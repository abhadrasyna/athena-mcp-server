"""Tests for scripts/discover_athena_tables.py."""

import csv

import discover_athena_tables

from athena_runner import query_executor
from athena_runner import result_downloader


class _FakeExecutor(query_executor.AthenaQueryExecutor):
  """Fake executor recording calls and returning a fixed output location."""

  def __init__(self):
    self.calls = []

  def run(self, sql, database):
    self.calls.append((sql, database))
    return query_executor.QueryResult(
        query_execution_id="q-1", output_location="s3://bucket/tables.txt",
        data_scanned_bytes=0, engine_execution_ms=0)


class _FakeDownloader(result_downloader.ResultDownloader):
  """Fake downloader that writes a fixed table listing."""

  def __init__(self, content):
    self._content = content

  def download(self, output_location, destination_path):
    with open(destination_path, "w", encoding="utf-8") as handle:
      handle.write(self._content)


def test_discover_tables_returns_stripped_nonempty_lines():
  executor = _FakeExecutor()
  downloader = _FakeDownloader("table_one\n\ntable_two \n")

  tables = discover_athena_tables.discover_tables(
      executor, downloader, "my_db")

  assert tables == ["table_one", "table_two"]
  assert executor.calls == [("SHOW TABLES IN my_db", "my_db")]


def test_write_tables_csv_creates_parent_dirs_and_header(tmp_path):
  output_path = tmp_path / "nested" / "tables.csv"

  discover_athena_tables.write_tables_csv(
      ["table_one", "table_two"], str(output_path))

  with open(output_path, newline="", encoding="utf-8") as handle:
    rows = list(csv.reader(handle))
  assert rows == [["table_name"], ["table_one"], ["table_two"]]


def test_main_end_to_end_writes_csv(monkeypatch, tmp_path):
  monkeypatch.setattr(
      discover_athena_tables.athena_cli_common, "build_executor",
      lambda run_config: (_FakeExecutor(), _FakeDownloader("table_one\n")))
  monkeypatch.setattr(
      discover_athena_tables.athena_cli_common, "ensure_sso_or_log_failure",
      lambda run_config, logger: True)

  output_path = tmp_path / "out.csv"
  exit_code = discover_athena_tables.main([
      "--database", "my_db", "--profile", "p", "--workgroup", "primary",
      "--output-location", "s3://bucket/", "--output", str(output_path),
      "--log-dir", str(tmp_path)])

  assert exit_code == 0
  with open(output_path, newline="", encoding="utf-8") as handle:
    rows = list(csv.reader(handle))
  assert rows == [["table_name"], ["table_one"]]


def test_main_returns_one_when_sso_check_fails(monkeypatch, tmp_path):
  monkeypatch.setattr(
      discover_athena_tables.athena_cli_common, "ensure_sso_or_log_failure",
      lambda run_config, logger: False)

  exit_code = discover_athena_tables.main([
      "--database", "my_db", "--profile", "p", "--workgroup", "primary",
      "--output-location", "s3://bucket/", "--log-dir", str(tmp_path)])

  assert exit_code == 1


def test_main_skips_auth_check_when_flag_set(monkeypatch, tmp_path):
  ensure_sso_calls = []
  monkeypatch.setattr(
      discover_athena_tables.athena_cli_common, "ensure_sso_or_log_failure",
      lambda run_config, logger: ensure_sso_calls.append(1) or True)
  monkeypatch.setattr(
      discover_athena_tables.athena_cli_common, "build_executor",
      lambda run_config: (_FakeExecutor(), _FakeDownloader("table_one\n")))

  output_path = tmp_path / "out.csv"
  exit_code = discover_athena_tables.main([
      "--database", "my_db", "--profile", "p", "--workgroup", "primary",
      "--output-location", "s3://bucket/", "--output", str(output_path),
      "--log-dir", str(tmp_path), "--skip-auth-check"])

  assert exit_code == 0
  assert not ensure_sso_calls


def test_main_defaults_output_path_to_database_name(monkeypatch, tmp_path):
  monkeypatch.setattr(
      discover_athena_tables.athena_cli_common, "build_executor",
      lambda run_config: (_FakeExecutor(), _FakeDownloader("table_one\n")))
  monkeypatch.setattr(
      discover_athena_tables.athena_cli_common, "ensure_sso_or_log_failure",
      lambda run_config, logger: True)

  exit_code = discover_athena_tables.main([
      "--database", "my_db", "--profile", "p", "--workgroup", "primary",
      "--output-location", "s3://bucket/", "--output-dir", str(tmp_path),
      "--log-dir", str(tmp_path)])

  assert exit_code == 0
  assert (tmp_path / "my_db_tables.csv").exists()
