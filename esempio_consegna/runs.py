"""The calendar of a policy: its charge runs, valuation days and statement years.

A charge run falls on each monthly anniversary of the start date (the day clamped to the
month end) after the first premium was invested, before maturity, before a surrender or
death, and not after the export. A policy is valued from its start on. Statements cover
every calendar year from the start to the year the policy ended, or to the last full year
before the export.
"""
import itertools

import conventions as c
import months


def run_days(contract, premiums, planned):
    """The days of the charge runs, given the premium bookings and all planned bookings."""
    first = min((booking.day for booking in premiums), default=c.RUNS_END)
    stop = min([*(booking.day for booking in planned if booking.kind in c.EXITS), contract.end, c.RUNS_END])
    anniversaries = (months.add_months(contract.start, k, contract.start.day) for k in itertools.count(1))
    return [day for day in itertools.takewhile(lambda day: day < stop, anniversaries) if day > first]


def valuation_days(contract, days):
    """The valuation `days` on which the policy exists."""
    return [day for day in days if contract.start <= day]


def statement_years(contract, bookings):
    """The calendar years with a statement."""
    exits = [booking.day.year for booking in bookings if booking.kind in c.EXITS]
    last = min([*exits, contract.end.year, contract.closed.year, c.LAST_STATEMENT_YEAR])
    return range(contract.start.year, last + 1)
