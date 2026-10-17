# 005 · t2_projection_year · from the story to round 1

**Step:** story → first rule as a sketch with holes. **LLM:** Claude Code.

## Input

The task text of t2:

> Goal: calculate the value at maturity that the offer projected for every policy.
> - The projection simulates the policy month by month, from the start date to the maturity date, as if the
>   funds grew every month at the assumed yearly rate of NRILLU.
> - It is a simplified accounting: there are no real fund prices, no currencies and no individual agreements,
>   and the whole value is treated as one amount.
> - The diagnostic file shows the projected value at the end of every policy year.

From the general text: parameters are valid on the application date and not today; the COBOL and Java versions
of Neuron do not calculate everything in the same way. From t3: every month Neuron takes the admin fee, the
management charge (a different rate per pot) and the risk charge.

The tables the spec tool linked to the anchor NRRISK (`spec.spec_for`, `schema.relations`) and their dictionary
entries: NRPOLH (premium, frequency, start, maturity, broker), NRRISK (tariff key, sum insured, medical loading),
NRPERS (birth date, sex, smoker), NRPROD (tariff family, PD_INIMON "months of initial pot"), NRCHRG (admin fee,
management charge pot 1 and pot 2 p.a., smoker factor, mortality table), NRENTC (entry charge rate per broker
tier), NRMORT (death probability per table, sex and age), NRILLU (illustration growth rate p.a.).

## Prompt

Write the projection the story describes. Every choice the story leaves open becomes a hole of the sketch, with
the readings an actuarial system plausibly uses, so the search can decide (§6 "program synthesis by sketching").

## Output

`projection.py`, round 1. Every month: the premium due in that month less the entry charge, then the admin fee,
the management charge, the risk charge (sum at risk × death probability / 12 × (1 + loading) × smoker factor),
then a month of growth. The tariff key gives the sex basis of the mortality table (position 3: M, W or U) and
the death benefit option (position 7: A, B, C).

Holes:

- `parameter_day`: the date whose parameters count: PH_APPDT (the story's hint) or PH_BEGDT
- `pots`: "two" (the premiums of the first PD_INIMON months at CG_AMCP1) or "one"
- `age`: completed years, nearest birthday, calendar years, days / 365, days / 365.25, months / 12
- `half_up`: every amount half up to the cent, or cut off
- `growth`: one rounded fraction, or decimal arithmetic with 16 or 28 significant digits

Round 1 with the plainest reading (two pots, completed years, half up, fraction): 5058 of 79040 rows right
(`reports/t2_projection_year/r1.md`).
