"""Value of fund units in the policy currency, at the bid price and exchange rates of a day.

Neuron converts through CHF: one unit of the policy currency is worth so many units of the
fund currency, the cross rate, kept unrounded. A position is worth units x bid / cross
rate, rounded to the cent the way of the day.
"""
import functools

from core import money


@functools.cache
def cross(market, currency, fund, day, before=False):
    """Units of the fund's currency for one unit of `currency` on `day` (or the day before)."""
    return market.chf(currency, day, before) / market.chf(market.currency[fund], day, before)


def worth(market, currency, fund, units, day):
    """Value of `units` of a fund on `day`, in the policy currency."""
    return money.cents(units * market.bid(fund, day) / cross(market, currency, fund, day), day)
