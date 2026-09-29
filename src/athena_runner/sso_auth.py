"""Ensures an AWS SSO profile has valid, non-expired credentials.

Verifies credentials with STS `get_caller_identity`; if that fails with
an auth-related error, shells out to `aws-sso` to refresh transparently
(non-interactive, using ~/.aws/sso_secrets -- see ../../docs/aws-sso-setup.md)
instead of failing the whole run.
"""

import functools
import logging
import shutil
import subprocess
from typing import Any, Callable, List

import botocore.exceptions

from athena_runner import exceptions
from athena_runner import sso_profiles

_logger = logging.getLogger(__name__)

# STS error codes that mean "credentials are stale/invalid", not "something
# else is wrong" (e.g. a real permissions error should still surface).
_AUTH_ERROR_CODES = frozenset({
    "ExpiredToken",
    "ExpiredTokenException",
    "UnrecognizedClientException",
    "InvalidClientTokenId",
    "AuthFailure",
})

CommandRunner = Callable[[List[str]], "subprocess.CompletedProcess[str]"]
PathFinder = Callable[[str], "str | None"]

_DEFAULT_COMMAND_RUNNER: CommandRunner = functools.partial(
    subprocess.run, capture_output=True, text=True, check=False)


class SsoCredentialRefresher:
  """Checks and, if needed, refreshes AWS SSO credentials for one profile.

  Kept separate from AthenaQueryExecutor (SRP/ISP): callers that only
  need to run an already-authenticated query aren't forced to depend on
  the SSO refresh flow, and this class doesn't need to know anything
  about Athena. `sts_client_factory` is called fresh each time (rather
  than reusing one client) so a just-refreshed credentials file is
  actually re-read from disk (Dependency Inversion: this class doesn't
  care how the client is built).
  """

  def __init__(
      self,
      profile: str,
      sts_client_factory: Callable[[], Any],
      command_runner: CommandRunner = _DEFAULT_COMMAND_RUNNER,
      path_finder: PathFinder = shutil.which,
  ) -> None:
    """Initializes the refresher.

    Args:
      profile: AWS SSO profile name to check/refresh.
      sts_client_factory: Zero-arg callable returning a fresh boto3 STS
        client built from `profile`'s current credentials.
      command_runner: Runs the `aws-sso` command; defaults to
        `subprocess.run`. Overridable for testing.
      path_finder: Looks up a binary on PATH; defaults to `shutil.which`.
        Overridable for testing.
    """
    self._profile = profile
    self._sts_client_factory = sts_client_factory
    self._command_runner = command_runner
    self._path_finder = path_finder

  def ensure_valid(self) -> bool:
    """Ensures the profile has valid credentials, refreshing if needed.

    Returns:
      True if credentials were already valid; False if a refresh via
      `aws-sso` was required (and succeeded).

    Raises:
      exceptions.SsoLoginError: If credentials are invalid/expired and
        `aws-sso` isn't installed, fails, or credentials are still
        invalid afterward.
    """
    if self._credentials_are_valid():
      return True
    _logger.info(
        "Credentials for profile '%s' are stale/invalid; refreshing via "
        "aws-sso...", self._profile)
    self._refresh_via_aws_sso()
    if not self._credentials_are_valid():
      _logger.error(
          "'aws-sso' ran but profile '%s' still has invalid credentials.",
          self._profile)
      raise exceptions.SsoLoginError(
          f"'aws-sso' ran but profile '{self._profile}' still has "
          "invalid credentials afterward.")
    _logger.info("Refreshed credentials for profile '%s'.", self._profile)
    return False

  def _credentials_are_valid(self) -> bool:
    try:
      self._sts_client_factory().get_caller_identity()
      return True
    except botocore.exceptions.ClientError as exc:
      code = exc.response.get("Error", {}).get("Code", "")
      if code in _AUTH_ERROR_CODES:
        _logger.debug(
            "Profile '%s' credentials invalid: %s", self._profile, code)
        return False
      raise
    except botocore.exceptions.NoCredentialsError:
      _logger.debug("Profile '%s' has no credentials on disk.", self._profile)
      return False

  def _refresh_via_aws_sso(self) -> None:
    if self._path_finder("aws-sso") is None:
      raise exceptions.SsoLoginError(
          "'aws-sso' not found on PATH; install it per docs/aws-sso-setup.md "
          "or run it manually to refresh credentials.")
    role_mapping = sso_profiles.get_role_mapping(self._profile)
    command = [
        "aws-sso", "--profile", self._profile,
        "--desired-role", role_mapping.desired_role,
        "--maximum-duration", "auto",
    ]
    if role_mapping.exact_role:
      command.append("--exact-role")
    _logger.debug("Running: %s", " ".join(command))
    result = self._command_runner(command)
    if result.returncode != 0:
      stderr = (result.stderr or "").strip()
      _logger.error(
          "'aws-sso' login for profile '%s' failed (exit %s): %s",
          self._profile, result.returncode, stderr)
      raise exceptions.SsoLoginError(
          f"'aws-sso' login for profile '{self._profile}' failed "
          f"(exit {result.returncode}): {stderr}")
