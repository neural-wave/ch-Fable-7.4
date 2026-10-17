"""Z3 tools to explain rounded amounts of the form `amount = round(rate x base)`, in exact integer arithmetic.

Money is in cents and rates in millionths (`N(6)`: 0.03 is 30000), so the product `base x rate` is an integer in
units of 1e-8 francs and rounding it to cents is an integer division by `SCALE` plus a carry.

The constraints are written in SMT-LIB, the input language of Z3, and parsed by Z3: `(<= low (* base rate) high)`
says that `base` times the unknown integer `rate` lies between `low` and `high`.

- `proof.explain` asks whether any combination of candidate bases, rates and rounding modes gives an amount.
  UNSAT proves that no rule of that space produces it: a manual correction or a missing rule.
- `intervals`: the interval of exact products, and so of rates, that a rounded amount allows.
- `rates.recover_rate` finds with MaxSMT the one rate that reproduces the most (base, amount) pairs of a group,
  without looking at the parameter tables; the pairs that it cannot reproduce are the outliers of the group.
"""
import z3

SCALE = 1_000_000  # rates in millionths: cents x millionths / SCALE = cents
HALF = 500_000  # half a cent, in the units of a product (cents x millionths)
MODES = ("half_up", "half_even", "down", "up")  # the rounding modes to cents that the tools consider


def numeral(number: int) -> str:
    """`number` as an SMT-LIB numeral; a negative one is written `(- 5)`."""
    return z3.IntVal(number).sexpr()


def parsed(formula: str, unknown: z3.ArithRef) -> z3.BoolRef:
    """The SMT-LIB `formula` as a Z3 constraint on the integer `unknown`, which it names by its name."""
    return z3.parse_smt2_string(f"(assert {formula})", decls={str(unknown): unknown})[0]
