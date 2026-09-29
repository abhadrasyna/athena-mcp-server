"""Reads the first few rows of a downloaded CSV for an inline MCP preview.

Kept separate from `query_tools.py` (Single Responsibility) so "how we
run a query" and "how we summarize its output for an agent" can change
independently.
"""

import csv
import dataclasses
from typing import List


@dataclasses.dataclass(frozen=True)
class ResultPreview:
  """A small, inline-renderable slice of a downloaded query result CSV.

  Attributes:
    columns: Header row, in file order.
    rows: Up to `max_rows` data rows, each a list of string cell values
      in the same order as `columns`.
    total_rows_previewed: `len(rows)` -- how many data rows are actually
      included below.
    truncated: Whether the CSV has more data rows beyond this preview.
  """

  columns: List[str]
  rows: List[List[str]]
  total_rows_previewed: int
  truncated: bool


def read_preview(csv_path: str, max_rows: int = 20) -> ResultPreview:
  """Reads up to `max_rows` data rows of `csv_path` into a `ResultPreview`.

  Args:
    csv_path: Local path to a downloaded Athena result CSV.
    max_rows: Maximum number of data rows to include (excludes the
      header row).

  Returns:
    A `ResultPreview` of the file's header and first `max_rows` rows.

  Raises:
    ValueError: If `csv_path` has no header row (i.e. is empty).
  """
  with open(csv_path, newline="", encoding="utf-8") as csv_file:
    reader = csv.reader(csv_file)
    try:
      columns = next(reader)
    except StopIteration as exc:
      raise ValueError(f"'{csv_path}' is empty -- no header row.") from exc
    rows: List[List[str]] = []
    truncated = False
    for row in reader:
      if len(rows) >= max_rows:
        truncated = True
        break
      rows.append(row)
  return ResultPreview(
      columns=columns,
      rows=rows,
      total_rows_previewed=len(rows),
      truncated=truncated,
  )
