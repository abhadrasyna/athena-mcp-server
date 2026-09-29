"""Tests for athena_runner.query_executor."""

import pytest

from athena_runner import config as config_lib
from athena_runner import exceptions
from athena_runner import query_executor


def _run_config(**overrides):
  defaults = {
      "profile": "test-profile",
      "workgroup": "primary",
      "output_location": "s3://bucket/",
      "output_dir": "/tmp/out",
      "poll_interval_seconds": 0,
      "timeout_seconds": 5,
  }
  defaults.update(overrides)
  return config_lib.RunConfig(**defaults)


class _FakeAthenaClient:
  """Fake boto3 Athena client that walks through a scripted state list."""

  def __init__(self, states):
    self._states = list(states)
    self.start_query_execution_calls = []

  def start_query_execution(self, **kwargs):
    self.start_query_execution_calls.append(kwargs)
    return {"QueryExecutionId": "q-123"}

  def get_query_execution(self, QueryExecutionId):  # pylint: disable=invalid-name
    del QueryExecutionId  # Single scripted execution per test.
    state = self._states.pop(0) if len(self._states) > 1 else self._states[0]
    execution = {
        "Status": {"State": state},
        "ResultConfiguration": {"OutputLocation": "s3://bucket/q-123.csv"},
        "Statistics": {
            "DataScannedInBytes": 100,
            "EngineExecutionTimeInMillis": 50,
        },
    }
    if state != "SUCCEEDED":
      execution["Status"]["StateChangeReason"] = "boom"
    return {"QueryExecution": execution}


def test_run_returns_query_result_on_success():
  client = _FakeAthenaClient(["RUNNING", "SUCCEEDED"])
  executor = query_executor.BotoAthenaQueryExecutor(client, _run_config())

  result = executor.run("SELECT 1", "my_db")

  assert result.query_execution_id == "q-123"
  assert result.output_location == "s3://bucket/q-123.csv"
  assert result.data_scanned_bytes == 100
  assert result.engine_execution_ms == 50
  assert client.start_query_execution_calls[0]["QueryExecutionContext"] == {
      "Database": "my_db"}


def test_run_raises_query_execution_error_on_failure():
  client = _FakeAthenaClient(["FAILED"])
  executor = query_executor.BotoAthenaQueryExecutor(client, _run_config())

  with pytest.raises(exceptions.QueryExecutionError, match="boom"):
    executor.run("SELECT 1", "my_db")


def test_run_raises_query_timeout_error_when_never_terminal():
  client = _FakeAthenaClient(["RUNNING"])
  run_config = _run_config(timeout_seconds=0, poll_interval_seconds=0)
  executor = query_executor.BotoAthenaQueryExecutor(client, run_config)

  with pytest.raises(exceptions.QueryTimeoutError):
    executor.run("SELECT 1", "my_db")
