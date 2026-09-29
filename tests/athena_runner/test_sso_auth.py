"""Tests for athena_runner.sso_auth."""

import subprocess

import botocore.exceptions
import pytest

from athena_runner import exceptions
from athena_runner import sso_auth


class _FakeStsClient:
  """Fake boto3 STS client raising a scripted sequence of outcomes."""

  def __init__(self, outcomes):
    # Each outcome is either None (success) or an exception instance.
    self._outcomes = list(outcomes)

  def get_caller_identity(self):
    outcome = self._outcomes.pop(0) if len(self._outcomes) > 1 \
        else self._outcomes[0]
    if outcome is not None:
      raise outcome
    return {"Account": "123456789012"}


def _client_error(code):
  return botocore.exceptions.ClientError(
      {"Error": {"Code": code, "Message": "boom"}}, "GetCallerIdentity")


def _fake_command_runner(returncode=0, stderr=""):
  def _run(command):
    del command  # Not inspected by these fakes.
    return subprocess.CompletedProcess(
        args=[], returncode=returncode, stdout="", stderr=stderr)
  return _run


def test_ensure_valid_returns_true_when_already_valid():
  sts_client = _FakeStsClient([None])
  refresher = sso_auth.SsoCredentialRefresher(
      profile="clarissa-insights-product",
      sts_client_factory=lambda: sts_client,
      command_runner=_fake_command_runner(),
      path_finder=lambda _: "/usr/local/bin/aws-sso",
  )

  assert refresher.ensure_valid() is True


def test_ensure_valid_refreshes_and_returns_false_on_expired_token():
  sts_client = _FakeStsClient([_client_error("ExpiredToken"), None])
  calls = []
  refresher = sso_auth.SsoCredentialRefresher(
      profile="clarissa-insights-product",
      sts_client_factory=lambda: sts_client,
      command_runner=lambda command: (
          calls.append(command) or
          subprocess.CompletedProcess([], 0, "", "")),
      path_finder=lambda _: "/usr/local/bin/aws-sso",
  )

  assert refresher.ensure_valid() is False
  assert calls[0][:2] == ["aws-sso", "--profile"]
  assert "--exact-role" in calls[0]


def test_ensure_valid_refreshes_on_no_credentials_error():
  sts_client = _FakeStsClient(
      [botocore.exceptions.NoCredentialsError(), None])
  refresher = sso_auth.SsoCredentialRefresher(
      profile="clarissa-insights-product",
      sts_client_factory=lambda: sts_client,
      command_runner=_fake_command_runner(),
      path_finder=lambda _: "/usr/local/bin/aws-sso",
  )

  assert refresher.ensure_valid() is False


def test_ensure_valid_reraises_non_auth_client_errors():
  sts_client = _FakeStsClient([_client_error("AccessDenied")])
  refresher = sso_auth.SsoCredentialRefresher(
      profile="clarissa-insights-product",
      sts_client_factory=lambda: sts_client,
      command_runner=_fake_command_runner(),
      path_finder=lambda _: "/usr/local/bin/aws-sso",
  )

  with pytest.raises(botocore.exceptions.ClientError):
    refresher.ensure_valid()


def test_ensure_valid_raises_sso_login_error_when_aws_sso_not_on_path():
  sts_client = _FakeStsClient([_client_error("ExpiredToken")])
  refresher = sso_auth.SsoCredentialRefresher(
      profile="clarissa-insights-product",
      sts_client_factory=lambda: sts_client,
      command_runner=_fake_command_runner(),
      path_finder=lambda _: None,
  )

  with pytest.raises(exceptions.SsoLoginError, match="not found on PATH"):
    refresher.ensure_valid()


def test_ensure_valid_raises_sso_login_error_when_command_fails():
  sts_client = _FakeStsClient([_client_error("ExpiredToken")])
  refresher = sso_auth.SsoCredentialRefresher(
      profile="clarissa-insights-product",
      sts_client_factory=lambda: sts_client,
      command_runner=_fake_command_runner(returncode=1, stderr="bad login"),
      path_finder=lambda _: "/usr/local/bin/aws-sso",
  )

  with pytest.raises(exceptions.SsoLoginError, match="bad login"):
    refresher.ensure_valid()


def test_ensure_valid_raises_sso_login_error_when_still_invalid_after_refresh():
  sts_client = _FakeStsClient(
      [_client_error("ExpiredToken"), _client_error("ExpiredToken")])
  refresher = sso_auth.SsoCredentialRefresher(
      profile="clarissa-insights-product",
      sts_client_factory=lambda: sts_client,
      command_runner=_fake_command_runner(),
      path_finder=lambda _: "/usr/local/bin/aws-sso",
  )

  with pytest.raises(exceptions.SsoLoginError, match="still has invalid"):
    refresher.ensure_valid()


def test_ensure_valid_raises_key_error_for_unmapped_profile():
  sts_client = _FakeStsClient([_client_error("ExpiredToken")])
  refresher = sso_auth.SsoCredentialRefresher(
      profile="no-such-profile",
      sts_client_factory=lambda: sts_client,
      command_runner=_fake_command_runner(),
      path_finder=lambda _: "/usr/local/bin/aws-sso",
  )

  with pytest.raises(KeyError, match="no-such-profile"):
    refresher.ensure_valid()
