"""Custom exceptions for the Athena query runner."""


class AthenaRunnerError(Exception):
  """Base class for all athena_runner errors."""


class QueryExecutionError(AthenaRunnerError):
  """Raised when an Athena query reaches a FAILED or CANCELLED state."""


class QueryTimeoutError(AthenaRunnerError):
  """Raised when an Athena query does not finish within the allotted time."""


class SsoLoginError(AthenaRunnerError):
  """Raised when refreshing AWS SSO credentials via `aws-sso` fails."""


class MetricResultError(AthenaRunnerError):
  """Raised when an adoption metric's query result CSV is missing rows or
  the expected `session_date`/`metric_value` columns.
  """
