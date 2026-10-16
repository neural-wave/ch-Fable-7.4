"""All the bookings of a policy: invested premiums, customer orders and monthly charge runs.

The premiums and the orders are known in advance; the charge runs follow on the days of
runs.py, each one on the units traded before its day, until a run finds nothing left.
"""
import bisect
import itertools
import operator

import account
import charges
import investment
import runs

DAY = operator.attrgetter("day")


def charge_runs(export, contract, planned, days):
    """The bookings of each run on `days`, run after run."""
    units, traded, booked = account.Account(export.market, contract.currency), list(map(DAY, planned)), 0
    for day in days:
        cut = bisect.bisect_left(traded, day)
        units.book(planned[booked:cut])
        booked = cut
        run = charges.run(export, contract, units, day)
        units.book(run)
        yield run


def bookings(export, contract):
    """Every booking of a policy, in trade-date order."""
    premiums = investment.bookings(export, contract)
    planned = sorted([*premiums, *export.orders.get(contract.policy_id, [])], key=DAY)
    made = itertools.takewhile(bool, charge_runs(export, contract, planned, runs.run_days(contract, premiums, planned)))
    return sorted([*planned, *itertools.chain.from_iterable(made)], key=DAY)


def ledgers(export):
    """(contract, bookings) of every policy of the export, one policy at a time."""
    for policy_id in export.versions:
        contract = export.contract(policy_id)
        yield contract, bookings(export, contract)
