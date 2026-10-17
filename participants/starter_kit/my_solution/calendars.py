"""Business days: the days that are neither a weekend nor a holiday of a calendar.

A calendar is named like the holidays it keeps: "TI" those of canton Ticino, "CH" the Swiss national ones,
anything else none (weekends only).
"""
import datetime as dt
import functools

import holidays
import polars as pl

WEEKEND = 6  # ISO weekday of Saturday
COUNTRY = "CH"


def free_days(calendar: str, years: range) -> list[dt.date]:
    """The holidays of `calendar` in `years`."""
    match calendar:
        case "CH":
            return list(holidays.country_holidays(COUNTRY, years=years))
        case "TI":
            return list(holidays.country_holidays(COUNTRY, subdiv=calendar, years=years))
    return []


@functools.cache
def business_days(calendar: str, years: range) -> pl.DataFrame:
    """DAY, NEXT and AFTER: every day of `years` (and January after them), the first business day on or after it
    and the first one after it."""
    last = dt.date(years.stop, 1, 31)
    days = pl.DataFrame({"DAY": pl.date_range(dt.date(years.start, 1, 1), last, eager=True)})
    working = pl.col("DAY").dt.weekday().lt(WEEKEND).and_(pl.col("DAY").is_in(free_days(calendar, years)).not_())
    following = days.with_columns(NEXT=pl.when(working).then(pl.col("DAY")).backward_fill())
    return following.with_columns(AFTER=pl.col("NEXT").shift(pl.lit(1).neg()))  # NEXT of the following day
