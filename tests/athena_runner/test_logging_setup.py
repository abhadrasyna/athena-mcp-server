"""Tests for athena_runner.logging_setup."""

import logging
import os

from athena_runner import logging_setup


def test_configure_logging_creates_log_dir(tmp_path):
  log_dir = tmp_path / "logs"

  logging_setup.configure_logging(str(log_dir), "some_script")

  assert log_dir.is_dir()


def test_configure_logging_creates_a_log_file_named_after_the_script(
    tmp_path):
  log_path = logging_setup.configure_logging(str(tmp_path), "some_script")

  assert os.path.isfile(log_path)
  assert os.path.basename(log_path) == "some_script.log"


def test_configure_logging_writes_debug_records_to_file(tmp_path):
  log_path = logging_setup.configure_logging(str(tmp_path), "some_script")
  logger = logging.getLogger("athena_runner.some_module")

  logger.debug("a debug-level message")

  with open(log_path, encoding="utf-8") as log_file:
    contents = log_file.read()
  assert "a debug-level message" in contents


def test_configure_logging_only_sends_info_and_above_to_stream(
    tmp_path, capsys):
  logging_setup.configure_logging(str(tmp_path), "some_script")
  logger = logging.getLogger("athena_runner.some_module")

  logger.debug("should not reach stderr")
  logger.info("should reach stderr")

  captured = capsys.readouterr()
  assert "should not reach stderr" not in captured.err
  assert "should reach stderr" in captured.err


def test_configure_logging_is_idempotent_across_repeated_calls(tmp_path):
  logging_setup.configure_logging(str(tmp_path), "some_script")
  logging_setup.configure_logging(str(tmp_path), "some_script")
  logger = logging.getLogger("athena_runner")

  assert len(logger.handlers) == 2  # One stream handler, one file handler.


def test_configure_logging_reuses_the_same_path_across_separate_runs(
    tmp_path):
  # Simulates two separate CLI invocations (not two calls in one
  # process): each should resolve to the exact same on-disk path,
  # appending to it rather than creating a second file.
  first_path = logging_setup.configure_logging(str(tmp_path), "some_script")
  second_path = logging_setup.configure_logging(str(tmp_path), "some_script")

  assert first_path == second_path
  log_files = [
      name for name in os.listdir(str(tmp_path))
      if name.startswith("some_script")
  ]
  assert log_files == ["some_script.log"]


def test_configure_logging_rotates_once_max_bytes_is_exceeded(tmp_path):
  log_path = logging_setup.configure_logging(
      str(tmp_path), "some_script", max_bytes=200, backup_count=2)
  logger = logging.getLogger("athena_runner.some_module")

  # Each record is well under 200 bytes alone, but many of them
  # together exceed it, forcing at least one rotation.
  for i in range(50):
    logger.debug("message number %d, padded to take up some space", i)

  assert os.path.isfile(log_path)
  assert os.path.isfile(log_path + ".1")
  # backup_count=2 caps total rotated backups at 2, regardless of how
  # many rotations actually happened.
  assert not os.path.isfile(log_path + ".3")
