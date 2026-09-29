"""Tests for athena_runner.sso_profiles."""

import pytest

from athena_runner import sso_profiles


def test_get_role_mapping_returns_registered_mapping():
  mapping = sso_profiles.get_role_mapping("clarissa-insights-product")

  assert mapping.desired_role == (
      "arn:aws:iam::137353254249:role/readonly-synamedia")
  assert mapping.exact_role is True


def test_get_role_mapping_returns_astro_mapping():
  mapping = sso_profiles.get_role_mapping("astro-insights-product")

  assert mapping.desired_role == (
      "arn:aws:iam::315899926467:role/devops-synamedia")
  assert mapping.exact_role is True


def test_get_role_mapping_unknown_profile_raises_key_error():
  with pytest.raises(KeyError, match="clarissa-insights-product"):
    sso_profiles.get_role_mapping("unknown-profile")
