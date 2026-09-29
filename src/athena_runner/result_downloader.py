"""Downloads a completed Athena query's raw S3 output to local disk."""

import abc
import logging
import os
from typing import Any
from urllib.parse import urlparse

_logger = logging.getLogger(__name__)


class ResultDownloader(abc.ABC):
  """Interface for fetching a completed query's output to local disk.

  Separated from AthenaQueryExecutor (Interface Segregation) so a caller
  that only runs queries without saving them locally isn't forced to
  depend on S3/download machinery.
  """

  @abc.abstractmethod
  def download(self, output_location: str, destination_path: str) -> None:
    """Copies the query result at `output_location` to `destination_path`.

    Args:
      output_location: S3 URI Athena wrote the raw result to, e.g.
        's3://bucket/path/query-id.csv'.
      destination_path: Local filesystem path to write the CSV to. Parent
        directories are created if missing.
    """


class S3ResultDownloader(ResultDownloader):
  """ResultDownloader backed by a boto3 S3 client."""

  def __init__(self, s3_client: Any) -> None:
    """Initializes the downloader.

    Args:
      s3_client: A boto3 S3 client (see aws_clients.AwsClientFactory).
    """
    self._s3 = s3_client

  def download(self, output_location: str, destination_path: str) -> None:
    bucket, key = self._parse_s3_uri(output_location)
    os.makedirs(os.path.dirname(destination_path) or ".", exist_ok=True)
    _logger.info(
        "Downloading s3://%s/%s to %s", bucket, key, destination_path)
    self._s3.download_file(bucket, key, destination_path)
    _logger.info("Wrote result to %s", destination_path)

  @staticmethod
  def _parse_s3_uri(s3_uri: str) -> tuple:
    parsed = urlparse(s3_uri)
    return parsed.netloc, parsed.path.lstrip("/")
