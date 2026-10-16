"""Rate recovery with Z3 MaxSMT: the rate of a group of rounded amounts, found from the amounts alone.

Every row of a group gives an interval for the rate (`intervals`), and the rate of the group must fit the
intervals of all its rows. The constraints are linear in the rate, which keeps MaxSMT fast (an encoding with
integer division and remainder took minutes per group instead of a fraction of a second).
"""
import z3

from neuron.solver import SCALE
from neuron.solver.intervals import fits, keeps


def bound(rate, constraints: list, minimize: bool) -> int:
    """Smallest or largest rate that satisfies all `constraints`.

    The two bounds show how sharply the data fixes the rate: a single value when they are equal.
    """
    optimizer = z3.Optimize()
    optimizer.add(*constraints)
    (optimizer.minimize if minimize else optimizer.maximize)(rate)
    optimizer.check()
    return optimizer.model()[rate].as_long()


def recover_rate(pairs: dict[tuple[int, int], int], mode: str = "half_up", max_rate: int = SCALE) -> dict:
    """The rate (millionths) that reproduces the most (base, amount) pairs; `pairs` maps a pair to its count.

    MaxSMT: every pair is a soft constraint weighted by its count. Returns the best rate, the interval [low, high]
    of the rates that keep all those pairs, the number of rows and the pairs that no such rate explains.
    """
    rate = z3.Int("rate")
    domain = [rate >= 0, rate <= max_rate]
    optimizer = z3.Optimize()
    optimizer.add(*domain)
    for (base, amount), count in pairs.items():
        optimizer.add_soft(fits(rate, base, amount, mode), weight=count)
    optimizer.check()
    best = optimizer.model()[rate].as_long()
    kept = [pair for pair in pairs if keeps(best, *pair, mode)]
    constraints = [*domain, *(fits(rate, *pair, mode) for pair in kept)]
    return {"rate": best, "low": bound(rate, constraints, True), "high": bound(rate, constraints, False),
            "rows": sum(pairs.values()), "outliers": {pair: pairs[pair] for pair in set(pairs).difference(kept)}}
