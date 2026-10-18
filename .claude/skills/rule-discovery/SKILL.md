---
name: rule-discovery
description: Find the exact formula of a Neuron challenge target (t0_commission ... t4_annual_statement, t5 outliers) with the lab pipeline - clustering, optimal decision trees, exact score - one change at a time, then freeze or write the function in starter_kit/my_solution/submission.py and score it with lab score. Use it for any work on the challenge tasks.
---

# Rule discovery with the lab

You reverse-engineer the formulas of a legacy insurance system. The lab finds them, you steer it:

- **clustering** of target/input relations finds the regimes of a formula (rates, offsets) and the noise rows;
- **optimal decision trees** find the conditions that select each regime;
- the **exact scorer** decides: a value counts only if it is right to the cent or to the day.

When the pipeline has a complete rule, `lab freeze` writes it as code. When it has only partial rules, you write the
function from them, and `lab score` compares it with the ground truth and explains, with the same trees, where it
is wrong. You add a feature or change the code only where a report shows a gap. You never trust a number that has
no score.

## Hard rules

1. Run every command from the `lab/` folder, with `uv run`.
2. Make **one change at a time**. After every change, run the command that scores it and write the number down.
3. Never put target values into code. The code in `starter_kit/my_solution/` calculates everything from `legacy_dir`;
   only `t5_outlier_detection` reads `targets_dir`.
4. Do not edit `starter_kit/scoring.py`, `starter_kit/check.py`, `SCHEMA.md`, or anything in `legacy/` or `targets/`.
5. Do not edit the harness in `lab/neuronlab/`. If it lacks something, write it in `lab/runs/<task>/notes.md` and stop.
6. Never print a whole CSV or Parquet file: NRBOOK has 6.8 million rows. Read `report.md`, and look at single
   policies with `uv run lab show`.
7. Do not commit.

## The tasks

| Task | Key | Values | Extra argument |
|---|---|---|---|
| `t0_commission` | policy_id, due_nr | amount | |
| `t1_next_due_dates` | policy_id, n | due_date, collection_date | extract date 2026-06-30 |
| `t2_projected_maturity_value` | policy_id | maturity_value | |
| `t3_surrender_value` | policy_id, valuation_date | surrender_value | the valuation dates |
| `t4_annual_statement` | policy_id, year | premiums, entry_charges, admin_fees, management_fees, risk_charges, total_charges | |

The values of a task are computed in file order: a value may use the values before it (`collection_date` uses
`due_date`, `total_charges` the four charges), never a later one. The report shows these relations too, and calendar
features of the target's own dates such as `weekday(due_date)`.

The target files with more columns (`t3_surrender_value.policy_value`) and the diagnostic files (`t2_projection_year`,
`t3_booking`, `t3_holding`) help to understand a rule. The submission may never read them. The diagnostic files
are tasks of the lab too: `uv run lab run t3_booking` finds the formula of each booking amount, price and unit
count (on a fixed fifth of the policies, because the file has 5 million rows).

## The loop

### 1. Run the pipeline

```bash
uv run lab run <task>
```

It is the first command on a task, before you read data or write code. When `scripts/opencode-tasks.sh` started
you, it already ran it, `lab suggest` and `lab score`: their output is in `lab/runs/<task>/pipeline.md`.

`lab run` prints `lab/runs/<task>/report.md`. That file is all you need to read. For every target value it has:

| Line | Meaning |
|---|---|
| `Grain`, `Filter` | the legacy table the task iterates on, and which of its rows are in the target |
| `Relation: value / X: N clusters` | the value is X times a constant, one constant per cluster (`- X`: plus a constant; `- (days) X`, `- (months) X`: a date shifted from X) |
| `previous(v)` as X | a sequence: the value follows from the value of the same policy one step before (the previous due date, last year) |
| `Other relation: ...` | the next best relations: look at them when the first one leaves many rows as noise |
| `Exact identity: v = a + b + c` | the value is the sum of earlier values of the same row |
| `Approximate only: ...` | dense clusters that no constant reproduces to the cent: the value is probably a sum of parts rounded one by one |
| `Optimal trees: errors E, leaves L` | E rows that the best conditions put in the wrong cluster |
| `conflicting vector (...)` | rows with the same feature values but different clusters: **a feature is missing** |
| `Best candidate C...: total A/B, holdout H/K` | the best complete rule, its exact score on all rows and on the holdout |
| `Residuals: ... Fit another cluster` | rows that another cluster would fit: **a condition is missing** |
| `noise ... listed in NREXCP` | rows no rule reproduces: manual corrections, they go to t5 |

