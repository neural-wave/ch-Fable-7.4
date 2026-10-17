"""Exact decimal arithmetic on whole columns: values as Int128 counts of 10^-scale, rounding in every mode.

`scaled(col, s)` turns a Decimal (or Int) column into an Int128 of units 10^-s; `round_to(n, scale_in, scale_out,
mode)` rounds such integers like `decimal.Decimal.quantize` with the same rounding names, so a whole column is
checked against a target in one vectorized step instead of 200 000 Decimal operations.
"""
from decimal import Decimal

import polars as pl

MODES = ("ROUND_HALF_UP", "ROUND_HALF_EVEN", "ROUND_HALF_DOWN", "ROUND_DOWN", "ROUND_UP", "ROUND_FLOOR",
         "ROUND_CEILING")


def scaled(expr, scale):
    """Decimal/Int expression -> Int128 count of 10^-scale (exact when the column has at most `scale` decimals)."""
    return (expr.cast(pl.Decimal(38, scale)) * pl.lit(10 ** scale, dtype=pl.Decimal(38, 0))).cast(pl.Int128)


def constant(value):
    """Decimal constant -> (integer, scale), e.g. 0.040 -> (4, 2)."""
    value = Decimal(str(value)).normalize()
    exponent = max(0, -value.as_tuple().exponent)
    return int(value.scaleb(exponent)), exponent


def round_to(n, scale_in, scale_out, mode):
    """Round Int128 `n` (units 10^-scale_in) to units 10^-scale_out with a `decimal` rounding mode."""
    if scale_in <= scale_out:
        return n * (10 ** (scale_out - scale_in))
    d = pl.lit(10 ** (scale_in - scale_out), dtype=pl.Int128)
    q, rem = n.floordiv(d), n - n.floordiv(d) * d  # floor division: rem >= 0
    up, neg = (rem > 0).cast(pl.Int128), n < 0
    twice = rem * 2
    if mode == "ROUND_FLOOR":
        return q
    if mode == "ROUND_CEILING":
        return q + up
    if mode == "ROUND_DOWN":
        return pl.when(neg).then(q + up).otherwise(q)
    if mode == "ROUND_UP":
        return pl.when(neg).then(q).otherwise(q + up)
    above, tie = (twice > d).cast(pl.Int128), (twice == d).cast(pl.Int128)
    if mode == "ROUND_HALF_UP":
        return pl.when(neg).then(q + above).otherwise(q + above + tie)
    if mode == "ROUND_HALF_DOWN":
        return pl.when(neg).then(q + above + tie).otherwise(q + above)
    if mode == "ROUND_HALF_EVEN":
        return q + above + tie * (q % 2).abs()
    raise ValueError(mode)
