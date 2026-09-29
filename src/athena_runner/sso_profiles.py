"""Known AWS SSO profile -> IAM role mappings, for auto-refresh.

`aws-sso` needs an explicit `--desired-role` every time it authenticates
(see ../../docs/aws-sso-setup.md); this maps each profile this project uses to
the role it should request, so callers don't have to pass it on every
Athena query invocation. Add new profiles here as they're configured.
"""

import dataclasses


@dataclasses.dataclass(frozen=True)
class SsoRoleMapping:
  """Which IAM role a given AWS SSO profile should authenticate as.

  Attributes:
    desired_role: Role name/ARN passed to `aws-sso --desired-role`.
    exact_role: Whether to pass `aws-sso --exact-role` (the role ARN
      must match precisely) instead of fuzzy substring matching.
  """
  desired_role: str
  exact_role: bool = True


_PROFILE_ROLES: dict[str, SsoRoleMapping] = {
    "clarissa-insights-product": SsoRoleMapping(
        desired_role="arn:aws:iam::137353254249:role/readonly-synamedia",
        exact_role=True,
    ),
    "astro-insights-product": SsoRoleMapping(
        desired_role="arn:aws:iam::315899926467:role/devops-synamedia",
        exact_role=True,
    ),
}


def get_role_mapping(profile: str) -> SsoRoleMapping:
  """Returns the SsoRoleMapping registered for `profile`.

  Args:
    profile: The AWS SSO profile name (e.g. 'clarissa-insights-product').

  Raises:
    KeyError: If `profile` has no registered role mapping.
  """
  try:
    return _PROFILE_ROLES[profile]
  except KeyError as exc:
    available = ", ".join(sorted(_PROFILE_ROLES)) or "(none registered)"
    raise KeyError(
        f"No SSO role mapping for profile '{profile}'. Registered "
        f"profiles: {available}. Add one in sso_profiles.py.") from exc
