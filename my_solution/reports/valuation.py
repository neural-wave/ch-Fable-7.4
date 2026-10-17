"""Policy value and surrender value on the valuation dates (task t3).

The policy value is the sum of the positions on that day, the units traded on the day
included, each valued at the bid price in the policy currency and rounded the way of the
day. The surrender value takes off the penalty of the product's scale (NRSURR, by completed
policy years); there is no penalty inside the waiver periods of NRWAIV (surrender.py).
"""
import bisect

from accounting import account
from core import lookup
from insurance import ages
from reports import periods, surrender


def penalty(export, contract, day):
    """Share of the policy value kept on a surrender on `day`."""
    if lookup.valid_rows(export.waivers, day, "WV_VLDFR", "WV_VLDTO"):
        return 0
    return export.surrender_rates.get((contract.scale, ages.policy_years(contract.start, day)), 0)


def surrender_values(export, contract, bookings, days):
    """{day: surrender value} on the valuation `days` from the start of the policy on.

    One account follows the bookings day after day, as the ledger does: each valuation
    day adds only the bookings traded since the one before.
    """
    traded, held, booked = [booking.day for booking in bookings], account.Account(export.market, contract.currency), 0
    values = {}
    for day in sorted(periods.valuation_days(contract, days)):
        cut = bisect.bisect_right(traded, day)
        held.book(bookings[booked:cut])
        booked = cut
        values[day] = surrender.value(held.total(day), penalty(export, contract, day), day)
    return values
