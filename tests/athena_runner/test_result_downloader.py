"""Tests for athena_runner.result_downloader."""

from athena_runner import result_downloader


class _FakeS3Client:
  """Fake boto3 S3 client that records download_file calls."""

  def __init__(self):
    self.download_calls = []

  def download_file(self, bucket, key, destination_path):
    self.download_calls.append((bucket, key, destination_path))
    with open(destination_path, "w", encoding="utf-8") as f:
      f.write("stub")


def test_download_parses_bucket_and_key_and_creates_parent_dirs(tmp_path):
  s3_client = _FakeS3Client()
  downloader = result_downloader.S3ResultDownloader(s3_client)
  destination = tmp_path / "nested" / "out.csv"

  downloader.download("s3://my-bucket/some/key.csv", str(destination))

  assert s3_client.download_calls == [
      ("my-bucket", "some/key.csv", str(destination))]
  assert destination.parent.is_dir()
