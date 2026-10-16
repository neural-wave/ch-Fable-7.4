"""Z3 tools to explain rounded amounts of the form `amount = round(rate x base)`, in exact integer arithmetic.

Money is in cents and rates in millionths (`N(6)`: 0.03 is 30000), so the product `base x rate` is an integer in
units of 1e-8 francs and rounding it to cents is an integer division by `SCALE` plus a carry.

- `proof.explain` asks whether any combination of candidate bases, rates and rounding modes gives an amount.
  UNSAT proves that no rule of that space produces it: a manual correction or a missing rule.
- `rates.recover_rate` finds with MaxSMT the one rate that reproduces the most (base, amount) pairs of a group,
  without looking at the parameter tables; the pairs that it cannot reproduce are the outliers of the group.
"""
SCALE = 1_000_000  # rates in millionths: cents x millionths / SCALE = cents
MODES = ("half_up", "half_even", "down", "up")  # the rounding modes to cents that the tools consider
