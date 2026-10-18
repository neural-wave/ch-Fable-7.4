"""Interval reasoning on rounded amounts: every rounded amount bounds the exact value that it comes from.

If 9.45 is round(rate x base) with half-up rounding, the product rate x base lies between 9.445 and 9.455, so the
rate of that row lies in an interval. Intersecting the intervals of a group gives its exact rate, or nothing: a
missing condition, a wrong rounding mode or an outlier. All values are integers: amounts in cents, rates in
millionths, products in cents x millionths.
"""
import math

import z3

from neuron.solver import SCALE, numeral, parsed

RATE = z3.Int("rate")  # the unknown rate, in millionths
MARGINS = {  # mode: how far below and above amount x SCALE a product can lie and still round to the amount
    "half_up": (500_000, 499_999),  # the half rounds up
    "half_even": (500_000, 500_000),  # the half-up interval plus the exact halves, which round to the even cent
    "down": (0, 999_999),  # every rest is cut off
    "up": (999_999, 0),  # every rest adds a cent
}


def fits(base: int, amount: int, mode: str) -> z3.BoolRef:
    """Z3 constraint, linear in RATE: `base x RATE` (cents x millionths) rounds to `amount` cents with `mode`."""
    below, above = MARGINS[mode]
    exact = numeral(math.prod([amount, SCALE]))
    return parsed(f"(<= (- {exact} {below}) (* {numeral(base)} rate) (+ {exact} {above}))", RATE)


def within(top: int) -> z3.BoolRef:
    """Z3 constraint: RATE lies between 0 and `top`."""
    return parsed(f"(<= 0 rate {numeral(top)})", RATE)
