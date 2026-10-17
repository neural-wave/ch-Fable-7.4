"""The public holidays of Ticino, the calendar of the direct debits.

In Ticino Good Friday is a working day, while 6 Jan, 19 Mar, Corpus Domini and 29 Jun are
holidays. The calendar is computed offline by the holidays package, for any year.
"""
import functools

import holidays

import conventions as c


@functools.cache
def ticino_holidays(year):
    """Public holidays of the canton of Ticino in `year`."""
    return holidays.country_holidays(c.HOLIDAY_COUNTRY, subdiv=c.HOLIDAY_REGION, years=year)
