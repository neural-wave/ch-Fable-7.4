"""Exact money arithmetic on the stored integers: amounts in cents, rates in millionths.

Floats would lose cents on large sums, and the targets count a row only when it is exact to the cent. So every
calculation stays in integers and only the result becomes a `decimal.Decimal` amount.
"""
from decimal import Decimal

import polars as pl

RATE_UNIT = 1_000_000  # rates are stored in millionths: 0.03 is 30000
HALF_UP = 500_000  # half of RATE_UNIT, added before the division to round half up
CENT = Decimal("0.01")


def share(amount: pl.Expr, rate: pl.Expr) -> pl.Expr:
    """`amount` (cents) times `rate` (millionths), in cents rounded half up.

    The product is in units of 1e-8 francs. Adding half a cent and dividing by RATE_UNIT rounds it half up to
    the cent, exactly; the amounts are never negative.
    """
    return amount.mul(rate).add(HALF_UP).floordiv(RATE_UNIT)


def francs(cents: pl.Expr) -> pl.Expr:
    """An amount in cents as an exact decimal with two decimals (1234 -> 12.34).

    Polars multiplies decimals exactly, and the rows of the result are `decimal.Decimal` values.
    """
    return cents.cast(pl.Decimal(38, 0)).mul(CENT)
