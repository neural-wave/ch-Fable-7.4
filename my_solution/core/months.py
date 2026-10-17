"""Month arithmetic of Neuron: whole months, with the day clamped to the end of the month."""
from dateutil.relativedelta import relativedelta


def add_months(day, months, anchor_day=None):
    """The same day `months` later, clamped to the month end (31 Jan + 1 month = 28 Feb).

    `anchor_day` keeps a schedule on its own day after a short month (28 Feb, then 31 Mar).
    """
    return day + relativedelta(months=months, day=anchor_day)
