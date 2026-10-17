"""Business days of NeuralWave Life: Monday to Friday, without the public holidays of Ticino.

The holidays are in holiday_calendar.py. A debit due on a weekend or a holiday is
collected on the next business day.
"""
import datetime as dt

import conventions as c
from billing import holiday_calendar


def is_business_day(day):
    """Monday to Friday and not a Ticino public holiday."""
    return day.weekday() < c.SATURDAY and day not in holiday_calendar.ticino_holidays(day.year)


def next_business_day(day):
    """`day` if it is a business day, otherwise the first business day after it.

    Neuron only moves forward, also into the next month: 31 Oct 2026 is collected on 2 Nov.
    """
    while not is_business_day(day):
        day += dt.timedelta(days=1)
    return day
