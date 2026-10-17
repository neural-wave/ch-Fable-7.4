"""The amounts of the charges: the entry charge of a premium and the management fee, and the pots."""
from decimal import ROUND_DOWN

from neuron import add_months, cents, era_rounding, is_cobol, months_between


def net_premium(amount, allocation_share, entry_rate, day_):
    """(net amount, entry charge) of the share of a premium that goes to one fund.

    The net amount is rounded, and the entry charge is the rest, so the rounding goes to the charge.
    """
    gross = amount * allocation_share
    net = cents(gross * (1 - entry_rate), era_rounding(day_))
    return net, gross - net


def management_fee(value, rate, start, day_):
    """The monthly management charge of a value at a yearly rate.

    Neuron NG charges a twelfth of the rate. The COBOL version charged the days since the same day of the month
    before (the monthiversary of the begin date) / 360, with the cents cut off.
    """
    if is_cobol(day_):
        last_month = add_months(start, months_between(start, day_) - 1)
        return cents(value * rate * (day_ - last_month).days / 360, ROUND_DOWN)
    return cents(value * rate / 12)


def pot(received, initial_end):
    """The pot of the units a premium buys: "1" (initial units) for the money received before `initial_end`."""
    return "1" if received < initial_end else "2"

