"""Tests for athena_mcp.tool_config."""

# pylint: disable=protected-access
# These tests exercise tool_config's internal mounting mechanism
# directly, which is the whole point of this module's docstring
# ("Registered-query registry loading mechanism").

import sys

import pytest

from athena_mcp import tool_config


def test_get_project_config_returns_mtn_config():
  project_config = tool_config.get_project_config("mtn")

  assert project_config.run_config.profile == "clarissa-insights-product"
  assert project_config.database == "unified_e6auj7k7"
  assert project_config.registry_loader is not None


def test_get_project_config_raises_value_error_for_unknown_project():
  with pytest.raises(ValueError, match="Unknown project 'nope'"):
    tool_config.get_project_config("nope")


def test_get_project_config_returns_astro_config():
  project_config = tool_config.get_project_config("astro")

  assert project_config.run_config.profile == "astro-insights-product"
  assert project_config.run_config.workgroup == "primary"
  assert project_config.run_config.output_location == (
      "s3://aws-athena-query-results-315899926467-ap-southeast-1/")
  assert project_config.run_config.region == "ap-southeast-1"
  assert project_config.database == "default"
  assert project_config.registry_loader is None


def test_mount_external_subpackage_loads_directory_as_dotted_name(
    tmp_path, monkeypatch):
  package_dir = tmp_path / "fake_pkg"
  package_dir.mkdir()
  (package_dir / "__init__.py").write_text("")
  (package_dir / "leaf.py").write_text("VALUE = 42")

  monkeypatch.setitem(sys.modules, "athena_runner",
                       sys.modules["athena_runner"])
  dotted_name = "athena_runner._test_fake_pkg"
  monkeypatch.delitem(sys.modules, dotted_name, raising=False)

  module = tool_config._mount_external_subpackage(dotted_name, package_dir)

  assert module.__name__ == dotted_name
  assert sys.modules["athena_runner"]._test_fake_pkg is module

  import importlib  # pylint: disable=import-outside-toplevel
  leaf = importlib.import_module(f"{dotted_name}.leaf")
  assert leaf.VALUE == 42

  del sys.modules[dotted_name]
  del sys.modules[f"{dotted_name}.leaf"]
  delattr(sys.modules["athena_runner"], "_test_fake_pkg")


def test_mount_external_subpackage_raises_file_not_found_when_missing(
    tmp_path):
  missing_dir = tmp_path / "does-not-exist"

  with pytest.raises(FileNotFoundError, match="does-not-exist"):
    tool_config._mount_external_subpackage(
        "athena_runner._missing_test_pkg", missing_dir)


def test_load_mtn_registry_resolves_playback_outcome_query():
  mtn_queries_dir = tool_config._mtn_queries_dir()
  if not mtn_queries_dir.is_dir():
    pytest.skip(
        f"Sibling aws-access-cli checkout not found at {mtn_queries_dir}")

  registry = tool_config._load_mtn_registry()

  assert "playback-outcome" in registry.names()
  query = registry.get("playback-outcome")
  assert query.database == "unified_e6auj7k7"
