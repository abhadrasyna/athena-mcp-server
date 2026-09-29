"""`athena-mcp-server` console-script entry point.

See `story.md`'s "Config defaults" and "Standalone packaging" sections.
This is the only executable entry point for this package -- no bare
top-level launcher script under `src/` or elsewhere, per the
"Standalone packaging" decision. It owns:

- argparse for the server-wide config defaults (`--output-dir`,
  `--log-dir`, `--poll-interval`, `--timeout`), all resolved relative
  to this repo's root, never the caller's cwd (a caller may invoke
  `athena-mcp-server` from any other project's directory once
  registered at the Copilot CLI user/global level).
- Configuring logging (via `athena_runner.logging_setup`) before any
  tool call can log anything -- `athena_mcp.server` itself never
  configures logging (see its module docstring).
- Applying the parsed config defaults onto every registered project's
  `RunConfig` in `athena_mcp.tool_config.PROJECT_CONFIGS`, then
  starting `athena_mcp.server`'s `MCPServer` instance over stdio.
"""

import argparse
import dataclasses
import pathlib
from typing import Optional, Sequence

from athena_runner import logging_setup

from athena_mcp import server
from athena_mcp import tool_config

# Mirrors `tool_config._REPO_ROOT`: `src/athena_mcp/cli.py` -> repo root.
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_DEFAULT_OUTPUT_DIR = _REPO_ROOT / "output"
_DEFAULT_LOG_DIR = _REPO_ROOT / "logs"

# Mirrors `athena_runner.config.RunConfig`'s own field defaults.
_DEFAULT_POLL_INTERVAL_SECONDS = 2
_DEFAULT_TIMEOUT_SECONDS = 300


def _build_arg_parser() -> argparse.ArgumentParser:
  """Builds the `athena-mcp-server` argparse parser."""
  parser = argparse.ArgumentParser(
      prog="athena-mcp-server",
      description=(
          "Starts the Athena MCP server (stdio transport), exposing "
          "Athena querying as MCP tools. See docs/mcp-server-setup.md."
      ),
  )
  parser.add_argument(
      "--output-dir",
      default=str(_DEFAULT_OUTPUT_DIR),
      help=(
          "Local directory downloaded result CSVs are saved to. "
          f"Defaults to this repo's own 'output/' dir ({_DEFAULT_OUTPUT_DIR})"
          ", not the caller's cwd."
      ),
  )
  parser.add_argument(
      "--log-dir",
      default=str(_DEFAULT_LOG_DIR),
      help=(
          "Directory the server's log file is written to. Defaults to "
          f"this repo's own 'logs/' dir ({_DEFAULT_LOG_DIR}), not the "
          "caller's cwd."
      ),
  )
  parser.add_argument(
      "--poll-interval",
      type=int,
      default=_DEFAULT_POLL_INTERVAL_SECONDS,
      help=(
          "Seconds to wait between Athena query status polls. Defaults "
          f"to {_DEFAULT_POLL_INTERVAL_SECONDS}."
      ),
  )
  parser.add_argument(
      "--timeout",
      type=int,
      default=_DEFAULT_TIMEOUT_SECONDS,
      help=(
          "Max seconds to wait for an Athena query to finish before "
          f"giving up. Defaults to {_DEFAULT_TIMEOUT_SECONDS}."
      ),
  )
  return parser


def _apply_server_defaults(
    output_dir: str, poll_interval_seconds: int, timeout_seconds: int
) -> None:
  """Applies parsed CLI config onto every registered project's `RunConfig`.

  Mutates `tool_config.PROJECT_CONFIGS` in place, in this process, before
  `server.run()` starts accepting tool calls -- every project resolved
  later via `tool_config.get_project_config` picks up these overrides.
  Projects not yet fully configured (registered but still `None`,
  pending their own discovery tasks) are left untouched.

  Args:
    output_dir: Overrides each `RunConfig.output_dir`.
    poll_interval_seconds: Overrides each `RunConfig.poll_interval_seconds`.
    timeout_seconds: Overrides each `RunConfig.timeout_seconds`.
  """
  for project, project_config in tool_config.PROJECT_CONFIGS.items():
    if project_config is None:
      continue
    new_run_config = dataclasses.replace(
        project_config.run_config,
        output_dir=output_dir,
        poll_interval_seconds=poll_interval_seconds,
        timeout_seconds=timeout_seconds,
    )
    tool_config.PROJECT_CONFIGS[project] = dataclasses.replace(
        project_config, run_config=new_run_config)


def main(argv: Optional[Sequence[str]] = None) -> None:
  """Parses CLI args, configures logging, and starts the MCP server.

  Args:
    argv: Argument list to parse instead of `sys.argv[1:]`; used by
      tests, left `None` in normal console-script invocation.
  """
  parser = _build_arg_parser()
  args = parser.parse_args(argv)

  logging_setup.configure_logging(args.log_dir, "athena_mcp_server")
  _apply_server_defaults(args.output_dir, args.poll_interval, args.timeout)

  server.run()


if __name__ == "__main__":
  main()
