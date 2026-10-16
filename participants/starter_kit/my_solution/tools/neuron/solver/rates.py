"""Rate recovery with Z3 MaxSMT: the rate of a group of rounded amounts, found from the amounts alone.

Every rounded amount bounds the exact product, so the rate of one row lies in an interval and the rate of the
group must fit the intervals of all its rows. The constraints are linear in the rate, which keeps MaxSMT fast
(an encoding with integer division and remainder took minutes per group instead of a fraction of a second).
"""
import z3

from neuron.solver import SCALE

OFFSETS = {  # mode: (lowest, highest) product - amount x SCALE that still rounds to the amount
    "half_up": (-SCALE // 2, SCALE // 2 - 1),
    "half_even": (-SCALE // 2, SCALE // 2),  # the half-up interval plus the exact halves
    "down": (0, SCALE - 1),
    "up": (-SCALE + 1, 0),
}


def bounds(base: int, amount: int, mode: str) -> tuple[int, int]:
    """Smallest and largest product `base x rate` (cents x millionths) that rounds to `amount` cents.

    Half-even uses the half-up interval widened by the exact halves: the two differ only there.
    """
    low, high = OFFSETS[mode]
    return amount * SCALE + low, amount * SCALE + high


def fits(rate, base: int, amount: int, mode: str):
    """Z3 constraint, linear in `rate`: `base x rate` rounds to `amount`."""
    low, high = bounds(base, amount, mode)
    return z3.And(base * rate >= low, base * rate <= high)


def keeps(rate: int, base: int, amount: int, mode: str) -> bool:
    """True when the integer `rate` reproduces the pair (base, amount).

    The same test as `fits`, in plain Python, for a rate that Z3 already found.
    """
    low, high = bounds(base, amount, mode)
    return low <= base * rate <= high


def bound(rate, constraints: list, minimize: bool) -> int:
    """Smallest or largest non-negative rate that satisfies all `constraints`.

    The two bounds show how sharply the data fixes the rate: a single value when they are equal.
    """
    optimizer = z3.Optimize()
    optimizer.add(rate >= 0, *constraints)
    (optimizer.minimize if minimize else optimizer.maximize)(rate)
    optimizer.check()
    return optimizer.model()[rate].as_long()


def recover_rate(pairs: dict[tuple[int, int], int], mode: str = "half_up", max_rate: int = SCALE) -> dict:
    """The rate (millionths) that reproduces the most (base, amount) pairs; `pairs` maps a pair to its count.

    MaxSMT: every pair is a soft constraint weighted by its count. Returns the best rate, the interval [low, high]
    of the rates that keep all those pairs, the number of rows and the pairs that no such rate explains.
    """
    rate = z3.Int("rate")
    optimizer = z3.Optimize()
    optimizer.add(rate >= 0, rate <= max_rate)
    for (base, amount), count in pairs.items():
        optimizer.add_soft(fits(rate, base, amount, mode), weight=count)
    optimizer.check()
    best = optimizer.model()[rate].as_long()
    kept = [fits(rate, *pair, mode) for pair in pairs if keeps(best, *pair, mode)]
    outliers = {pair: count for pair, count in pairs.items() if not keeps(best, *pair, mode)}
    return {"rate": best, "low": bound(rate, kept, True), "high": bound(rate, kept, False),
            "rows": sum(pairs.values()), "outliers": outliers}
