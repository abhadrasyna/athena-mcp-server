"""Tests for athena_mcp.server: tool registration + stdio hygiene.

The stdio-hygiene tests verify (per `story.md`'s "Critical
implementation constraint: stdio hygiene" section) that
`athena_runner.logging_setup`'s handlers -- and by extension every code
path reachable from an MCP tool call -- never write to stdout, since
stdout is reserved exclusively for JSON-RPC frames when this server
runs over stdio. A stray `print()`/misconfigured handler here would
silently corrupt the protocol stream.
"""

import asyncio
import io
import logging

import pytest

from athena_runner import logging_setup

from athena_mcp import server


def test_all_four_tools_are_registered():
  tools = asyncio.run(server.server.list_tools())
  tool_names = {tool.name for tool in tools}

  assert tool_names == {
      "list_athena_queries",
      "run_registered_athena_query",
      "run_athena_sql",
      "refresh_athena_sso",
  }


def test_logging_setup_never_writes_to_stdout(tmp_path, monkeypatch):
  captured_stdout = io.StringIO()
  monkeypatch.setattr("sys.stdout", captured_stdout)

  logging_setup.configure_logging(str(tmp_path), "test_stdio_hygiene")
  logger = logging.getLogger("athena_runner")
  logger.debug("debug message")
  logger.info("info message")
  logger.warning("warning message")
  logger.error("error message")

  assert captured_stdout.getvalue() == ""


def test_logging_setup_handlers_are_not_attached_to_stdout(tmp_path):
  logging_setup.configure_logging(str(tmp_path), "test_stdio_hygiene_2")
  logger = logging.getLogger("athena_runner")

  for handler in logger.handlers:
    stream = getattr(handler, "stream", None)
    if stream is not None:
      assert stream.name != "<stdout>", (
          f"Handler {handler!r} is attached to stdout -- would corrupt "
          "the MCP JSON-RPC frame stream.")


@pytest.fixture(autouse=True)
def _reset_athena_runner_logger():
  """Leaves the shared 'athena_runner' logger clean for other test modules."""
  yield
  logger = logging.getLogger("athena_runner")
  for handler in list(logger.handlers):
    handler.close()
    logger.removeHandler(handler)
