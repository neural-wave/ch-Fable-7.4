"""Units moved by a trade, rounded to 6 decimals the way of the trade day.

A charge takes amount x cross rate / bid units out of a position; a premium buys
amount x cross rate / ask units, at the cross rate of the day before the trade.
"""
import conversion
import money


def taken(market, currency, fund, amount, day):
    """The units, negative, that a charge of `amount` takes out of a fund on `day`."""
    return -money.units(amount * conversion.cross(market, currency, fund, day) / market.bid(fund, day), day)


def bought(market, currency, fund, amount, day):
    """The units of a fund that a premium `amount` buys on its trade day `day`."""
    return money.units(amount * conversion.cross(market, currency, fund, day, before=True) / market.ask(fund, day), day)
