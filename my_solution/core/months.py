"""Month arithmetic of Neuron: whole months, with the day clamped to the end of the month.

Counting months as one number (year x 12 + month) gives the dates of dateutil's
relativedelta at a tenth of its cost: the ledger moves by months more than 600,000 times.
"""
import calendar
import datetime as dt
import functools

import conventions as c


@functools.cache
def length(year, month):
    """Number of days of a month."""
    return calendar.monthrange(year, month)[1]


def number(day):
    """The month of `day` as one number: year x 12 + month - 1."""
    return day.year * c.MONTHS_PER_YEAR + day.month - 1


def add_months(day, months, anchor_day=None):
    """The same day `months` later, clamped to the month end (31 Jan + 1 month = 28 Feb).

    `anchor_day` keeps a schedule on its own day after a short month (28 Feb, then 31 Mar).
    """
    year, month = divmod(number(day) + months, c.MONTHS_PER_YEAR)
    return dt.date(year, month + 1, min(anchor_day or day.day, length(year, month + 1)))


def completed_months(start, day):
    """Whole months from `start` to a `day` on or after it: 31 Jan to 28 Feb is one."""
    months = number(day) - number(start)
    return months - (add_months(start, months) > day)
