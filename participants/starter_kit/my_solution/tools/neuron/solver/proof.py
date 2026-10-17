"""Proofs with Z3: can any rule of a finite space of bases, rates and rounding modes give an amount?

Every rule of the space is one candidate: a base (e.g. PR_AMTRC), a rate (e.g. B/L) and a rounding mode. Z3 looks
for a candidate whose rounded product is the amount. A SAT answer names such a rule. An UNSAT answer is a proof
over the whole space that none gives it: the amount was set by hand or follows a rule outside the space.
"""
import itertools
import math

import z3

from neuron.solver import HALF, MODES, SCALE, numeral, parsed

RULE = z3.Int("rule")  # the number of the candidate rule that Z3 picks
CARRY = {  # mode: when rounding adds a cent, in SMT-LIB over the cents q and the rest r of a product
    "half_up": f"(>= r {HALF})",
    "half_even": f"(or (> r {HALF}) (and (= r {HALF}) (= (mod q 2) 1)))",
    "down": "false",
    "up": "(> r 0)",
}


def rounded(product: int, mode: str) -> str:
    """SMT-LIB term: the product (cents x millionths) rounded to cents with the rounding `mode`.

    The integer division cuts off the rest of the product; the carry adds the cent back when the mode asks for it.
    """
    term = numeral(product)
    return f"(let ((q (div {term} {SCALE})) (r (mod {term} {SCALE}))) (+ q (ite {CARRY[mode]} 1 0)))"


def explain(target: int, bases: dict[str, int], rates: dict[str, int], modes=MODES) -> dict | None:
    """A rule {"base", "rate", "mode"} with `round(rate x base) == target`, or None if there is none (UNSAT).

    `bases` and `rates` map a name to an integer in cents or millionths, e.g. {"PR_AMTRC": 18000} and
    {"B/L": 30000}; `target` is in cents.
    """
    rules = list(itertools.product(bases, rates, modes))
    candidates = " ".join(f"(and (= rule {number}) (= {rounded(math.prod([bases[base], rates[rate]]), mode)} "
                          f"{numeral(target)}))" for number, (base, rate, mode) in enumerate(rules))
    solver = z3.Solver()
    solver.add(parsed(f"(or {candidates})", RULE))
    match solver.check():
        case z3.sat:
            return dict(zip(("base", "rate", "mode"), rules[solver.model()[RULE].as_long()], strict=True))
    return None
