# 014 · regression and Z3 · recover the rates from inputs and outputs

**Step:** §6 "find the formula: linear or robust regression recovers rates and factors from inputs and outputs;
symbolic regression and program synthesis search for the expression that matches the targets exactly". **LLM:**
Claude Code.

## Prompt

Write a tool that recovers the factor of a rule from inputs and outputs alone: a robust regression for the
approximate factor and the rows it does not explain, and a solver for the one integer factor that reproduces every
row to the cent under a given rounding. Check it on two rules whose rates the tariff tables hold, without reading
those tables: the management charge and the surrender penalty.

## Output

`tools/detective/regression.py`: `factors` (Huber regression without intercept), `exact_factor` (Z3: the integer k
with target = round(term × k / scale) on a sample of 400 rows), `write_formulas`.

## Findings

`reports/t3_booking_amc/r6-formulas.md`: the management charges of Neuron NG without individual agreements, on the
teacher-forced values (`charges.run_rows`, `charges.value_of`), grouped by the tariff family (the first two
letters of the tariff key) and the pot:

- **F1–F5** regression and Z3 agree: FK 3 % (pot 1) and 1.2 % (pot 2), FX 2.5 % and 1 %, FS 0.9 % a year, a
  twelfth per run rounded half up. These are CG_AMCP1 and CG_AMCP2 of NRCHRG, the same in every generation.

`reports/t3_surrender_value/r4-formulas.md`: the surrender values with a penalty, by the product's scale and the
completed policy years:

- **F1–F10, F15–F20, F24–F27** the penalty rates of NRSURR, exactly (scale 1: 5, 4, 3, 2, 1 %; scale 2: 3, 2,
  1 %; scale 3: 2, 1 %), with the surrender value rounded half up by Neuron NG and cut off by the old system (as
  `t3_surrender_value/r3-search-net/S1` found)
- **F11–F14, F21–F23, F28** single rows beyond the scale whose surrender value is above the policy value: no
  factor fits. These are hand edits (t5, `013-t5-story.md`)
