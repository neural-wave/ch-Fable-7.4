"""The arithmetic of the taxes: a rate levied on an amount, and the gains the taxes are levied on."""
from decimal import Decimal

ZERO = Decimal(0)
VST_ALLOWANCE = Decimal(5000)  # CH: the part of a payout free of withholding tax when NRTAXR has no threshold


def levy(rate, amount, otherwise=ZERO):
    """`rate` x `amount`; `otherwise` when there is no rate (None)."""
    return otherwise if rate is None else rate * amount


def taxable_gain(payout, fund_value, premiums):
    """The gain in a payout, at least 0.

    When the fund has grown above the premiums: payout x (fund value - premiums) / fund value, the share of
    the gain in the fund. Otherwise: the payout less the premiums.
    """
    if fund_value > premiums and premiums > 0:
        return payout * ((fund_value - premiums) / fund_value)
    return max(ZERO, payout - premiums)


def fund_growth(value_and_premiums):
    """The fund value less the premiums, at least 0, of a (fund value, premiums) pair."""
    value, premiums = value_and_premiums
    return max(ZERO, value - premiums)


def above_allowance(payout, threshold):
    """The part of a CH payout subject to VST.

    The payout above the allowance, at least 0. The allowance is the NRTAXR threshold / 100, or VST_ALLOWANCE
    when the row has no threshold.
    """
    allowance = threshold / 100 if threshold else VST_ALLOWANCE
    return max(ZERO, payout - allowance)
