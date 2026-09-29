"""Tests for athena_mcp.result_preview."""

import pytest

from athena_mcp import result_preview


def _write_csv(tmp_path, rows):
  path = tmp_path / "result.csv"
  path.write_text("\n".join(",".join(row) for row in rows) + "\n")
  return str(path)


def test_read_preview_returns_all_rows_when_under_max(tmp_path):
  csv_path = _write_csv(tmp_path, [
      ["sessionId", "playback_outcome"],
      ["s1", "OK"],
      ["s2", "EBVS"],
  ])

  preview = result_preview.read_preview(csv_path, max_rows=20)

  assert preview.columns == ["sessionId", "playback_outcome"]
  assert preview.rows == [["s1", "OK"], ["s2", "EBVS"]]
  assert preview.total_rows_previewed == 2
  assert preview.truncated is False


def test_read_preview_truncates_at_max_rows(tmp_path):
  rows = [["sessionId"]] + [[f"s{i}"] for i in range(5)]
  csv_path = _write_csv(tmp_path, rows)

  preview = result_preview.read_preview(csv_path, max_rows=3)

  assert preview.rows == [["s0"], ["s1"], ["s2"]]
  assert preview.total_rows_previewed == 3
  assert preview.truncated is True


def test_read_preview_raises_value_error_on_empty_file(tmp_path):
  csv_path = tmp_path / "empty.csv"
  csv_path.write_text("")

  with pytest.raises(ValueError, match="empty"):
    result_preview.read_preview(str(csv_path))


def test_read_preview_handles_header_only_file(tmp_path):
  csv_path = _write_csv(tmp_path, [["sessionId", "playback_outcome"]])

  preview = result_preview.read_preview(csv_path)

  assert preview.columns == ["sessionId", "playback_outcome"]
  assert not preview.rows
  assert preview.total_rows_previewed == 0
  assert preview.truncated is False
