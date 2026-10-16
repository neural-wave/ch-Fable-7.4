"""Proofs with Z3: can any rule of a finite space of bases, rates and rounding modes give an amount?

Every rule of the space is one candidate: a base (e.g. PR_AMTRC), a rate (e.g. B/L) and a rounding mode. Z3 looks
for a candidate whose rounded product is the amount. A SAT answer names such a rule. An UNSAT answer is a proof
over the whole space that none gives it: the amount was set by hand or follows a rule outside the space.
"""
import itertools

import z3

from neuron.solver import HALF, MODES, SCALE


def rounded(product: int, mode: str):
    """Z3 expression: the product (cents x millionths) rounded to cents with the rounding `mode`.

    The integer division cuts off the rest of the product; the carry adds the cent back when the mode asks for it.
    """
    quotient, rest = z3.IntVal(product) / SCALE, z3.IntVal(product) % SCALE
    carry = {"half_up": rest >= HALF, "half_even": z3.Or(rest > HALF, z3.And(rest == HALF, quotient % 2 == 1)),
             "down": z3.BoolVal(False), "up": rest > 0}[mode]
    return quotient + z3.If(carry, 1, 0)


def explain(target: int, bases: dict[str, int], rates: dict[str, int], modes=MODES) -> dict | None:
    """A rule {"base", "rate", "mode"} with `round(rate x base) == target`, or None if there is none (UNSAT).

    `bases` and `rates` map a name to an integer in cents or millionths, e.g. {"PR_AMTRC": 18000} and
    {"B/L": 30000}; `target` is in cents.
    """
    rules = list(itertools.product(bases, rates, modes))
    choice = z3.Int("rule")
    solver = z3.Solver()
    solver.add(z3.Or([z3.And(choice == i, rounded(bases[base] * rates[rate], mode) == target)
                      for i, (base, rate, mode) in enumerate(rules)]))
    if solver.check() == z3.unsat:
        return None
    return dict(zip(("base", "rate", "mode"), rules[solver.model()[choice].as_long()], strict=True))
