"""Tests for athena_mcp.query_tools."""

import pytest

from athena_runner import config as config_lib

from athena_mcp import query_tools
from athena_mcp import tool_config


class _FakeAthenaClient:
  """Fake boto3 Athena client that succeeds a single query immediately."""

  def __init__(self):
    self.start_query_execution_calls = []

  def start_query_execution(self, **kwargs):
    self.start_query_execution_calls.append(kwargs)
    return {"QueryExecutionId": "q-123"}

  def get_query_execution(self, QueryExecutionId):  # pylint: disable=invalid-name
    del QueryExecutionId
    return {
        "QueryExecution": {
            "Status": {"State": "SUCCEEDED"},
            "ResultConfiguration": {
                "OutputLocation": "s3://bucket/q-123.csv"},
            "Statistics": {
                "DataScannedInBytes": 10,
                "EngineExecutionTimeInMillis": 5,
            },
        }
    }


class _FakeS3Client:
  """Fake boto3 S3 client that writes a small, valid CSV on download."""

  def __init__(self, csv_contents="col1,col2\nv1,v2\n"):
    self.download_file_calls = []
    self._csv_contents = csv_contents

  def download_file(self, bucket, key, destination_path):
    self.download_file_calls.append((bucket, key, destination_path))
    with open(destination_path, "w", encoding="utf-8") as csv_file:
      csv_file.write(self._csv_contents)


class _FakeAwsClientFactory:
  """Fake AwsClientFactory returning scripted fake Athena/S3 clients."""

  instances = []

  def __init__(self, profile, region):
    self.profile = profile
    self.region = region
    self.athena = _FakeAthenaClient()
    self.s3 = _FakeS3Client()
    _FakeAwsClientFactory.instances.append(self)

  def athena_client(self):
    return self.athena

  def s3_client(self):
    return self.s3


class _FakeQuery:
  """Fake AthenaQuery for dispatch tests."""

  name = "fake-query"
  database = "fake_db"

  def __init__(self):
    self.build_sql_calls = []

  def build_sql(self, params):
    self.build_sql_calls.append(params)
    return "SELECT 1"

  def output_filename(self, params):
    del params
    return "fake_query_result.csv"


class _FakeRegistry:
  """Fake registry with a single registered `_FakeQuery`."""

  def __init__(self):
    self.query = _FakeQuery()

  def get(self, name):
    if name != self.query.name:
      raise KeyError(name)
    return self.query

  def names(self):
    return [self.query.name]


@pytest.fixture(autouse=True)
def _reset_fake_client_factory_instances():
  _FakeAwsClientFactory.instances = []
  yield
  _FakeAwsClientFactory.instances = []


@pytest.fixture(autouse=True)
def _patch_aws_client_factory(monkeypatch):
  monkeypatch.setattr(
      query_tools.aws_clients, "AwsClientFactory", _FakeAwsClientFactory)


@pytest.fixture
def _fake_registry():
  return _FakeRegistry()


@pytest.fixture
def _fake_project_config(monkeypatch, tmp_path, _fake_registry):
  """Registers a 'fake' project backed by `_FakeRegistry`/mocked boto3."""
  project_config = tool_config.ProjectConfig(
      run_config=config_lib.RunConfig(
          profile="fake-profile",
          workgroup="primary",
          output_location="s3://bucket/",
          output_dir=str(tmp_path),
      ),
      database="fake_db",
      registry_loader=lambda: _fake_registry,
  )
  monkeypatch.setitem(tool_config.PROJECT_CONFIGS, "fake", project_config)
  return project_config


@pytest.fixture
def _sso_calls(monkeypatch):
  calls = []
  monkeypatch.setattr(
      query_tools.cli_common, "ensure_valid_sso_credentials",
      lambda run_config: calls.append(run_config) or True)
  return calls


def test_list_athena_queries_reflects_registry_contents(
    _fake_project_config):
  descriptors = query_tools.list_athena_queries("fake")

  assert [d.name for d in descriptors] == ["fake-query"]
  assert descriptors[0].database == "fake_db"


def test_list_athena_queries_raises_for_unregistered_project():
  with pytest.raises(ValueError, match="Unknown project"):
    query_tools.list_athena_queries("no-such-project")


def test_run_registered_athena_query_dispatches_to_registry(
    _fake_project_config, _fake_registry, _sso_calls):
  del _sso_calls

  result = query_tools.run_registered_athena_query(
      "fake", "fake-query", {"date": "2026-07-08"})

  assert result.query_execution_id == "q-123"
  assert result.data_scanned_bytes == 10
  assert result.engine_execution_ms == 5
  assert _fake_registry.query.build_sql_calls == [{"date": "2026-07-08"}]
  assert result.preview.columns == ["col1", "col2"]


def test_run_registered_athena_query_raises_for_unknown_query_name(
    _fake_project_config, _sso_calls):
  del _sso_calls

  with pytest.raises(KeyError):
    query_tools.run_registered_athena_query("fake", "nope", {})


def test_run_athena_sql_passes_sql_and_database_through_unmodified(
    _fake_project_config, _sso_calls):
  del _sso_calls

  query_tools.run_athena_sql("fake", "SELECT * FROM t", database="custom_db")

  factory = _FakeAwsClientFactory.instances[0]
  call = factory.athena.start_query_execution_calls[0]
  assert call["QueryString"] == "SELECT * FROM t"
  assert call["QueryExecutionContext"] == {"Database": "custom_db"}


def test_run_athena_sql_defaults_to_project_database(
    _fake_project_config, _sso_calls):
  del _sso_calls

  query_tools.run_athena_sql("fake", "SELECT * FROM t")

  factory = _FakeAwsClientFactory.instances[0]
  call = factory.athena.start_query_execution_calls[0]
  assert call["QueryExecutionContext"] == {"Database": "fake_db"}


def test_sso_preflight_invoked_before_execute(
    _fake_project_config, _sso_calls):
  query_tools.run_athena_sql("fake", "SELECT 1")

  assert len(_sso_calls) == 1
  assert _sso_calls[0].profile == "fake-profile"


def test_run_athena_sql_raises_for_unregistered_project():
  with pytest.raises(ValueError, match="Unknown project"):
    query_tools.run_athena_sql("no-such-project", "SELECT 1")


def test_list_athena_queries_raises_not_implemented_for_astro():
  # ASTRO-4: 'astro' is now fully configured but has no registered-query
  # registry (registry_loader=None) -- ASTRO-3 found no MTN AthenaQuery
  # applies to Astro's schema, and Astro-specific ones are a follow-up.
  with pytest.raises(NotImplementedError, match="no registered-query"):
    query_tools.list_athena_queries("astro")


def test_run_registered_athena_query_raises_not_implemented_for_astro():
  with pytest.raises(NotImplementedError, match="no registered-query"):
    query_tools.run_registered_athena_query("astro", "playback-outcome", {})


def test_effective_run_config_rejects_unknown_override_keys(
    _fake_project_config):
  with pytest.raises(ValueError, match="Unsupported override"):
    query_tools.run_athena_sql(
        "fake", "SELECT 1", overrides={"bogus_field": "x"})


def test_refresh_athena_sso_returns_refresher_result(
    _fake_project_config, monkeypatch):
  monkeypatch.setattr(
      query_tools.cli_common, "ensure_valid_sso_credentials",
      lambda run_config: False)

  assert query_tools.refresh_athena_sso("fake") is False
