"""Tests for scripts/athena_cli_common.py."""

import logging
import os

import athena_cli_common

from athena_runner import cli_common
from athena_runner import config as config_lib
from athena_runner import exceptions
from athena_runner import query_executor
from athena_runner import result_downloader


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
  """Fake executor that returns a fixed QueryResult per `run()` call."""

  def __init__(self, output_location="s3://bucket/out.txt"):
    self.calls = []
    self._output_location = output_location

  def run(self, sql, database):
    self.calls.append((sql, database))
    return query_executor.QueryResult(
        query_execution_id="q-1", output_location=self._output_location,
        data_scanned_bytes=0, engine_execution_ms=0)


class _FakeDownloader(result_downloader.ResultDownloader):
  """Fake downloader that writes fixed `content` to any destination."""

  def __init__(self, content=""):
    self.content = content
    self.download_calls = []

  def download(self, output_location, destination_path):
    self.download_calls.append((output_location, destination_path))
    with open(destination_path, "w", encoding="utf-8") as handle:
      handle.write(self.content)


def test_build_executor_returns_boto_backed_pair(monkeypatch):
  built_clients = {}

  class _FakeClientFactory:
    def __init__(self, profile, region):
      built_clients["profile"] = profile
      built_clients["region"] = region

    def athena_client(self):
      return "athena-client"

    def s3_client(self):
      return "s3-client"

  monkeypatch.setattr(
      athena_cli_common.aws_clients, "AwsClientFactory", _FakeClientFactory)

  executor, downloader = athena_cli_common.build_executor(
      _run_config(profile="my-profile", region="eu-west-1"))

  assert built_clients == {"profile": "my-profile", "region": "eu-west-1"}
  assert isinstance(executor, query_executor.BotoAthenaQueryExecutor)
  assert isinstance(downloader, result_downloader.S3ResultDownloader)


def test_run_and_read_lines_returns_stripped_lines():
  executor = _FakeExecutor(output_location="s3://bucket/result.txt")
  downloader = _FakeDownloader(content="table_one\ntable_two\n")

  lines = athena_cli_common.run_and_read_lines(
      executor, downloader, "SHOW TABLES IN my_db", "my_db")

  assert lines == ["table_one", "table_two"]
  assert executor.calls == [("SHOW TABLES IN my_db", "my_db")]
  assert downloader.download_calls[0][0] == "s3://bucket/result.txt"


def test_run_and_read_lines_removes_temp_file_afterward():
  written_paths = []

  class _RecordingDownloader(result_downloader.ResultDownloader):
    def download(self, output_location, destination_path):
      written_paths.append(destination_path)
      with open(destination_path, "w", encoding="utf-8") as handle:
        handle.write("x\n")

  athena_cli_common.run_and_read_lines(
      _FakeExecutor(), _RecordingDownloader(), "SELECT 1", "my_db")

  assert written_paths
  assert not os.path.exists(written_paths[0])


def test_ensure_sso_or_log_failure_returns_true_when_already_valid(
    monkeypatch, caplog):
  monkeypatch.setattr(
      cli_common, "ensure_valid_sso_credentials", lambda run_config: True)

  with caplog.at_level(logging.INFO):
    result = athena_cli_common.ensure_sso_or_log_failure(
        _run_config(), logging.getLogger("test"))

  assert result is True
  assert "Refreshed" not in caplog.text


def test_ensure_sso_or_log_failure_logs_and_returns_true_on_refresh(
    monkeypatch, caplog):
  monkeypatch.setattr(
      cli_common, "ensure_valid_sso_credentials", lambda run_config: False)

  with caplog.at_level(logging.INFO):
    result = athena_cli_common.ensure_sso_or_log_failure(
        _run_config(profile="my-profile"), logging.getLogger("test"))

  assert result is True
  assert "Refreshed SSO credentials for profile 'my-profile'" in caplog.text


def test_ensure_sso_or_log_failure_returns_false_on_sso_login_error(
    monkeypatch, caplog):
  def _raise(run_config):
    del run_config
    raise exceptions.SsoLoginError("aws-sso failed")

  monkeypatch.setattr(cli_common, "ensure_valid_sso_credentials", _raise)

  with caplog.at_level(logging.INFO):
    result = athena_cli_common.ensure_sso_or_log_failure(
        _run_config(), logging.getLogger("test"))

  assert result is False
  assert "aws-sso failed" in caplog.text
