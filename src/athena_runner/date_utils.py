"""Shared date-validation helper used by both query params and adoption
metrics, so the YYYY-MM-DD format check has a single implementation.
"""

import calendar
import datetime


def add_days(date: str, days: int) -> str:
  """Returns `date` (YYYY-MM-DD) shifted by `days` days, same format.

  Args:
    date: A valid YYYY-MM-DD date string.
    days: Number of days to add (may be negative).

  Returns:
    The shifted date, formatted as YYYY-MM-DD.

  Raises:
    ValueError: If `date` is not a valid YYYY-MM-DD date.
  """
  parsed = datetime.datetime.strptime(date, "%Y-%m-%d")
  shifted = parsed + datetime.timedelta(days=days)
  return shifted.strftime("%Y-%m-%d")


def validate_iso_date(value: str, label: str) -> str:
  """Validates `value` is a YYYY-MM-DD date string.

  Args:
    value: The date string to validate.
    label: Human-readable name of the field, used in the error message
      (e.g. '--param date' or '--date').

  Returns:
    `value`, unchanged, if valid.

  Raises:
    ValueError: If `value` is not a valid YYYY-MM-DD date.
  """
  try:
    datetime.datetime.strptime(value, "%Y-%m-%d")
  except ValueError as exc:
    raise ValueError(f"{label} must be YYYY-MM-DD, got '{value}'") from exc
  return value


def month_bounds(month: str) -> tuple[str, str]:
  """Returns the first and last YYYY-MM-DD dates of `month` (YYYY-MM).

  Args:
    month: A YYYY-MM string, e.g. '2026-09'.

  Returns:
    A `(first_day, last_day)` tuple, each YYYY-MM-DD.

  Raises:
    ValueError: If `month` is not a valid YYYY-MM string.
  """
  try:
    parsed = datetime.datetime.strptime(month, "%Y-%m")
  except ValueError as exc:
    raise ValueError(f"--month must be YYYY-MM, got '{month}'") from exc
  last_day_num = calendar.monthrange(parsed.year, parsed.month)[1]
  first_day = parsed.strftime("%Y-%m-01")
  last_day = parsed.replace(day=last_day_num).strftime("%Y-%m-%d")
  return first_day, last_day


def week_bounds(date: str) -> tuple[str, str]:
  """Returns the ISO week's Monday and Sunday YYYY-MM-DD dates for `date`.

  Args:
    date: A YYYY-MM-DD date string; any day within the target ISO week.

  Returns:
    A `(week_start, week_end)` tuple, each YYYY-MM-DD, where `week_start`
    is the Monday and `week_end` is the Sunday of `date`'s ISO week.

  Raises:
    ValueError: If `date` is not a valid YYYY-MM-DD date.
  """
  try:
    parsed = datetime.datetime.strptime(date, "%Y-%m-%d")
  except ValueError as exc:
    raise ValueError(f"--week must be YYYY-MM-DD, got '{date}'") from exc
  week_start = parsed - datetime.timedelta(days=parsed.weekday())
  week_end = week_start + datetime.timedelta(days=6)
  return week_start.strftime("%Y-%m-%d"), week_end.strftime("%Y-%m-%d")


def resolve_date_range(
    date: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    month: str | None = None,
    week: str | None = None,
) -> tuple[str, str]:
  """Resolves the `--date`/`--start-date`+`--end-date`/`--month`/`--week`
  CLI flags.

  Exactly one of the following must be given:
  - `date`: shorthand for `start_date=end_date=date`.
  - `start_date` and `end_date` together: an explicit inclusive range.
  - `month`: shorthand for the full calendar month's range.
  - `week`: an anchor YYYY-MM-DD date; shorthand for the Monday..Sunday
    bounds of that date's ISO week (see `week_bounds()`).

  Args:
    date: Value of `--date`, if given.
    start_date: Value of `--start-date`, if given.
    end_date: Value of `--end-date`, if given.
    month: Value of `--month`, if given.
    week: Value of `--week`, if given (an anchor date within the target
      ISO week, e.g. '2026-09-01').

  Returns:
    A validated `(start_date, end_date)` tuple, each YYYY-MM-DD.

  Raises:
    ValueError: If the flags are missing, conflicting, or invalid.
  """
  selected = [
      name for name, value in (
          ("--date", date), ("--start-date/--end-date",
                              start_date or end_date), ("--month", month),
          ("--week", week))
      if value]
  if not selected:
    raise ValueError(
        "Must specify one of --date, --start-date/--end-date, --month, "
        "or --week")
  if len(selected) > 1:
    raise ValueError(
        f"Specify only one of --date, --start-date/--end-date, --month, "
        f"or --week; got {' and '.join(selected)}")

  if date:
    validate_iso_date(date, "--date")
    return date, date

  if month:
    return month_bounds(month)

  if week:
    validate_iso_date(week, "--week")
    return week_bounds(week)

  if not start_date or not end_date:
    raise ValueError("--start-date and --end-date must be given together")
  validate_iso_date(start_date, "--start-date")
  validate_iso_date(end_date, "--end-date")
  if end_date < start_date:
    raise ValueError(
        f"--end-date ({end_date}) must not be before --start-date "
        f"({start_date})")
  return start_date, end_date
