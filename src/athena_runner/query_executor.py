"""Executes Athena queries and blocks until they reach a terminal state."""

import abc
import logging
import time
from typing import Any, Dict, NamedTuple

from athena_runner import config as config_lib
from athena_runner import exceptions

_logger = logging.getLogger(__name__)


class QueryResult(NamedTuple):
  """Outcome of a successfully completed Athena query.

  Attributes:
    query_execution_id: Athena's identifier for the query run.
    output_location: S3 URI Athena wrote the raw results to.
    data_scanned_bytes: Bytes scanned, for cost/perf visibility.
    engine_execution_ms: Query engine execution time in milliseconds.
  """
  query_execution_id: str
  output_location: str
  data_scanned_bytes: int
  engine_execution_ms: int


class AthenaQueryExecutor(abc.ABC):
  """Interface for running a SQL string against Athena to completion.

  Kept minimal (Interface Segregation) so callers that only need to run
  and wait for a query aren't forced to depend on download or query-
  definition concerns.
  """

  @abc.abstractmethod
  def run(self, sql: str, database: str) -> QueryResult:
    """Runs `sql` against `database` and blocks until it finishes.

    Args:
      sql: The Athena SQL statement to execute.
      database: The Athena database/catalog to run the query against.

    Returns:
      A QueryResult describing the succeeded query.

    Raises:
      exceptions.QueryExecutionError: If the query fails or is cancelled.
      exceptions.QueryTimeoutError: If the query doesn't finish in time.
    """


class BotoAthenaQueryExecutor(AthenaQueryExecutor):
  """AthenaQueryExecutor backed by a boto3 Athena client."""

  _TERMINAL_STATES = frozenset({"SUCCEEDED", "FAILED", "CANCELLED"})

  def __init__(self, athena_client: Any,
               run_config: config_lib.RunConfig) -> None:
    """Initializes the executor.

    Args:
      athena_client: A boto3 Athena client (see aws_clients.AwsClientFactory).
      run_config: Workgroup/output-location/timeout settings for this run.
    """
    self._athena = athena_client
    self._config = run_config

  def run(self, sql: str, database: str) -> QueryResult:
    query_execution_id = self._start(sql, database)
    execution = self._poll_until_terminal(query_execution_id)
    return self._to_query_result(query_execution_id, execution)

  def _start(self, sql: str, database: str) -> str:
    response = self._athena.start_query_execution(
        QueryString=sql,
        QueryExecutionContext={"Database": database},
        WorkGroup=self._config.workgroup,
        ResultConfiguration={"OutputLocation": self._config.output_location},
    )
    query_execution_id = response["QueryExecutionId"]
    _logger.info(
        "Started Athena query %s on database=%s workgroup=%s",
        query_execution_id, database, self._config.workgroup)
    return query_execution_id

  def _poll_until_terminal(self, query_execution_id: str) -> Dict[str, Any]:
    """Polls Athena until the query is done, then returns its execution."""
    waited_seconds = 0
    while True:
      response = self._athena.get_query_execution(
          QueryExecutionId=query_execution_id)
      execution = response["QueryExecution"]
      status = execution["Status"]
      _logger.debug(
          "Query %s status=%s waited=%ss", query_execution_id,
          status["State"], waited_seconds)
      if status["State"] in self._TERMINAL_STATES:
        self._raise_if_not_succeeded(query_execution_id, status)
        return execution
      if waited_seconds >= self._config.timeout_seconds:
        raise exceptions.QueryTimeoutError(
            f"Query {query_execution_id} still {status['State']} after "
            f"{self._config.timeout_seconds}s")
      time.sleep(self._config.poll_interval_seconds)
      waited_seconds += self._config.poll_interval_seconds

  def _raise_if_not_succeeded(self, query_execution_id: str,
                               status: Dict[str, Any]) -> None:
    if status["State"] != "SUCCEEDED":
      reason = status.get("StateChangeReason", "unknown reason")
      _logger.error(
          "Query %s ended in %s: %s", query_execution_id, status["State"],
          reason)
      raise exceptions.QueryExecutionError(
          f"Query {query_execution_id} ended in {status['State']}: {reason}")

  def _to_query_result(self, query_execution_id: str,
                        execution: Dict[str, Any]) -> QueryResult:
    stats = execution.get("Statistics", {})
    _logger.info(
        "Query %s SUCCEEDED in %sms, scanned %s bytes", query_execution_id,
        stats.get("EngineExecutionTimeInMillis", "?"),
        stats.get("DataScannedInBytes", "?"))
    return QueryResult(
        query_execution_id=query_execution_id,
        output_location=execution["ResultConfiguration"]["OutputLocation"],
        data_scanned_bytes=stats.get("DataScannedInBytes", 0),
        engine_execution_ms=stats.get("EngineExecutionTimeInMillis", 0),
    )
