"""Tests for athena_runner.date_utils."""

import pytest

from athena_runner import date_utils


def test_validate_iso_date_returns_value_when_valid():
  assert date_utils.validate_iso_date("2026-09-01", "--date") == "2026-09-01"


def test_validate_iso_date_raises_value_error_when_invalid():
  with pytest.raises(ValueError, match="--date must be YYYY-MM-DD"):
    date_utils.validate_iso_date("09-01-2026", "--date")


def test_add_days_advances_within_month():
  assert date_utils.add_days("2026-08-01", 1) == "2026-08-02"


def test_add_days_rolls_over_month_end():
  assert date_utils.add_days("2026-08-31", 1) == "2026-09-01"


def test_add_days_supports_negative_offset():
  assert date_utils.add_days("2026-09-01", -1) == "2026-08-31"


def test_month_bounds_returns_first_and_last_day():
  assert date_utils.month_bounds("2026-09") == ("2026-09-01", "2026-09-30")


def test_month_bounds_handles_leap_february():
  assert date_utils.month_bounds("2028-02") == ("2028-02-01", "2028-02-29")


def test_month_bounds_raises_value_error_when_invalid():
  with pytest.raises(ValueError, match="--month must be YYYY-MM"):
    date_utils.month_bounds("2026-13")


def test_week_bounds_returns_monday_and_sunday():
  assert date_utils.week_bounds("2026-09-09") == ("2026-09-07", "2026-09-13")


def test_week_bounds_when_date_is_monday():
  assert date_utils.week_bounds("2026-09-07") == ("2026-09-07", "2026-09-13")


def test_week_bounds_when_date_is_sunday():
  assert date_utils.week_bounds("2026-09-13") == ("2026-09-07", "2026-09-13")


def test_week_bounds_rolls_over_month_end():
  assert date_utils.week_bounds("2026-08-31") == ("2026-08-31", "2026-09-06")


def test_week_bounds_raises_value_error_when_invalid():
  with pytest.raises(ValueError, match="--week must be YYYY-MM-DD"):
    date_utils.week_bounds("2026-13-01")


def test_resolve_date_range_with_date_returns_single_day_range():
  assert (
      date_utils.resolve_date_range(date="2026-09-01")
      == ("2026-09-01", "2026-09-01"))


def test_resolve_date_range_with_start_and_end_date():
  assert (
      date_utils.resolve_date_range(
          start_date="2026-09-01", end_date="2026-09-05")
      == ("2026-09-01", "2026-09-05"))


def test_resolve_date_range_with_month():
  assert (
      date_utils.resolve_date_range(month="2026-09")
      == ("2026-09-01", "2026-09-30"))


def test_resolve_date_range_with_week():
  assert (
      date_utils.resolve_date_range(week="2026-09-09")
      == ("2026-09-07", "2026-09-13"))


def test_resolve_date_range_with_week_on_monday():
  assert (
      date_utils.resolve_date_range(week="2026-09-07")
      == ("2026-09-07", "2026-09-13"))


def test_resolve_date_range_raises_when_week_conflicts_with_date():
  with pytest.raises(ValueError, match="only one of"):
    date_utils.resolve_date_range(date="2026-09-01", week="2026-09-01")


def test_resolve_date_range_raises_when_week_is_invalid():
  with pytest.raises(ValueError, match="--week must be YYYY-MM-DD"):
    date_utils.resolve_date_range(week="not-a-date")


def test_resolve_date_range_raises_when_nothing_given():
  with pytest.raises(ValueError, match="Must specify one of"):
    date_utils.resolve_date_range()


def test_resolve_date_range_raises_when_conflicting_flags_given():
  with pytest.raises(ValueError, match="only one of"):
    date_utils.resolve_date_range(
        date="2026-09-01", start_date="2026-09-01", end_date="2026-09-02")


def test_resolve_date_range_raises_when_only_start_date_given():
  with pytest.raises(ValueError, match="must be given together"):
    date_utils.resolve_date_range(start_date="2026-09-01")


def test_resolve_date_range_raises_when_end_date_before_start_date():
  with pytest.raises(ValueError, match="must not be before"):
    date_utils.resolve_date_range(
        start_date="2026-09-05", end_date="2026-09-01")
