"""Factory for boto3 clients that share one authenticated AWS SSO session."""


import boto3


class AwsClientFactory:
  """Builds boto3 clients scoped to a single profile/session.

  Centralizing session/client creation here means every other module
  depends on this abstraction instead of constructing boto3 sessions
  itself (Dependency Inversion), and "how we authenticate to AWS" stays
  this class's single responsibility.
  """

  def __init__(self, profile: str, region: str | None = None) -> None:
    """Initializes the factory with a boto3 session for `profile`.

    Args:
      profile: AWS SSO profile name (see ../../docs/aws-sso-setup.md).
      region: Optional AWS region override; defaults to the profile's
        configured region.
    """
    self._session = boto3.Session(profile_name=profile, region_name=region)

  def athena_client(self):
    """Returns a boto3 Athena client for the configured session."""
    return self._session.client("athena")

  def s3_client(self):
    """Returns a boto3 S3 client for the configured session."""
    return self._session.client("s3")

  def sts_client(self):
    """Returns a boto3 STS client for the configured session."""
    return self._session.client("sts")
