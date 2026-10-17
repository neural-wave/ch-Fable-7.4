"""The periods the reports cover: the valuation days of t3 and the statement years of t4.

A policy is valued from its start on. Statements cover every calendar year from the start
to the year the policy ended, or to the last full year before the export.
"""
import conventions as c


def valuation_days(contract, days):
    """The valuation `days` on which the policy exists."""
    return [day for day in days if contract.start <= day]


def statement_years(contract, bookings):
    """The calendar years with a statement."""
    exits = [booking.day.year for booking in bookings if booking.kind in c.EXITS]
    last = min([*exits, contract.end.year, contract.closed.year, c.LAST_STATEMENT_YEAR])
    return range(contract.start.year, last + 1)
