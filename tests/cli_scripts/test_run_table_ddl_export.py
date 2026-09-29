"""Tests for scripts/run_table_ddl_export.py."""

import csv

import pytest
import run_table_ddl_export

from athena_runner import config as config_lib
from athena_runner import exceptions, query_executor, result_downloader


def _run_config(**overrides):
  defaults = {
      "profile": "test-profile",
      "workgroup": "primary",
      "output_location": "s3://bucket/",
      "output_dir": "/tmp/out",
  }
  defaults.update(overrides)
  return config_lib.RunConfig(**defaults)


class _FakeExecutor(query_executor.AthenaQueryExecutor):
  """Fake executor mapping each table's `SHOW CREATE TABLE` to fixed DDL.

  Any table name listed in `error_tables` raises QueryExecutionError
  instead, so callers can exercise the "one bad table doesn't lose the
  rest" behavior.
  """

  def __init__(self, ddl_by_table=None, error_tables=()):
    self._ddl_by_table = ddl_by_table or {}
    self._error_tables = set(error_tables)
    self.calls = []

  def run(self, sql, database):
    self.calls.append((sql, database))
    if "SHOW TABLES" in sql:
      return query_executor.QueryResult(
          query_execution_id="q-tables", output_location="s3://bucket/t.txt",
          data_scanned_bytes=0, engine_execution_ms=0)
    table = sql.rsplit(".", maxsplit=1)[-1]
    if table in self._error_tables:
      raise exceptions.QueryExecutionError(f"denied: {table}")
    return query_executor.QueryResult(
        query_execution_id=f"q-{table}",
        output_location=f"s3://bucket/{table}.txt",
        data_scanned_bytes=0, engine_execution_ms=0)


class _FakeDownloader(result_downloader.ResultDownloader):
  """Fake downloader serving fixed content per table, plus a table list."""

  def __init__(self, ddl_by_table=None, table_list_content=""):
    self._ddl_by_table = ddl_by_table or {}
    self._table_list_content = table_list_content
    self.download_calls = []

  def download(self, output_location, destination_path):
    self.download_calls.append(output_location)
    if output_location == "s3://bucket/t.txt":
      content = self._table_list_content
    else:
      table = output_location.rsplit("/", maxsplit=1)[-1][:-len(".txt")]
      content = self._ddl_by_table.get(table, f"CREATE TABLE {table} (...)")
    with open(destination_path, "w", encoding="utf-8") as handle:
      handle.write(content)


def _read_ddl_csv(path):
  with open(path, newline="", encoding="utf-8") as handle:
    return list(csv.DictReader(handle))


def test_read_tables_csv_returns_table_names(tmp_path):
  csv_path = tmp_path / "tables.csv"
  csv_path.write_text("table_name\ntable_one\ntable_two\n", encoding="utf-8")

  # pylint: disable-next=protected-access
  tables = run_table_ddl_export._read_tables_csv(str(csv_path))

  assert tables == ["table_one", "table_two"]


def test_read_tables_csv_raises_on_missing_column(tmp_path):
  csv_path = tmp_path / "tables.csv"
  csv_path.write_text("wrong_column\nvalue\n", encoding="utf-8")

  with pytest.raises(ValueError, match="table_name"):
    # pylint: disable-next=protected-access
    run_table_ddl_export._read_tables_csv(str(csv_path))


def test_fetch_table_ddl_joins_lines():
  executor = _FakeExecutor()
  downloader = _FakeDownloader({"my_table": "CREATE TABLE my_table (\n  x)"})

  ddl = run_table_ddl_export.fetch_table_ddl(
      executor, downloader, "my_db", "my_table")

  assert ddl == "CREATE TABLE my_table (\n  x)"


def test_export_table_ddl_records_error_placeholder_for_failing_table(
    tmp_path):
  executor = _FakeExecutor(error_tables={"bad_table"})
  downloader = _FakeDownloader()
  output_path = tmp_path / "ddl.csv"
  context = run_table_ddl_export.ExportContext(
      executor=executor, downloader=downloader, run_config=_run_config(),
      database="my_db")

  run_table_ddl_export.export_table_ddl(
      context, ["good_table", "bad_table"], str(output_path),
      batch_size=10, skip_auth_check=True)

  rows = _read_ddl_csv(output_path)
  assert rows[0]["table_name"] == "good_table"
  assert "CREATE TABLE" in rows[0]["ddl"]
  assert rows[1]["table_name"] == "bad_table"
  assert rows[1]["ddl"] == "ERROR: denied: bad_table"


