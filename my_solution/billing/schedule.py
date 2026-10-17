"""Premium due dates (task t1).

Neuron counts whole premium periods from the anchor of the schedule (anchor.py), with
the day clamped to the month end. Evidence: 15,028 of 15,028 train rows exact.
"""
import itertools

import conventions as c
from billing import anchor
from core import months


def due_dates(policy, after, until):
    """Due dates of a policy in (after, until], none on or after its maturity date."""
    period = c.MONTHS_PER_PERIOD[policy["PH_FREQ"]]
    first = anchor.anchor(policy["PH_BEGDT"], period)
    days = (months.add_months(first, k * period, first.day) for k in itertools.count())
    open_days = itertools.takewhile(lambda day: day <= until and day < policy["PH_ENDDT"], days)
    return [day for day in open_days if day > after]
