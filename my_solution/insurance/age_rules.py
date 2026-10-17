"""The two rules that fixed the insurance age on the start date of a policy.

COBOL divided the days lived by 365 and rounded to the nearest year: the 29 Februaries do
not count, so of two persons with the same birthday the older one can be a year older.
365 is odd, so a half year never falls on a whole day and the rounding has no tie.
Neuron NG counts the completed months (a month is complete on the day of the birthday)
and rounds to the nearest year, half a year up. Both rules are exact on every risk charge
of the train policies. The age of a policy is fixed once, so each rule remembers it.
"""
import datetime as dt
import functools

import conventions as c


@functools.cache
def cobol(birth, start):
    """Age by the days lived; 30 Feb counts as 2 Mar."""
    year, month, day = birth
    return round(((start - dt.date(year, month, 1)).days - day + 1) / c.DAYS_PER_YEAR)


@functools.cache
def neuron_ng(birth, start):
    """Age by the completed months."""
    year, month, day = birth
    completed = (start.year - year) * c.MONTHS_PER_YEAR + start.month - month - (start.day < day)
    return (completed + c.HALF_YEAR) // c.MONTHS_PER_YEAR