def test_export_table_ddl_flushes_and_rechecks_sso_between_batches(
    monkeypatch, tmp_path):
  executor = _FakeExecutor()
  downloader = _FakeDownloader()
  output_path = tmp_path / "ddl.csv"
  context = run_table_ddl_export.ExportContext(
      executor=executor, downloader=downloader, run_config=_run_config(),
      database="my_db")
  sso_checks = []
  monkeypatch.setattr(
      run_table_ddl_export.athena_cli_common, "ensure_sso_or_log_failure",
      lambda run_config, logger: sso_checks.append(1) or True)

  run_table_ddl_export.export_table_ddl(
      context, ["t1", "t2", "t3"], str(output_path), batch_size=1,
      skip_auth_check=False)

  # First batch never re-checks (already checked before the loop by the
  # caller); batches 2 and 3 each re-check once.
  assert len(sso_checks) == 2
  assert len(_read_ddl_csv(output_path)) == 3


def test_export_table_ddl_raises_and_preserves_partial_csv_on_sso_failure(
    monkeypatch, tmp_path):
  executor = _FakeExecutor()
  downloader = _FakeDownloader()
  output_path = tmp_path / "ddl.csv"
  context = run_table_ddl_export.ExportContext(
      executor=executor, downloader=downloader, run_config=_run_config(),
      database="my_db")
  monkeypatch.setattr(
      run_table_ddl_export.athena_cli_common, "ensure_sso_or_log_failure",
      lambda run_config, logger: False)

  with pytest.raises(exceptions.SsoLoginError, match="1/2"):
    run_table_ddl_export.export_table_ddl(
        context, ["t1", "t2"], str(output_path), batch_size=1,
        skip_auth_check=False)

  rows = _read_ddl_csv(output_path)
  assert [row["table_name"] for row in rows] == ["t1"]


def test_main_rejects_tables_and_tables_csv_together(tmp_path):
  tables_csv = tmp_path / "tables.csv"
  tables_csv.write_text("table_name\nfrom_csv\n", encoding="utf-8")

  with pytest.raises(SystemExit) as exc_info:
    run_table_ddl_export.main([
        "--database", "my_db", "--tables-csv", str(tables_csv),
        "--tables", "ignored_table", "--profile", "p", "--workgroup",
        "primary", "--output-location", "s3://bucket/",
        "--log-dir", str(tmp_path)])

  assert exc_info.value.code == 2  # argparse: mutually exclusive flags.


def test_main_tables_csv_end_to_end(monkeypatch, tmp_path):
  tables_csv = tmp_path / "tables.csv"
  tables_csv.write_text("table_name\nfrom_csv\n", encoding="utf-8")
  monkeypatch.setattr(
      run_table_ddl_export.athena_cli_common, "build_executor",
      lambda run_config: (_FakeExecutor(), _FakeDownloader()))
  monkeypatch.setattr(
      run_table_ddl_export.athena_cli_common, "ensure_sso_or_log_failure",
      lambda run_config, logger: True)

  output_path = tmp_path / "ddl.csv"
  exit_code = run_table_ddl_export.main([
      "--database", "my_db", "--tables-csv", str(tables_csv),
      "--profile", "p", "--workgroup", "primary",
      "--output-location", "s3://bucket/", "--output", str(output_path),
      "--log-dir", str(tmp_path)])

  assert exit_code == 0
  rows = _read_ddl_csv(output_path)
  assert [row["table_name"] for row in rows] == ["from_csv"]


def test_main_dry_run_with_tables_prints_and_skips_athena(capsys, tmp_path):
  exit_code = run_table_ddl_export.main([
      "--database", "my_db", "--tables", "t1,t2", "--profile", "p",
      "--workgroup", "primary", "--output-location", "s3://bucket/",
      "--dry-run", "--log-dir", str(tmp_path)])

  assert exit_code == 0
  assert capsys.readouterr().out == "t1\nt2\n"


def test_main_returns_one_when_sso_check_fails(monkeypatch, tmp_path):
  monkeypatch.setattr(
      run_table_ddl_export.athena_cli_common, "ensure_sso_or_log_failure",
      lambda run_config, logger: False)

  exit_code = run_table_ddl_export.main([
      "--database", "my_db", "--tables", "t1", "--profile", "p",
      "--workgroup", "primary", "--output-location", "s3://bucket/",
      "--log-dir", str(tmp_path)])

  assert exit_code == 1


def test_main_database_auto_discovers_tables(monkeypatch, tmp_path):
  monkeypatch.setattr(
      run_table_ddl_export.athena_cli_common, "build_executor",
      lambda run_config: (
          _FakeExecutor(),
          _FakeDownloader(table_list_content="only_table\n")))
  monkeypatch.setattr(
      run_table_ddl_export.athena_cli_common, "ensure_sso_or_log_failure",
      lambda run_config, logger: True)

  output_path = tmp_path / "ddl.csv"
  exit_code = run_table_ddl_export.main([
      "--database", "my_db", "--profile", "p", "--workgroup", "primary",
      "--output-location", "s3://bucket/", "--output", str(output_path),
      "--log-dir", str(tmp_path)])

  assert exit_code == 0
  rows = _read_ddl_csv(output_path)
  assert [row["table_name"] for row in rows] == ["only_table"]
