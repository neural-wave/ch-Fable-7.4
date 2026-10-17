"""Exact money arithmetic on the stored integers: amounts in cents, rates in millionths.

The targets count a value only when it is exact to the cent, so everything stays in integers and only the result
becomes a `decimal.Decimal`.
"""
import polars as pl

RATE_UNIT = 1_000_000  # rates are stored with 6 decimals: 0.03 is 30000
CENT = "0.01"


def expression(value) -> pl.Expr:
    """`value` as an expression: a literal unless it is one already."""
    return value if isinstance(value, pl.Expr) else pl.lit(value)


def rounded(numerator: pl.Expr, denominator: int | pl.Expr, half_up: bool | pl.Expr) -> pl.Expr:
    """`numerator / denominator` as an integer: half up, or cut off where `half_up` is false (a flag or a boolean
    column)."""
    half = expression(denominator).floordiv(2).mul(expression(half_up).cast(pl.Int64))
    return numerator.add(half).floordiv(expression(denominator))


def share(amount: pl.Expr, rate: pl.Expr, half_up: bool = True) -> pl.Expr:
    """`amount` (cents) times `rate` (millionths), in cents."""
    return rounded(amount.mul(rate), RATE_UNIT, half_up)


def francs(cents: pl.Expr) -> pl.Expr:
    """An amount in cents as an exact decimal with two decimals (1234 -> 12.34)."""
    return cents.cast(pl.Decimal(38, 0)).mul(pl.lit(CENT).cast(pl.Decimal(38, 2)))
