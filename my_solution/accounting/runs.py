"""The charge runs of a policy: the days on which Neuron charged ADM, AMC and RSK.

A charge run falls on each monthly anniversary of the start date (the day clamped to the
month end) after the first premium was invested, before maturity, before a surrender or
death, and not after the export.
"""
import itertools

import conventions as c
from core import months


def run_days(contract, premiums, planned):
    """The days of the charge runs, given the premium bookings and all planned bookings."""
    first = min((booking.day for booking in premiums), default=c.RUNS_END)
    stop = min([*(booking.day for booking in planned if booking.kind in c.EXITS), contract.end, c.RUNS_END])
    anniversaries = (months.add_months(contract.start, k, contract.start.day) for k in itertools.count(1))
    return [day for day in itertools.takewhile(lambda day: day < stop, anniversaries) if day > first]
