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

RATE_UNIT = 1_000_000  # rates are stored in millionths: 0.03 is 30000; so are units, prices and exchange rates
VALUE_UNIT = 10_000_000_000  # units x price, both in millionths, per cent: 1e12 / 100
MONTHLY_UNIT = 12_000_000  # a yearly rate in millionths taken every month: amount x rate / 12 / RATE_UNIT
CENT = Decimal("0.01")
ONE = Decimal(1)
DECIMAL = decimal.Context(prec=28)  # the decimal arithmetic of the projection: 28 significant digits per result
ROUNDING = {True: ROUND_HALF_UP, False: ROUND_DOWN}  # half_up -> how a decimal amount is rounded to the cent


def rounded(numerator: pl.Expr, denominator, half_up: pl.Expr) -> pl.Expr:
    """`numerator / denominator` as an integer: rounded half up where `half_up` is true, else truncated.

    The integer division cuts off the rest; adding half the denominator first rounds half up instead. Both are
    exact, since numerator and denominator are integers and the numerators are never negative. The denominator
    is a number or an expression; both halves keep its integer type (zero is the denominator times 0).
    """
    divisor = denominator if isinstance(denominator, pl.Expr) else pl.lit(denominator)
    half = pl.when(half_up).then(divisor.floordiv(2)).otherwise(divisor.mul(0))
    return numerator.add(half).floordiv(divisor)


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


def value_of(units: pl.Expr, price: pl.Expr, half_up: pl.Expr) -> pl.Expr:
    """The value in cents of the policy currency of `units` at `price` of the fund (`market`: x RF / RP)."""
    worth = units.cast(pl.Int128).mul(price).mul(pl.col("RF"))
    return rounded(worth, pl.col("RP").mul(VALUE_UNIT), half_up).cast(pl.Int64)


def units_for(amount: pl.Expr, price: pl.Expr, half_up: pl.Expr) -> pl.Expr:
    """The units (millionths) that `amount` in cents of the policy currency is worth at `price` (x RP / RF)."""
    worth = amount.cast(pl.Int128).mul(pl.col("RP")).mul(VALUE_UNIT)
    return rounded(worth, pl.col("RF").mul(price), half_up).cast(pl.Int64)


def allotted(frame: pl.DataFrame, column: str, weight: str, group: str, half_up: pl.Expr) -> pl.DataFrame:
    """`frame` with `column`, a total that is the same in every row of `group`, split over those rows by `weight`.

    Every share is rounded as `half_up` says, and the cents that the rounding leaves over or takes too many go
    to the row with the largest weight: on a tie the first one, so the rows come sorted by fund and pot.
    """
    weights = frame.with_columns(WEIGHTS=pl.col(weight).sum().over(group),
                                 LARGEST=pl.col(weight).rank("ordinal", descending=True).over(group).eq(1))
    shares = weights.with_columns(SHARE=rounded(pl.col(column).mul(pl.col(weight)), pl.col("WEIGHTS"), half_up))
    rest = pl.col(column).sub(pl.col("SHARE").sum().over(group))
    allotted_shares = pl.col("SHARE").add(pl.when("LARGEST").then(rest).otherwise(0))
    return shares.with_columns(allotted_shares.alias(column)).drop("WEIGHTS", "LARGEST", "SHARE")


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
