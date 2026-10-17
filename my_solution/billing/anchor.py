"""The anchor of a premium schedule: the due date from which Neuron NG counts the periods.

COBOL added each period to the previous due date, so the day drifts (31 Jan, 28 Feb,
28 Mar); Neuron NG counts whole periods from the last due date that COBOL reached
before the switch day, and keeps its day.
"""
import conventions as c
from core import months


def anchor(start, period):
    """The start date, moved period by period under COBOL rules until the switch day."""
    while months.add_months(start, period) < c.ERA_SWITCH:
        start = months.add_months(start, period)
    return start
