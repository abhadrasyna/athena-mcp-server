"""Shared CLI-boundary helpers used by both `run_athena_query.py` and
`run_adoption_report.py`.

Kept separate from either script (SRP/DRY) so the SSO pre-flight check
only has one implementation to maintain.
"""

from athena_runner import aws_clients
from athena_runner import config as config_lib
from athena_runner import sso_auth


def ensure_valid_sso_credentials(run_config: config_lib.RunConfig) -> bool:
  """Ensures `run_config.profile` has valid AWS SSO credentials.

  Args:
    run_config: Supplies the profile/region to check.

  Returns:
    True if credentials were already valid; False if a refresh via
    `aws-sso` was required (and succeeded).

  Raises:
    exceptions.SsoLoginError: If credentials are invalid and `aws-sso`
      isn't installed, fails, or credentials are still invalid after.
  """
  def _sts_client_factory():
    return aws_clients.AwsClientFactory(
        run_config.profile, run_config.region).sts_client()

  refresher = sso_auth.SsoCredentialRefresher(
      run_config.profile, _sts_client_factory)
  return refresher.ensure_valid()
