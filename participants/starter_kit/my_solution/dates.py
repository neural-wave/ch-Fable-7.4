"""The calendar of Neuron: schedules of whole months and the business days of the local calendar.

Neuron NG (Java) computes a schedule as its first date plus whole periods: a day 31 becomes the last day of a
shorter month and comes back in the next long one (31 Jan -> 28 Feb -> 31 Mar). Business days are the weekdays
that are no public holiday in canton Ticino (`conventions.CALENDAR`).
"""
import functools

import holidays
import polars as pl

from conventions import CALENDAR


def completed_months(start: pl.Expr, end: pl.Expr) -> pl.Expr:
    """The whole months from `start` to `end`: a month is complete when `end` reaches the day of `start` again."""
    months = end.dt.year().sub(start.dt.year()).mul(12).add(end.dt.month()).sub(start.dt.month())
    return months.sub(end.dt.day().lt(start.dt.day()).cast(pl.Int32))


def completed_years(start: pl.Expr, end: pl.Expr) -> pl.Expr:
    """The whole years from `start` to `end`: a year is complete on the anniversary, `start` plus whole years.

    As in Java, the anniversary of 29 February is 28 February in the years without a leap day.
    """
    years = end.dt.year().sub(start.dt.year())
    anniversary = start.dt.offset_by(pl.format("{}y", years))
    return years.sub(anniversary.gt(end).cast(pl.Int32))


def month_days(start: pl.Expr, day: pl.Expr) -> pl.Expr:
    """The days of the month of the schedule `start` plus whole months that ends on the monthly date of `day`.

    The monthly date is `start` plus the months from the month of `start` to the month of `day`.
    """
    months = day.dt.year().sub(start.dt.year()).mul(12).add(day.dt.month()).sub(start.dt.month())
    ends = start.dt.offset_by(pl.format("{}mo", months))
    return days_between(start.dt.offset_by(pl.format("{}mo", months.sub(1))), ends)


def days_between(start: pl.Expr, end: pl.Expr) -> pl.Expr:
    """The number of days from `start` to `end`."""
    return end.sub(start).dt.total_days()


def every_months(start: str, end: str, months: int) -> pl.Expr:
    """List of the dates from the column `start` every `months` months, before the column `end` (excluded).

    Every date is `start` plus whole periods, so a short month does not move the dates after it.
    """
    return pl.date_ranges(start, end, interval=f"{months}mo", closed="left")


@functools.cache
def public_holidays() -> list:
    """The public holidays of the local calendar, generated offline by the library `holidays`."""
    return sorted(holidays.country_holidays(**CALENDAR))


def business_day(day: pl.Expr) -> pl.Expr:
    """`day` itself when it is a business day, else the next business day after weekends and holidays."""
    return day.dt.add_business_days(0, holidays=public_holidays(), roll="forward")
