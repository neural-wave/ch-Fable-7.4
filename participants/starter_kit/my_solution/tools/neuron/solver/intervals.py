"""Interval reasoning on rounded amounts: every rounded amount bounds the exact value that it comes from.

If 9.45 is round(rate x base) with half-up rounding, the product rate x base lies between 9.445 and 9.455, so the
rate of that row lies in an interval. Intersecting the intervals of a group gives its exact rate, or nothing: a
missing condition, a wrong rounding mode or an outlier. All values are integers: amounts in cents, rates in
millionths, products in cents x millionths.
"""
import z3

from neuron.solver import SCALE

OFFSETS = {  # mode: lowest and highest offset of a product from amount x SCALE that still rounds to the amount
    "half_up": (-500_000, 499_999),  # the half rounds up
    "half_even": (-500_000, 500_000),  # the half-up interval plus the exact halves, which round to the even cent
    "down": (0, 999_999),  # every rest is cut off
    "up": (-999_999, 0),  # every rest adds a cent
}


def bounds(base: int, amount: int, mode: str) -> tuple[int, int]:
    """Smallest and largest product `base x rate` (cents x millionths) that rounds to `amount` cents."""
    low, high = OFFSETS[mode]
    exact = amount * SCALE
    return exact + low, exact + high


def fits(rate, base: int, amount: int, mode: str):
    """Z3 constraint, linear in `rate`: `base x rate` rounds to `amount`."""
    low, high = bounds(base, amount, mode)
    product = base * rate
    return z3.And(product >= low, product <= high)


def keeps(rate: int, base: int, amount: int, mode: str) -> bool:
    """True when the integer `rate` reproduces the pair (base, amount).

    The same test as `fits`, in plain Python, for a rate that Z3 already found.
    """
    low, high = bounds(base, amount, mode)
    return low <= base * rate <= high
