"""Proofs with Z3: can any rule of a finite space of bases, rates and rounding modes give an amount?

A SAT answer names a rule that gives the amount. An UNSAT answer is a proof over the whole space: none gives it,
so the amount was set by hand or follows a rule outside the space.
"""
import z3

from neuron.solver import MODES, SCALE


def rounded(product, mode: str):
    """Z3 expression: `product` (cents x millionths) rounded to cents with the rounding `mode`.

    The carry adds the cent that the integer division cuts off, when the rounding mode asks for it.
    """
    quotient, rest = product / SCALE, product % SCALE  # integer division of non-negative numbers
    carry = {
        "half_up": rest >= SCALE // 2,
        "half_even": z3.Or(rest > SCALE // 2, z3.And(rest == SCALE // 2, quotient % 2 == 1)),
        "down": z3.BoolVal(False),
        "up": rest > 0,
    }[mode]
    return quotient + z3.If(carry, 1, 0)


def one_of(var, values: dict[str, int]):
    """Z3 constraint: `var` takes one of the integer `values`."""
    return z3.Or([var == value for value in values.values()])


def name_of(values: dict[str, int], value: int) -> str:
    """The name of `value` in `values`, e.g. the base column of the base that Z3 picked."""
    return next(name for name, candidate in values.items() if candidate == value)


def explain(target: int, bases: dict[str, int], rates: dict[str, int], modes=MODES) -> dict | None:
    """A combination (base, rate, mode) with `round(rate x base) == target`, or None if there is none (UNSAT).

    `bases` and `rates` map a name to an integer in cents or millionths, e.g. {"PR_AMTRC": 18000} and
    {"B/L": 30000}; `target` is in cents.
    """
    base, rate, mode, product = z3.Int("base"), z3.Int("rate"), z3.Int("mode"), z3.Int("product")
    solver = z3.Solver()
    solver.add(one_of(base, bases), one_of(rate, rates))
    solver.add(z3.Or([z3.And(base == b, rate == r, product == b * r) for b in bases.values() for r in rates.values()]))
    solver.add(z3.Or([z3.And(mode == i, rounded(product, m) == target) for i, m in enumerate(modes)]))
    if solver.check() != z3.sat:
        return None
    model = solver.model()
    return {"base": name_of(bases, model[base].as_long()), "rate": name_of(rates, model[rate].as_long()),
            "mode": modes[model[mode].as_long()]}
