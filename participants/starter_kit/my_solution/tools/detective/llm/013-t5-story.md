# 013 · t5 · the noise and the structure

**Step:** story → tools (§6 "find the noise", "find the structure") → findings → rule. **LLM:** Claude Code.

## Input

The task text of t5:

> Goal: find the values in all previous tasks that were overwritten by hand. Some are listed in NREXCP, but not
> all; some tasks have outliers, while some might not. t5 gets the target files of the policies it has to check.
> A value that differs from what your rules calculate is either a manual correction or a rule you have not found
> yet.

§6: "Find the noise: anomaly detection (for example an isolation forest on the remaining differences) separates
the manual corrections from rules you have not found yet." "Find the structure: clustering groups policies that
behave in the same way, and feature importance shows which columns matter for a target."

What the rules leave (`check.py`): t0 10, t1 0, t2 8, t3 16, t4 20 differences.

## Prompt 1: the noise

Write an isolation forest on the differences that a round leaves, from features of the difference alone (no
labels); NREXCP only checks the result. A rule not found yet repeats, or cancels within a policy (an amount moved
to the next year); a hand edit stands alone.

Output: `tools/detective/noise.py` (`difference_features`: size, cents part, share of the target value, how
often the same difference occurs, how much the differences of a policy add up rather than cancel, how many
values of a row differ; `isolate`; `write_noise`).

- `t3_surrender_value/r1-noise` (round r1: an unfound rule and the hand edits together): **N1** 26 of 252
  differences isolated, 16 in whole francs (all 16 hand edits); **N2** all 12 NREXCP-listed entities isolated.
  Not isolated: 226 differences of +1 cent, the unfound rule (the old system rounding the penalty up,
  `t3_surrender_value/r2-search-penalty`)
- `t4_annual_statement/r1-noise` (round r1: entry charges in the wrong year and the hand edits): **N1** 19 of 56
  isolated, 12 in whole francs; the moved entry charges stay mostly unflagged. With 56 rows the forest is noisy,
  but it ranks the edits high
- the final rounds (`t0_commission/final-noise`, `t2_projected_maturity_value/final-noise`,
  `t3_surrender_value/r4-noise`, `t4_annual_statement/r2-noise`): every difference left is a whole number of
  francs (t0 10, t2 8, t3 16, t4 20), the NREXCP-listed ones among them (t0 6, t2 5, t3 11, t4 16 entities)

## Prompt 2: the structure

Write the permutation importance of the columns for the wrong rows of a round (a random forest, held-out rows)
and a clustering of the policies on their wrong share and the columns that matter.

Output: `tools/detective/structure.py` (`importance`, `clusters`, `structure`).

- `t4_annual_statement/r1-structure`: **I1** EX_TARGET = t4_annual_statement.admin_fees (the NREXCP listing):
  the ROC AUC drops by 0.079; **K1** the 17 listed policies, wrong 11.0 %, against 0.1 % elsewhere
- `t3_surrender_value/r1-structure`: the importance is diluted by the many date columns that say the same; the
  clusters say where to look: **K2** 11 policies with 63.6 % wrong rows, set apart by the NREXCP listing (the hand
  edits); **K1** old policies (long since the start), 5.6 % wrong, against **K3** 0.4 %: the old system, as the
  change point r1/C1 showed

## The rule

The rules of t0–t4 calculate every train value but these differences, and all of them are whole francs: a person
typed a new amount, while a rule not found yet leaves cents (r1-noise of t3). So a target value is taken for a
hand edit when it differs from the rule by whole francs.

Output: `outliers.py` (`outliers`: the rule values of t0, t2, t3 and t4 in cents next to the target files in
`targets_dir`); `submission.t5_outlier_detection`. `check.py`: 54 outliers (t0 10, t2 8, t3 16, t4 20), the
same 54 differences.
