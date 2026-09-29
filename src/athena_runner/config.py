"""Run configuration for a single Athena query execution."""

import dataclasses


@dataclasses.dataclass(frozen=True)
class RunConfig:
  """Immutable configuration for one Athena query run.

  Attributes:
    profile: AWS SSO profile name to build the boto3 session from.
    workgroup: Athena workgroup to run the query under.
    output_location: S3 URI where Athena writes its raw query results.
    output_dir: Local directory the final CSV is downloaded to.
    region: Optional AWS region override; defaults to the profile's region.
    poll_interval_seconds: Seconds to wait between query status polls.
    timeout_seconds: Max seconds to wait for the query to finish.
    max_concurrency: Max number of Athena queries to run concurrently,
      across metrics and month chunks. Not yet consumed by any query
      executor -- reserved for the upcoming parallel task pool.
  """

  profile: str
  workgroup: str
  output_location: str
  output_dir: str
  region: str | None = None
  poll_interval_seconds: int = 2
  timeout_seconds: int = 300
  max_concurrency: int = 5
