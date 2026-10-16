"""Premium due dates (task t1).

Neuron counts whole premium periods from an anchor, with the day clamped to the month end.
COBOL added each period to the previous due date (31 Jan, 28 Feb, 28 Mar: the day drifts),
Neuron NG keeps the anchor day. Evidence: 15,028 of 15,028 train rows exact.
"""
import itertools

import conventions as c
import months


def anchor(start, period):
    """The due date from which Neuron NG counts whole periods.

    It is the start date, moved period by period under COBOL rules until the switch day.
    """
    while months.add_months(start, period) < c.ERA_SWITCH:
        start = months.add_months(start, period)
    return start


def due_dates(policy, after, until):
    """Due dates of a policy in (after, until], none on or after its maturity date."""
    period = c.MONTHS_PER_PERIOD[policy["PH_FREQ"]]
    first = anchor(policy["PH_BEGDT"], period)
    days = (months.add_months(first, k * period, first.day) for k in itertools.count())
    open_days = itertools.takewhile(lambda day: day <= until and day < policy["PH_ENDDT"], days)
    return [day for day in open_days if day > after]
