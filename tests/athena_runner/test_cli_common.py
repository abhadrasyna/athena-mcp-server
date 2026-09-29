"""Tests for athena_runner.cli_common."""

from athena_runner import cli_common
from athena_runner import config as config_lib


class _FakeStsClient:
  """Fake boto3 STS client that always reports valid credentials."""

  def get_caller_identity(self):
    return {"Account": "123456789012"}


class _FakeAwsClientFactory:
  """Fake AwsClientFactory recording the profile/region it was built with."""

  instances = []

  def __init__(self, profile, region):
    self.profile = profile
    self.region = region
    _FakeAwsClientFactory.instances.append(self)

  def sts_client(self):
    return _FakeStsClient()


def _run_config(**overrides):
  defaults = {
      "profile": "clarissa-insights-product",
      "workgroup": "primary",
      "output_location": "s3://bucket/",
      "output_dir": "/tmp/out",
  }
  defaults.update(overrides)
  return config_lib.RunConfig(**defaults)


def test_ensure_valid_sso_credentials_returns_true_when_already_valid(
    monkeypatch):
  _FakeAwsClientFactory.instances = []
  monkeypatch.setattr(
      cli_common.aws_clients, "AwsClientFactory", _FakeAwsClientFactory)

  result = cli_common.ensure_valid_sso_credentials(_run_config())

  assert result is True
  assert _FakeAwsClientFactory.instances[0].profile == (
      "clarissa-insights-product")


def test_ensure_valid_sso_credentials_uses_run_config_region(monkeypatch):
  _FakeAwsClientFactory.instances = []
  monkeypatch.setattr(
      cli_common.aws_clients, "AwsClientFactory", _FakeAwsClientFactory)

  cli_common.ensure_valid_sso_credentials(_run_config(region="eu-central-1"))

  assert _FakeAwsClientFactory.instances[0].region == "eu-central-1"
