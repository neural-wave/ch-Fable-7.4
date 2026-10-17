"""Business days of NeuralWave Life: Monday to Friday, without the public holidays of Ticino.

In Ticino Good Friday is a working day, while 6 Jan, 19 Mar, Corpus Domini and 29 Jun are
holidays. The calendar is computed offline by the holidays package, for any year.
"""
import datetime as dt
import functools

import holidays

import conventions as c


@functools.cache
def ticino_holidays(year):
    """Public holidays of the canton of Ticino in `year`."""
    return holidays.country_holidays(c.HOLIDAY_COUNTRY, subdiv=c.HOLIDAY_REGION, years=year)


def is_business_day(day):
    """Monday to Friday and not a Ticino public holiday."""
    return day.weekday() < c.SATURDAY and day not in ticino_holidays(day.year)


def next_business_day(day):
    """`day` if it is a business day, otherwise the first business day after it.

    Neuron only moves forward, also into the next month: 31 Oct 2026 is collected on 2 Nov.
    """
    while not is_business_day(day):
        day += dt.timedelta(days=1)
    return day
