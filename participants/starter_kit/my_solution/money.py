"""Exact money arithmetic on the stored integers: amounts in cents, rates in millionths.

Floats would lose cents on large sums, and the targets count a row only when it is exact to the cent. So every
calculation stays in integers and only the result becomes a `decimal.Decimal` amount. The one exception is the
monthly growth of the projection (`grown`): Neuron multiplies with a rounded growth factor in decimal arithmetic of
28 significant digits, and only the same arithmetic gives the same cents.
"""
import decimal
import functools
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal

import polars as pl

RATE_UNIT = 1_000_000  # rates are stored in millionths: 0.03 is 30000
MONTHLY_UNIT = 12_000_000  # a yearly rate in millionths taken every month: amount x rate / 12 / RATE_UNIT
CENT = Decimal("0.01")
ONE = Decimal(1)
DECIMAL = decimal.Context(prec=28)  # the decimal arithmetic of the projection: 28 significant digits per result
ROUNDING = {True: ROUND_HALF_UP, False: ROUND_DOWN}  # half_up -> how a decimal amount is rounded to the cent


def rounded(numerator: pl.Expr, denominator, half_up: pl.Expr) -> pl.Expr:
    """`numerator / denominator` as an integer: rounded half up where `half_up` is true, else truncated.

    The integer division cuts off the rest; adding half the denominator first rounds half up instead. Both are
    exact, since numerator and denominator are integers and the numerators are never negative.
    """
    half = pl.when(half_up).then(pl.lit(denominator).floordiv(2)).otherwise(0)
    return numerator.add(half).floordiv(denominator)


def share(amount: pl.Expr, rate: pl.Expr) -> pl.Expr:
    """`amount` (cents) times `rate` (millionths), in cents rounded half up.

    The product is in units of 1e-8 francs, and dividing it by RATE_UNIT gives cents.
    """
    return rounded(amount.mul(rate), RATE_UNIT, half_up=pl.lit(True))


def monthly_share(amount: pl.Expr, yearly_rate: pl.Expr, half_up: pl.Expr) -> pl.Expr:
    """The part of `amount` (cents) that a yearly `rate` (millionths) takes in one month, in cents.

    A twelfth of the yearly rate, rounded half up or truncated as `half_up` says.
    """
    return rounded(amount.mul(yearly_rate), MONTHLY_UNIT, half_up)


def francs(cents: pl.Expr) -> pl.Expr:
    """An amount in cents as an exact decimal with two decimals (1234 -> 12.34).

    Polars multiplies decimals exactly, and the rows of the result are `decimal.Decimal` values.
    """
    return cents.cast(pl.Decimal(38, 0)).mul(CENT)


@functools.cache
def growth_factor(yearly_rate: int) -> Decimal:
    """1 + a twelfth of `yearly_rate` (millionths) with 28 significant digits, e.g. 1.003333333333333333333333333."""
    return DECIMAL.add(ONE, DECIMAL.divide(yearly_rate, MONTHLY_UNIT))


def grown(cents: int, yearly_rate: int, half_up: bool) -> int:
    """`cents` after a month of growth at `yearly_rate` (millionths), rounded to the cent as `half_up` says.

    The growth factor and the product keep 28 significant digits. The factor of 4 % is a bit less than the exact
    1 + 1/300, so a product that would end on exactly half a cent (or a whole cent, when truncating) may land just
    below it; the 28 digits round it back only when that error is small enough. The targets follow this to the
    cent, and the exact fraction does not.
    """
    product = DECIMAL.multiply(cents, growth_factor(yearly_rate))
    return int(product.quantize(ONE, rounding=ROUNDING[half_up]))


def monthly_growth(value: pl.Expr, yearly_rate: pl.Expr, half_up: pl.Expr) -> pl.Expr:
    """`value` (cents) after a month of growth at `yearly_rate`, row by row with `grown`."""
    return pl.struct(value, yearly_rate, half_up).map_batches(
        lambda rows: pl.Series([grown(*row) for row in rows.struct.unnest().iter_rows()], dtype=pl.Int64),
        return_dtype=pl.Int64)