### 2. Decide: do exactly one of these

| The report says | You do |
|---|---|
| `conflicting vector` lines, or `Fit another cluster` residuals | Step 3: add one feature |
| Only `noise` residuals, one value column | Step 4a: freeze |
| `No relation with dense clusters`, several value columns, or freeze refuses | Step 4b: write the function and score it |

### 3. Add one feature

Compare the example row of a conflicting vector with a row of the majority cluster, with `uv run lab show`, for
example `uv run lab show NRPOLH PH_POLNR=BL10000309`. Find the column or date that differs, write it as one
expression of these primitives, and score it:

```bash
uv run lab feature <task> <name> "<expression>"
# <name> = <expression>: best before C2.1 224418, after C3.1.1 225848 rows exact (<task>~llm)
```

| Primitive | Meaning | Example |
|---|---|---|
| `at(column, date)` | value of a versioned column on a date of the grain row | `at(BR_TIER, PR_RCVDT)` |
| `days(d1, d2)` | days from d1 to d2 | `days(PR_DUEDT, PR_RCVDT)` |
| `weekday(d)`, `day(d)`, `month(d)`, `year(d)` | parts of a date; weekday 1 = Monday | `weekday(PR_DUEDT)` |
| `month_end(d)` | the date is the last day of its month | `month_end(PH_BEGDT)` |
| `age(birth, d)` | completed years from the first date to the second | `age(PH_BEGDT, valuation_date)` |
| `birthday_days(birth, d)` | days from d to the next anniversary of birth | `birthday_days(PS_BIRTH, PR_DUEDT)` |
| `pos(column, i)` | character i (from 1) of a code | `pos(RK_TARKEY, 6)` |
| `ratio(a, b)`, `diff(a, b)` | a / b and a - b of two numbers | `ratio(PR_AMTRC, PR_AMTDU)` |
| `era(d)` | `before` or `after` the system change of 2007-08-11 | `era(PH_APPDT)` |

- Keep the feature only if "after" is higher than "before". Otherwise try another one, at most 5 tries per task.
- The features accumulate in the run `<task>~llm`. To start again, delete `lab/runs/<task>~llm/`.
- Instead of choosing yourself, `uv run lab suggest <task>` asks the open-weights model once and scores its answer in
  the same way. It starts again from a fresh `<task>~llm`: features added before are dropped.

### 4a. Freeze the winner into the submission

```bash
uv run lab freeze <task>~llm      # or: uv run lab freeze <task>   when no feature was added
```

It prints the generated function and the output of `check.py`. The `check.py` score must equal the `total` of the
candidate in the report. If it does not, write both numbers in `notes.md` and stop.

If freeze answers `refused: no code template for ...`, go to step 4b. If it answers `refused: the new function
scores ...`, the current function is better and stays. In both cases `submission.py` is unchanged.

### 4b. Write the function and score it

1. In `starter_kit/my_solution/submission.py`, write the function of the task from the evidence in the report:
   - the grain table and the filter are the loop and its `if`;
   - each card (leaf) is a condition and its constant, and a lookup replaces a group of cards;
   - the relation says how the constant is applied (`value / X` means `X * constant`).

   Use the helpers of `neuron.py`: `table`, `keyed`, `grouped`, `valid`, `latest`, `cents`, `add_months`. Keep the
   function short and generic, because the maintainability index of `submission.py` and `neuron.py` is scored: a
   lookup instead of constants, a loop instead of copies, a comment where a rule is not obvious.
