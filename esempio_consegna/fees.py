"""Annual management charge (AMC): the yearly rate, charged month by month on a value.

COBOL charged it by the day, ACT/360 since the previous run; Neuron NG charges a twelfth
of the yearly rate. Neuron multiplies before it divides, then rounds the way of the day.
"""
import conventions as c
import money
import months


def period(start, day):
    """(days, basis) of the share of the yearly AMC rate charged by the run on `day`."""
    if day < c.ERA_SWITCH:
        return (day - months.add_months(day, -1, start.day)).days, c.AMC_DAY_BASIS
    return 1, c.MONTHS_PER_YEAR


def amc(value, rate, share, basis, day):
    """The AMC on a `value` at a yearly `rate`, for `share` / `basis` of a year."""
    return money.cents(value * rate * share / basis, day)
