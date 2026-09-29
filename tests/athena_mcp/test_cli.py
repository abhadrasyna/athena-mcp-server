"""Tests for athena_mcp.cli: argparse defaults + server wiring.

`main()` itself (the console-script entry point) starts `server.run()`,
which blocks forever over stdio -- these tests monkeypatch `server.run`
so `main()` can be exercised end-to-end (arg parsing, logging setup,
`PROJECT_CONFIGS` mutation) without actually starting a transport.
"""

# pylint: disable=protected-access
# These tests exercise cli's own module-private defaults/helpers
# directly, which is the whole point of testing them.

import logging

import pytest

from athena_mcp import cli
from athena_mcp import server
from athena_mcp import tool_config


@pytest.fixture(autouse=True)
def _restore_project_configs():
  """Restores `PROJECT_CONFIGS` after each test mutates it via `cli`."""
  original = dict(tool_config.PROJECT_CONFIGS)
  yield
  tool_config.PROJECT_CONFIGS.clear()
  tool_config.PROJECT_CONFIGS.update(original)


def test_build_arg_parser_defaults_are_relative_to_repo_root():
  parser = cli._build_arg_parser()
  args = parser.parse_args([])

  assert args.output_dir == str(cli._DEFAULT_OUTPUT_DIR)
  assert args.log_dir == str(cli._DEFAULT_LOG_DIR)
  assert args.poll_interval == cli._DEFAULT_POLL_INTERVAL_SECONDS
  assert args.timeout == cli._DEFAULT_TIMEOUT_SECONDS


def test_build_arg_parser_accepts_overrides(tmp_path):
  parser = cli._build_arg_parser()
  args = parser.parse_args([
      "--output-dir", str(tmp_path / "out"),
      "--log-dir", str(tmp_path / "logs"),
      "--poll-interval", "5",
      "--timeout", "60",
  ])

  assert args.output_dir == str(tmp_path / "out")
  assert args.log_dir == str(tmp_path / "logs")
  assert args.poll_interval == 5
  assert args.timeout == 60


def test_apply_server_defaults_overrides_all_registered_projects(tmp_path):
  cli._apply_server_defaults(
      output_dir=str(tmp_path), poll_interval_seconds=9, timeout_seconds=99)

  mtn_run_config = tool_config.PROJECT_CONFIGS["mtn"].run_config
  assert mtn_run_config.output_dir == str(tmp_path)
  assert mtn_run_config.poll_interval_seconds == 9
  assert mtn_run_config.timeout_seconds == 99
  # Unrelated fields (profile, workgroup, region) are preserved as-is.
  assert mtn_run_config.profile == "clarissa-insights-product"

  astro_run_config = tool_config.PROJECT_CONFIGS["astro"].run_config
  assert astro_run_config.output_dir == str(tmp_path)
  assert astro_run_config.poll_interval_seconds == 9
  assert astro_run_config.timeout_seconds == 99
  assert astro_run_config.profile == "astro-insights-product"


def test_apply_server_defaults_skips_unconfigured_projects(monkeypatch):
  monkeypatch.setitem(tool_config.PROJECT_CONFIGS, "unconfigured", None)

  cli._apply_server_defaults(
      output_dir="/tmp/out", poll_interval_seconds=2, timeout_seconds=300)

  assert tool_config.PROJECT_CONFIGS["unconfigured"] is None


def test_main_configures_logging_and_starts_server(tmp_path, monkeypatch):
  started = []
  monkeypatch.setattr(server, "run", lambda: started.append(True))

  cli.main([
      "--output-dir", str(tmp_path / "output"),
      "--log-dir", str(tmp_path / "logs"),
      "--poll-interval", "3",
      "--timeout", "42",
  ])

  assert started == [True]
  assert (tmp_path / "logs" / "athena_mcp_server.log").is_file()
  mtn_run_config = tool_config.PROJECT_CONFIGS["mtn"].run_config
  assert mtn_run_config.output_dir == str(tmp_path / "output")
  assert mtn_run_config.poll_interval_seconds == 3
  assert mtn_run_config.timeout_seconds == 42

  logging.getLogger("athena_runner").handlers.clear()
