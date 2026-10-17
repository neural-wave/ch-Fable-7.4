"""Sharing a charge among the positions of a policy, in proportion to their values.

Each piece is rounded the way of the day and the rounding difference goes to the
position with the largest value; between equal values, to the first by fund and pot
(two halves of a switch, BL10002262 on 2019-12-01). Pieces of zero or less are left
out: a split never books a negative charge, and a split of nothing books nothing.
"""
from core import money


def pieces(total, weights, day):
    """The rounded pieces of `total` over non-empty `weights`."""
    whole = sum(weights.values())
    split = {key: money.cents(total * weight / whole, day) for key, weight in weights.items()}
    split[max(sorted(weights), key=weights.get)] += total - sum(split.values())
    return money.positive(split)


def pro_rata(total, weights, day):
    """{key: piece} of `total` shared in proportion to the positive `weights`."""
    if weights:
        return pieces(total, weights, day)
    return {}
