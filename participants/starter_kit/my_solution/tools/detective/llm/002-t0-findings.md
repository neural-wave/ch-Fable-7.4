# 002 · t0_commission · from the findings of round r1 to round 2

**Step:** findings → code (§6 "an LLM can turn the conditions found by a decision tree into readable code").
**LLM:** Claude Code.

## Input

`reports/t0_commission/r1.md`:

- 224418 right, 1440 wrong
- **r1/T1** `BR_TIER@PR_RCVDT != BR_TIER@last`: 1430 of 1430 wrong (100 %). The rule is wrong exactly where
  the broker tier on the money date differs from the tier of the last policy version.
- the change points explain at most 2 % of the wrong rows: no system change in t0

`reports/t0_commission/r1-search.md`, the holes of round 1 tried in all 18 combinations:

- **S1–S3** broker on PR_RCVDT, half up: 183519 / 183527 right on 80 % of the policies, 42329 / 42331 held out;
  the date of the rate lookup does not change a single row
- **S4–S6** broker on PR_DUEDT: 2 rows fewer; **S7–S9** cut off instead of half up: 2 rows fewer
- the last version (the story's plain reading): 1215 rows fewer

## Prompt

Turn the finding with the most exact matches into the rule. Where the data cannot choose between candidates,
take the simpler rule and say so.

## Output

`commission.py`: `broker_day="PR_RCVDT"`, `rate_day="PR_RCVDT"` (one date for both lookups; the data cannot tell
it from PR_DUEDT), `half_up=True`. The docstring cites r1/T1 and r1-search/S2.

## Result

10 rows left (8 + 2 held out). Next: `discover` round r2 on what is left.