2. Score it:
   ```bash
   uv run lab score <task>
   # Exact rows: 224418 / 225858 (holdout 43880 / 44052); ...
   # | x0.67 | 515 | [('BL10000309', 1), ...] |
   # Where it is wrong: optimal tree errors 121, leaves 7 on {EC_RATE@PR_RCVDT, BR_TIER}
   ```
   Every value column gets a table of labels for its wrong rows:
   - a difference such as `+2 days` or `+60.00`;
   - a ratio such as `x0.67`;
   - `missing`, when the function gave no value for a target key;
   - `noise`, for rows that look like manual corrections.

   The line `Where it is wrong` gives the conditions under which the function is wrong.
3. Change **one** thing, the one that line points at, and score again. Keep the change only if `Exact rows` goes up
   and the holdout does not go down.
4. To give the trees a feature they do not have, add it to the command, in the language of step 3:
   `uv run lab score <task> "receipt_tier=at(BR_TIER, PR_RCVDT)"`.
5. Stop when only `noise` is left, or after 10 changes without progress.

`lab score` refuses functions that open a target file. Every score goes into `lab/runs/<task>/ledger.jsonl`.

### 5. Verify

```bash
uv run pytest -q                                          # all pass; "2 skipped" is fine
(cd ../starter_kit && python3 check.py --tasks <task>)    # the score of step 4 again, with the system Python
```

Also check that the function does not read NRBOOK: the hand-in runs within a time limit, and the 6.8 million rows
of NRBOOK take minutes to read.

### 6. Let t5 see the task

`t5_outlier_detection` checks only the tasks listed in `CHECKED` at the end of `submission.py`. When a task scores
well, add it there with its key and value converters, like `t0_commission`. t5 calls each function with
`legacy_dir` only. Before you add t1 or t3, extend that call: t1 needs the extract date 2026-06-30, and t3 needs the
valuation dates, which t5 may read from the t3 file in `targets_dir`. Then run
`(cd ../starter_kit && python3 check.py --tasks t5_outlier_detection)`.

### 7. Write the notes

Append to `lab/runs/<task>/notes.md`: date, winning candidate, features added, score (total and holdout), the
residuals left and the open questions. The README of the hand-in is written from these notes.

## Worked example: t0, with the reference-date columns removed

`uv run lab suggest t0_commission --ablate '*@*' --dry-run` removes every column read on a date and prints the
prompt. Its report says:

```
Optimal trees: errors 1430, leaves 6; smallest feature sets: {BR_TIER, PH_PRDCD}; ...
  conflicting vector (BR_TIER = B, PH_PRDCD = FLKL): clusters 0.03 x 60987, 0.02 x 201, 0.04 x 164; example ['BL10000309', 1]
Best candidate C2.1: 6 constants on BR_TIER, PH_PRDCD, ROUND_HALF_UP; total 224418/225858
```

Same tier and product, different rates: the tier of the broker is not the same at all dates.
`uv run lab show NRPOLH PH_POLNR=BL10000309` shows two versions of the policy: broker B00055 until 2015-01-25,
then B00140. The right feature reads the tier on the day the premium was received: `at(BR_TIER, PR_RCVDT)`. With it the tree has
0 errors, the pool finds the lookup `NRCOMR.CR_RATE[CR_TIER, CR_PAYTP]`, and the score goes back to 225848 / 225858.
The 10 rows left are noise: manual corrections, 6 of them listed in NREXCP.

## Worked example: a written function that is wrong

A function for t0 that reads the current version of the policy (`latest`) instead of the version valid on
`PR_RCVDT` scores 224418 / 225858. `uv run lab score t0_commission` then shows the ratios `x0.67`, `x2.00`, `x1.33`,
`x1.50` and `x0.75`. These are the ratios between the commission rates of two tiers. The optimal tree on
{EC_RATE@PR_RCVDT, BR_TIER} puts them where the tier on the receipt date differs from the current tier. The fix is
`valid(..., "PH", premium_item["PR_RCVDT"])`, which gives 225848 again.

## Useful commands

```bash
uv run lab show <table or target> COL=VALUE ...   # at most 40 rows, e.g. lab show t1_next_due_dates policy_id=BL10000001
uv run lab score <task> [name=expression ...]      # exact score of submission.py and where it is wrong
uv run lab pool show <task>                       # all candidates with their scores
uv run lab iterate <task>                         # residuals of the best candidate again
```

Table and column meanings are in `SCHEMA.md` and in `legacy/NRDICT.csv`.
