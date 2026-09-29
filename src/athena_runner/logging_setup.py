"""Configures standard library logging for this project's CLI scripts.

Every CLI invocation (`run_athena_query.py`, `refresh_aws_sso.py`) gets
INFO+ output on stderr as before, but now *also* a full DEBUG-level log
file under `logs/`, shared across every run of that script (not one
new file per invocation) -- so a failure can be diagnosed after the
fact from that log file, without needing to have watched the terminal
live, and without `logs/` accumulating one file per invocation
forever. The file rotates (stdlib `RotatingFileHandler`) once it
exceeds `max_bytes`, keeping `backup_count` old copies
(`<script_name>.log.1`, `.2`, ...) before older ones are discarded, so
the directory self-bounds instead of needing a separate cleanup job.

Library modules (`query_executor.py`, `sso_auth.py`, etc.) never call
`configure_logging` themselves -- they just do
`logging.getLogger(__name__)` and emit records (standard practice: only
the application/CLI entry point owns handler configuration).
"""

import logging
import logging.handlers
import os

_LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"

# 5 MiB per file, 5 backups kept -- roughly 30 MiB max per script's log
# lineage regardless of how many times it's invoked.
_DEFAULT_MAX_BYTES = 5 * 1024 * 1024
_DEFAULT_BACKUP_COUNT = 5


def configure_logging(
    log_dir: str,
    script_name: str,
    *,
    stream_level: int = logging.INFO,
    file_level: int = logging.DEBUG,
    force: bool = True,
    max_bytes: int = _DEFAULT_MAX_BYTES,
    backup_count: int = _DEFAULT_BACKUP_COUNT,
) -> str:
  """Configures the 'athena_runner' logger hierarchy for one CLI run.

  Args:
    log_dir: Directory the log file is written to (created if
      missing).
    script_name: Identifies the CLI in the log filename, e.g.
      'run_athena_query' -> `run_athena_query.log`.
    stream_level: Minimum level printed to stderr.
    file_level: Minimum level written to the log file.
    force: When False and the 'athena_runner' logger was already
      configured earlier in this same process, this call is skipped
      and the already-active log file's path is returned unchanged,
      instead of replacing it with a new one. This lets a script that
      may run either standalone (fresh process, nothing configured
      yet -- still fully configures as normal) or in-process as a
      sub-report of an outer orchestrator (which already set up one
      combined log file for the whole run) share that combined file
      rather than clobbering it with its own. Defaults to True
      (always reconfigure), matching every standalone CLI's behavior.
    max_bytes: Rotate the log file once it would exceed this size.
    backup_count: Number of rotated backups to keep
      (`<script_name>.log.1`, `.2`, ...) before the oldest is deleted.

  Returns:
    The full path to the log file active for this run (the same
    stable path every time, appended to across invocations until it
    rotates; unless skipped via `force=False`).
  """
  logger = logging.getLogger("athena_runner")
  # `_active_log_path` is stashed as an attribute on the logger itself
  # (rather than module-level state) so a `force=False` call can find
  # the path an earlier `configure_logging` call set up, without a
  # `global` statement.
  if not force and logger.handlers:
    return logger._active_log_path  # pylint: disable=protected-access

  logger.setLevel(min(stream_level, file_level))
  logger.handlers.clear()  # Idempotent: safe to call more than once.
  logger.propagate = False

  formatter = logging.Formatter(_LOG_FORMAT)

  stream_handler = logging.StreamHandler()
  stream_handler.setLevel(stream_level)
  stream_handler.setFormatter(formatter)
  logger.addHandler(stream_handler)

  os.makedirs(log_dir, exist_ok=True)
  log_path = os.path.join(log_dir, f"{script_name}.log")
  file_handler = logging.handlers.RotatingFileHandler(
      log_path, maxBytes=max_bytes, backupCount=backup_count,
      encoding="utf-8")
  file_handler.setLevel(file_level)
  file_handler.setFormatter(formatter)
  logger.addHandler(file_handler)

  logger._active_log_path = log_path  # pylint: disable=protected-access
  # A visible separator at the start of each run's section of the
  # (shared, appended-to) file, so runs are easy to tell apart when
  # scrolling through it.
  logger.debug("%s starting %s %s", "=" * 20, script_name, "=" * 20)
  return log_path
