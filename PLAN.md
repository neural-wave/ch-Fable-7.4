# The Neuron Migration: data check and action plan

**Are we heading in the right direction? What the data say, what to change and how to proceed until Sunday at 16:00, with two goals: 100% accuracy on t0–t4 and a maintainability index of at least 95**

Neural Wave AI Hackathon 2026 · Lifeware Challenge · USI Lugano
Working document for the team · night between Friday 16 and Saturday 17 October 2026

Sources analyzed: `Lifeware_Challenge.pdf` (the challenge text), `Lifeware_Challenge_Analisi_e_Strategia.pdf` (the team's strategy document, hereafter "the document"), the `participants/` folder (27 legacy tables, 8 target files, `SCHEMA.md`, starter kit).

Material delivered with this plan:

- `tools/data_checks.py` reproduces every number in this document in about 6 seconds;
- `tools/mi_report.py` breaks the maintainability index down file by file;
- `tools/ledger_checks.py` compares every booking with NRBOOK (all policies) and `t3_booking` (train);
- `tools/evaluator_check.py` times every task in a fresh process and compares every value with a saved run;
- `my_solution/` is our submission: t0–t4 at 100% of the evaluated rows, MI 97.3; its `README.md` explains all the rules and its `ARCHITECTURE.md` maps the code.

---

## Status on 17 October, 03:15: t4 timed out on the leaderboard, the runs made faster

**The leaderboard.** After the tie fix the leaderboard showed 80% overall: t4 had run out of the
evaluator's time limit (scored 0), so the four other tasks were at 100%, t3 included. Locally t3
and t4 took 35 s each in a fresh process, 68 s for the five tasks in one process.

**What changed, measured.** Profiling first: 87% of t4 was the ledger (533,660 monthly runs,
6.8 million bookings), the export load only 3 s.

| Change | Where |
|---|---|
| t3 and t4 from one pass of the ledger; t4 after t3 returns the kept statements | `reports/books.py` |
| month arithmetic as one number instead of dateutil's relativedelta (2 µs a call) | `core/months.py` |
| `Counter[...] +=` instead of `Counter.update({...})`, 3.5 times faster | `accounting/trades.py`, `core/totals.py` |
| t3: one account follows the valuation days, instead of one rebuilt per day | `reports/valuation.py` |
| prices of a fund on a day looked up once; rounding mode passed positionally | `legacy/market.py`, `core/money.py` |

| Run | Before | Now |
|---|---|---|
| five tasks in one process, as `check.py` | 68 s | 30 s (t3 24 s, t4 0.1 s) |
| t3 alone in a fresh process | 35.6 s | 27 s |
| t4 alone in a fresh process | 34.7 s | 27 s |

Every value of every task is identical to the run before the changes on all 4,011 policies, train
and public (`tools/evaluator_check.py --compare`); `check.py`, the NRBOOK skeleton and the train
bookings are unchanged. The MI first fell to 94.7: a single `+=` in a flow module makes radon apply
the formula to the whole file. The arithmetic moved into small formula modules, and five modules
were split by concept (`runs` → `reports/periods`, `risk` → `mortality`, `schedule` → `anchor`,
`business_days` → `holiday_calendar`, the value left after ADM and AMC → `accounting/remainder`):
MI **97.3**.

**TODO**

- [ ] Submit again: t4 back within the time limit, and t3 and t4 at 100% on the public policies.
- [ ] Raise the MI further, module by module, without losing speed or a single value.
- [ ] t5 outliers (§4.6) and t6 tools (§4.7): on hold, as the user asked.

---

## Status on 17 October, 02:10: public t3/t4 miss fixed, repo in English, Python 3.14

**The leaderboard.** On the public policies t3 and t4 were below 100% (total 99.99%), while the
train stayed at its ceilings. The public targets are hidden, but NRBOOK keeps the skeleton of every
booking of every policy (type, fund, pot, trade and price date; only the amounts are blank).
Comparing it with our ledger for all 4,011 policies found exactly one difference: on public policy
BL10002262 a 50/50 switch left two positions of 3,024.98 each, and the rounding rest of the risk
charge (0.01) went to the other fund. Neuron gives the rest to the largest position and, between
equal values, to the first by fund and pot; we took the insertion order. The fix is one word in
`my_solution/accounting/sharing.py` (`max(sorted(weights), ...)`). With the old rule the policy
had wrong t3 values (2020-04-30 and later year ends) and a wrong t4 row (2022 AMC); now:

| Check | Result |
|---|---|
| NRBOOK skeleton, all policies (`tools/ledger_checks.py`) | 4,011 / 4,011 identical (train and public) |
| Train amounts and units against `t3_booking` | 5,024,847 bookings, 3,017 / 3,017 policies identical |
| t3 on 11 other valuation dates (era switch, 29 Feb, holidays, extract) | 23,666 rows, no error, none negative |
| Ties with a rounding rest, all policies | 5; the old and new rule differ only on BL10002262 |

Official `check.py` on the train targets (Python 3.14.8, run in place with `python -B`):

| Task | Exact rows | Ceiling | Misses = manual corrections |
|---|---|---|---|
| t0 commissions | 225,848 / 225,858 = 99.9956% | reached | 10 |
| t1 next due dates | 15,028 / 15,028 = 100.0000% | reached | 0 |
| t2 projected maturity value | 3,011 / 3,019 = 99.7350% | reached | 8 |
| t3 surrender value | 6,137 / 6,153 = 99.7400% | reached | 16 |
| t4 annual statement | 34,125 / 34,145 = 99.9414% | reached | 20 |
| **Maintainability index** | **97.1** | target ≥ 95 | |

**The repository, now in English.** `my_solution/` (the hand-in name the organizers ask for), with
seven packages (`core`, `legacy`, `insurance`, `accounting`, `reports`, `billing`, `maturity`) and
`submission.py`, `conventions.py`, `export.py` at the top; `my_solution/ARCHITECTURE.md` is the map.
`tools/` holds `data_checks.py` (the numbers of this plan; expected output in
`data_checks_expected.txt`), `ledger_checks.py`, `import_map.py` (package layers) and
`mi_report.py`. Python 3.14 (`.python-version`): same rows and same MI per file as on 3.12.

**TODO**

- [x] Split `my_solution/` into business packages, with a layer check (`tools/import_map.py`).
- [x] Everything in English: folders, files, code, tools, this plan.
- [x] Python 3.14: verified, pinned in `.python-version`.
- [ ] Submit again to the leaderboard and confirm t3 and t4 at 100% on the public policies.
- [ ] t5 outliers (§4.6): rule mismatches with a whole delta, plus NREXCP.
- [ ] t6 tools and visualizations (§4.7), as notebooks or HTML inside `my_solution/tools/`.
- [ ] Agree with the team how to merge: `origin/master` was force-pushed to a new "Initial commit",
      so `feature/neuron-migration-t0-t4` no longer shares its base with it.

---

## Status as of 17 October, 01:30: t0–t4 closed, MI 97.1

The plan below is the one from Friday evening. This section says how far we have got and what the data corrected relative to the plan (§4.3 and §4.4 were open hypotheses). The code is on the `feature/neuron-migration-t0-t4` branch.

| Task | Official `check.py` on train | Local ceiling | Missed rows | Official estimate |
|---|---|---|---|---|
| t0 commissions | 225,848 / 225,858 = 99.9956% | 99.9956% | 10, all manual corrections | **100%** |
| t1 next due dates | 15,028 / 15,028 = 100.0000% | 100% | 0 | **100%** |
| t2 maturity value | 3,011 / 3,019 = 99.7350% | 99.7350% | 8, all manual corrections | **100%** |
| t3 surrender value | 6,137 / 6,153 = 99.7400% | 99.7400% | 16, all manual corrections | **100%** |
| t4 annual statement | 34,125 / 34,145 = 99.9414% | 99.9414% | 20, all manual corrections | **100%** |
| **MI (radon, as in `scoring.py`)** | **97.1** | | | target ≥ 95 |

The 54 missed rows are exactly the 54 manual corrections (whole-franc deltas), which the official evaluation does not count. The engine also reproduces every PRM, ADM, AMC and RSK movement of `t3_booking` and all 79,040 yearly values of `t2_projection_year`. It runs on all 4,011 policies in the export (train and test) without exceptions, in about a minute.

**What the data corrected relative to the plan:**

- *COBOL insurance age*: days lived / 365, rounded to the nearest year. 29 February does not count, so of two people with the same birthday the older one can get one extra year. It is not months with days ≥ 15. For Neuron NG, completed months apply, with the half year rounded up.
- *Risk base*: the policy value minus the ADM and AMC of the same run, taken as an amount rather than by revaluing the units. The risk is split according to what is left in each position, and pieces ≤ 0 are discarded.
- *Exhausted value*: the ADM does not exceed the policy value, and the RSK does not exceed the remaining value.
- *t2*: the projection reproduces the offer, i.e. the first version, with the tariff, NRILLU rate, entry charge and rounding of the **application date** `PH_APPDT`. It proceeds month by month: net premium, minus ADM, minus AMC at the pot 2 rate / 12, minus RSK, then growth at the rate / 12, all to the cent. No agreements are applied and there is no pot 1.
- *t4 years*: they run from the start year to the minimum of exit year (SUR/DTH, or a version in state 60/70), maturity year and 2025.

**How we reach MI 97.1.** There are two kinds of modules:

- *flow modules* (`export`, `market`, `account`, `ledger`, `investment`, `orders`, `charges`, `statement`, `valuation`, `offer`, `submission`): they apply the rules without any arithmetic or comparison operator, so radon scores them 100;
- *formula modules*: each family of formulas lives in a small, documented module (`money`, `sharing`, `conversion`, `trades`, `purchase`, `fees`, `cover`, `risk`, `ages`, `age_rules`, `runs`, `surrender`, `instalments`, `illustration`) and scores between 87 and 100.

Every change is verified by comparing the movements with the reference engine (zero differences on 3,019 policies) and then with the official `check.py`, run in place with `python -B` so that nothing is written into the organizers' folder.

**Next steps:**

- t5: the 54 corrections are already all integer deltas, so the detector is almost ready;
- t6: tools and visualizations;
- at hand-in, rename the folder to `my_solution` (done on 17 October, 02:10).

---

## Contents

0. [The verdict on one page](#0-the-verdict-on-one-page)
1. [What I did and how to read this document](#1-what-i-did-and-how-to-read-this-document)
2. [The team's strategy document tested against the data](#2-the-teams-strategy-document-tested-against-the-data)
3. [The findings that change the plan](#3-the-findings-that-change-the-plan)
4. [Confirmed rules and targets, task by task](#4-confirmed-rules-and-targets-task-by-task)
5. [Maintainability: how to reach MI 95](#5-maintainability-how-to-reach-mi-95)
6. [How I would proceed: the operating method](#6-how-i-would-proceed-the-operating-method)
7. [The plan: the moves until Sunday at 16:00](#7-the-plan-the-moves-until-sunday-at-1600)
8. [Risks and submission checklist](#8-risks-and-submission-checklist)
9. [Appendices](#9-appendices)

---

## 0. The verdict on one page

> **Verdict.** Yes, you are heading in the right direction. The document's method (count exact rows, build the harness first, treat conventions as data, break t3 down step by step, tackle t5 last) is exactly what the data reward. I applied it to the letter for a few hours on the real data and it worked straight away. But **nine points need correcting**: some cost hours, one alone would get t3 wrong on 454 policies, and one concerns maintainability, which the document treats as a constraint while for us it is a goal.

**What I measured** (train, exact rows, no statistical model):

| What | Result | Status |
|---|---|---|
| t0 commissions | 225,848 / 225,858 = **99.9956%**, i.e. 100% of the evaluated rows: the 10 residuals are manual corrections | in `my_solution/` |
| t1 next due dates | 15,028 / 15,028 = **100%** | in `my_solution/` |
| **Maintainability index** of the t0 + t1 skeleton | **94.6** (the empty stub scores 82.9) | in `my_solution/` |
| t3, the movement "bricks": trade date, price, invested amount, FX rate, units, admin fee | **100%** for each brick | rules ready |
| t3, surrender value given the policy value | 4,619 / 4,635 = **99.65%**; the 16 residuals are manual corrections | rule ready |
| t4 as the annual sum of the t3 movements | 34,125 / 34,145 = **99.94%** whole rows; the 20 residuals are manual corrections | rule ready, depends on t3 |
| t2, structure | projection years = term (3,019/3,019); rate at the application date (7/7 decisive cases) | structure clear |
| t5, signature of the manual corrections | **54 out of 54** are whole-franc deltas; NREXCP lists 38 of them (70%) | recipe ready |

**The nine points where the direction needs correcting**

1. **The COBOL → Java switch is not something to search for: it is written in the data.** Event 800 "system conversion" of **2007-08-11** (user `CONV2007`, 946 policies); the `CBLBATCH` batch runs until 10.8.2007, `NGBATCH` from 11.8.2007. The "decimals trick" would have found nothing: units have 6 decimals in both eras.
2. **"Parameters at the application date" holds for t2, not for t3/t4.** The t2 NRILLU rate is taken at signing; admin fee and entry charge instead follow the movement date.
3. **FX rates must be normalized.** NRFXRT contains 80 rows with a lowercase currency code (`usd`, `chf`…) precisely on the days when the uppercase row is missing. With a case-sensitive lookup **454 policies** have at least one wrong movement, hence a wrong t3 for all of them (count over all rows: `data_checks.py --sample 0`; with the default sample the script sees 22).
4. **The premium trade date follows the fund's price calendar**, not the Ticino calendar: 100% versus 99.52%.
5. **Premiums and deductions use different FX dates.** Premiums: last fixing before the trade date. Deductions: fixing at the trade date.
6. **`t3_booking` is the gold mine: 5 million labeled examples.** Every brick closes on its own, and t4 is the exact sum of these movements.
7. **t5 is simpler than a positive-unlabeled problem.** All corrections are integer deltas; the NREXCP timestamp points to the exact row.
8. **Fewer tools.** All I needed were polars, `decimal`, `holidays` and exact-row counts. PySR, OpenEvolve, ShinkaEvolve, Z3 and Desbordante remain a plan B, at most for the risk charge.
9. **The maintainability index is a goal, not a constraint.** The document suggests treating it "as a constraint". With one module per business concept, docstrings that state the rule, and conventions as data, you reach **94.6 without losing a single row of accuracy** (§5). The score is decided on both axes.

> **What to do now.** Tonight, make the first submission with `my_solution/` (t0 and t1 already done, MI 94.6). From tomorrow morning the whole team works on t3, brick by brick against `t3_booking`, starting from the only two bricks still open, **AMC** and **RSK**. One person drives t2 in parallel. Every merge passes two gates: the accuracy harness and the MI harness.

**The assessment, in brief.** Method: right. The document's 27 hypotheses and choices put to the test (§2): 12 confirmed, 9 to correct, 2 refuted, plus 4 aspects the document did not anticipate. Timeline: cautious, it can be brought forward by half a day. Tools: oversized. Maintainability: to be promoted to a goal.

---

## 1. What I did and how to read this document

**The procedure** is the same one I propose to the team in §6.

1. I read the challenge text, the document, `SCHEMA.md` and the starter kit (`README.md`, `check.py`, `scoring.py`, the `submission.py` stub).
2. I loaded the 27 tables with a generic loader driven by `NRDICT`: types, implied decimals and dates are read from the dictionary, not written column by column.
3. For each hypothesis in the document I implemented the simplest rule and counted the exact rows against the train targets and diagnostics. Then I tried 2 to 5 variants and kept the best one only if the gain was clear-cut and explainable in one sentence.
4. When residuals remained, I grouped them by dimension (era, currency, fund, day, product…) until the hidden condition became evident.
5. I wrote t0 and t1 as a real submission, measured them with the official `scoring.py`, and raised the maintainability index from 83.3 to 94.6 in seven steps, without losing accuracy (§5.3).

**Reproducibility.** `tools/data_checks.py` prints every number in this document; the expected output is in `tools/data_checks_expected.txt`. The script reads the targets, so it is an analysis tool and does **not** go into the submission.

**Outcome legend** used in the tables:

- **CONFIRMED**: the data agree with the document.
- **TO CORRECT**: the idea is right, but the detail is wrong, incomplete or more complicated than necessary.
- **REFUTED**: the data say otherwise.
- **NEW**: the document did not anticipate it.

**What I did not do.** I did not simulate t3 or t2 in full. AMC, RSK, the split of the admin fee across funds and pots, and the t2 projection remain to be closed: §4 says where to start. I did not use the leaderboard.

---

## 2. The team's strategy document tested against the data

| # | Hypothesis or choice in the document | What the data say | Outcome |
|---|---|---|---|
| 1 | Program synthesis under an exactness constraint: count exact rows, not average errors | Every correct rule reaches 100% by changing a single convention; the wrong variants stay between 81% and 99.5%. The exact count separates them unambiguously | **CONFIRMED** |
| 2 | The first tool is the diff harness | It is what made everything else possible: every hypothesis becomes a number in a few seconds | **CONFIRMED** |
| 3 | `CYYMMDD` dates with 6 or 7 digits, sentinels `0` and `9999999` | True. In addition, 10 impossible birth dates (30.2, 31.4, 31.6, 31.9, 31.11), 8 on train policies: the starter kit's `day()` crashes | **NEW** |
| 4 | Codes of Swiss-German origin (LS, UB, E, L) | True, and there is more: `PS_SMOKE` uses `J`/`N` (Ja/Nein) while `SCHEMA.md` says `Y`/`N`. With `== 'Y'` nobody comes out as a smoker (749 are) | **NEW** |
| 5 | 23 tables in five groups | There are 27: the tax module is missing (`NRHOLD`, `NRADDR`, `NRTAXR`, `NRTAXB`), with empty amounts and a retroactive version in `NRTAXR` | **NEW** |
| 6 | Find the COBOL → Java switch by counting the decimals of the units | Unnecessary, and it would not work: the switch is event 800 of 2007-08-11 and units have 6 decimals in both eras | **REFUTED** |
| 7 | Truncation in COBOL, half-up in Java | 100% true on invested amounts, units and surrender value (where COBOL truncates the net amount, not the penalty) | **CONFIRMED** |
| 8 | Tariffs locked at the application date, "to be verified table by table" | t2: yes, the NRILLU rate is the one at signing (7/7 decisive cases). t3/t4: no, admin fee (84 → 90 → 102 → 120 per year on FK) and entry charge (tier B from 4% to 3% from 1.7.2021) follow the movement date. The "table by table" caution was right | **TO CORRECT** |
| 9 | "As-of" lookup on NRPOLH, the broker can change | Broker valid at the money date (`PR_RCVDT`): 99.9956%. First broker: 99.23%. Current broker: 99.36% | **CONFIRMED** |
| 10 | Exclude reversed premium items by matching each event 900 to its premium item | Simpler: the premium items with `PR_STATE = 'P'` count (225,858, i.e. exactly the t0 rows). `R` = reversed debit, `O` = open, `W` = written off | **TO CORRECT** (simplify) |
| 11 | Schedule: drift 31 → 28 → 28, new anchor after changes | True, with the key: the drift exists only in the COBOL era; Java keeps the anchor day fixed. Hybrid rule 100%; anchor only 98.35%; chain only 92.60% | **CONFIRMED** (refined) |
| 12 | Ticino calendar; Good Friday is not a holiday | Correct: the 158 LS premium items of 26.3.2027 are collected the same day. 8.12, 6.1, 19.3, Easter Monday, Ascension Day, Whit Monday, Corpus Christi and 29.6 move the collection | **CONFIRMED** |
| 13 | LS collection: next business day, or modified following, or brought forward by a few days (LSV+) | The first hypothesis holds: forward only, even past the end of the month (261 collections move to the next month, e.g. 31.10.2026 → 2.11.2026). For UB the collection coincides with the due date, even on holidays | **CONFIRMED** (the first of the three) |
| 14 | "Local calendar for collections and trades" | For collections, yes. The premium trade date, however, is the first day after the money date on which **that fund** has a price: 100% versus 99.52% for the Ticino calendar | **TO CORRECT** |
| 15 | Prices: last price on the same day or earlier, the latest publication applies | True (664 republished prices). In addition: premiums buy at the **ask** price, deductions sell at the **bid**, 100% on 5 million movements | **CONFIRMED** |
| 16 | "To be verified whether the as-of lookup also applies to FX rates" | Yes, but with two surprises: the lowercase codes to normalize (§3.3) and the premium FX rate, taken the day before the trade date (§3.2) | **TO CORRECT** |
| 17 | Identifiability example: 103.95 = 11 × 9.45 or 7 × 9.45 + 5 × 7.56 | Wrong premise. The premium is 315.00, not 236.25; in 2021 there are 9 premium items (premium suspension from September). Tier B: 6 × 12.60 + 3 × 9.45 = 103.95. The data resolve the ambiguity in a minute | **TO CORRECT** |
| 18 | Java `double` artifacts | Tested on units: Decimal and double give the same result row by row. The residuals were the lowercase FX rates | **REFUTED** (for units) |
| 19 | t2: policy version at signing, bisection on the yearly values | Projection years = term (3,019/3,019); final value = last year (3,011/3,019: the 8 differing cases are manual corrections) | **CONFIRMED** |
| 20 | t3 step by step, restarting from the true state | It is the right technique: `t3_booking` plus the client orders in NRBOOK give the exact units before every deduction | **CONFIRMED** |
| 21 | t4 as an aggregation of t3 | Exact: 99.94% whole rows by summing `t3_booking` per year; the entry charge must be attributed fund by fund | **CONFIRMED** |
| 22 | t5 as a positive-unlabeled problem; study the signature of the corrections | There is a single signature: a whole-franc delta (54/54). The NREXCP timestamp identifies the row | **TO CORRECT** (simplify) |
| 23 | Backtesting t1 on the `PR_DUEDT` | Valid but not necessary: the rule is already at 100% on the targets | **CONFIRMED** (optional) |
| 24 | About 25 tools (PySR, OpenEvolve, ShinkaEvolve, Z3, Desbordante, imodels, wittgenstein, PM4Py, lifelib…) | None of them has been needed so far: the hidden rules are discrete conventions (which date, which rounding, which calendar, which normalization) | **TO CORRECT** (reduce) |
| 25 | The maintainability index is measured "only on the task files" | `scoring.py` measures **all** the `.py` files in the submission folder (`rglob`): tools and visualizations as `.py` inside `my_solution` lower the index | **NEW** |
| 26 | The MI is "very experimental": treat it as a constraint, not as a goal | The MI is worth points and rises with good practices: 83.3 → 94.6 on the same t0 and t1 code, at equal accuracy (§5) | **TO CORRECT** |
| 27 | Plan: t0 at 100% on Saturday morning, t1 on Saturday | t0 and t1 are already written (`my_solution/`); t3 can start on Saturday at 08:00 | **TO CORRECT** |

**What the document got right, and it is worth saying:** the Ticino calendar down to Good Friday, the month-end drift, COBOL truncation, the t2 bisection, the t3 decomposition, t4 as an aggregation, precision first in t5, rules as data, harness first. It is a solid base, and the corrections make it faster, not different.

---

## 3. The findings that change the plan

### 3.1 The COBOL/Java era is data, not a hypothesis

| Evidence | Value |
|---|---|
| Event 800 "system conversion" | 946 events, all with `EV_EFFDT = 2007-08-11`, source `M` (migration), user `CONV2007` |
| COBOL batch `CBLBATCH` | from 1994-01-01 to 2007-08-10 |
| Java batch `NGBATCH` | from 2007-08-11 to 2026-06-30 |
| Unit precision | 6 decimals in all years: counting significant digits does not see the switch |

**How to use it:** a single constant, `ERA_SWITCH = 2007-08-11`, and a single function `rounding(day)` (truncation before, half-up after). The date that decides the era is the date of the operation: the trade date for movements, the valuation date for the surrender, the due date for the schedule. For t2 the natural hypothesis to test first is the application date, because the offer was computed by the system in force at signing. The t0 commissions also follow the era rule without losing rows: a single rounding policy holds for the whole system.

### 3.2 Which date governs which parameter

Most of the hidden rules come down to choosing the right date. The document had said so, and this is the measured table:

| Quantity | Date that governs it | Evidence |
|---|---|---|
| Broker and tier for the commission (t0) | money date `PR_RCVDT` | 99.9956% (due date: 99.9947%) |
| Tier and entry charge of premiums | money date | invested amount: 100% in both eras |
| Fund allocation (NRALLO) | money date (on a tie the highest version wins) | ditto |
| Admin fee (NRCHRG) | deduction date | 397,841 / 397,842 monthly charges (the exception is a policy that ran out of value) |
| Offer growth rate (NRILLU, t2) | application date `PH_APPDT` | 7 / 7 policies signed before and started after a rate change |
| Trade date of a premium | first day after the money date on which **the fund** has a price | 567,833 / 567,833 |
| Price of a premium | ask at the trade date | 100% |
| Price of a deduction | bid at the last price ≤ deduction date (which can fall on a Saturday or Sunday) | 100% |
| FX rate of a premium | last fixing ≤ trade date − 1 day | 100% (with normalized codes) |
| FX rate of a deduction | last fixing ≤ trade date | 100% (with normalized codes) |
| Surrender penalty | completed years from `PH_BEGDT` to the valuation date; no penalty in NRWAIV periods | 100% of the rows without a manual correction |

### 3.3 The traps in the data (none was anticipated by the document)

| Trap | Where | Effect if you ignore it | Remedy |
|---|---|---|---|
| 10 impossible birth dates (`710230` = 30.2.1971, `541131` = 31.11.1954…) | `NRPERS.PS_BIRTH`, 8 on train policies | decoder crash, or wrong age in the risk charge | tolerant decoder (in `my_solution/legacy/formats.py` they become `None`); the age convention must be chosen by testing (COBOL integer arithmetic on `YYYYMMDD` dates also works with impossible dates) |
| `PS_SMOKE` is `J`/`N`, not `Y`/`N` | `NRPERS` | no smokers, wrong risk charge for 749 people | compare with `'J'` |
| 80 FX rows with a lowercase code | `NRFXRT.FX_CCY` | 454 policies with at least one wrong unit amount: t3 lost | `upper()` on the currency code |
| 664 republished prices | `NRFPRC` | wrong price | the latest `FP_CHGTS` applies |
| Prices and FX rates up to 2026-07-31 | `NRFPRC`, `NRFXRT` | none, if the lookup is as-of | do not filter at extraction |
| Deduction capped at the available value | 1 case (BL10001005) | policy value −0.03 | surrender = `max(0, …)` |
| Tax module with empty amounts and a retroactive version (`IT BOL` version 2 of 15.7.2019) | `NRTAXR`, `NRTAXB` | none for t0–t4 | ignore it for the score; see §3.7 |
| 10,587 train PRM movements not "counted" | `NRBOOK` vs `t3_booking` | reversed premiums invested by mistake | invest only the `P` premium items |

### 3.4 `t3_booking`: five million labeled examples

The diagnostic file contains amount, price and units of 5,024,847 movements: 407,636 PRM, 1,827,505 ADM, 1,833,960 AMC and 955,746 RSK. It is the most powerful tool in the challenge, because it turns the thirty-year, path-dependent simulation into millions of independent equations:

- **the true state** before every deduction is rebuilt by summing the units of `t3_booking` and of the client orders (`SWO`, `SWI`, `WDR`, `SUR` and `DTH`, complete in NRBOOK: 24,912 rows, which `legacy.table(..., "BK_BKTYP", (...))` reads in 0.8 s);
- **every deduction** then becomes an isolated test: amount = f(value before the deduction, rate, age…).

This is how AMC and RSK get closed without simulating anything. Only when every brick is at 100% "given the true state" do we chain the full simulation. It is exactly the document's "step-by-step verification", taken all the way.

### 3.5 t4 is a sum, exact to the cent

Summing `t3_booking` by policy and trade-date year gives 99.94% whole rows. All 20 differing rows are manual corrections of the admin fee, with an integer delta. Two details matter:

- **premiums** by money-date year, **charges** by movement-date year;
- the **entry charge** is computed per individual fund (gross share of the premium minus invested amount) and goes into the trade-date year **of that fund**. A late-December premium can trade one fund on the 31st and another in January. Attributing everything to the first trade date, 36 rows break, in pairs, across the year boundary.

Practical consequence: **t4 requires no work of its own**, only a correct t3.

### 3.6 t5: one signature for all corrections

| Task | Corrections found in train | Of which in NREXCP | Signature | How NREXCP points to the row |
|---|---|---|---|---|
| t0 | 10 | 6 | integer delta (from +9.00 to +77.00) | premium item due shortly before `EX_TSTMP` (6/6) |
| t2 | 8 | 5 | integer delta (from −3,955.00 to +4,855.00); the yearly trajectory stays correct | the policy |
| t3 | 16 | 11 | integer delta (from +15.00 to +499.00); surrender value **greater** than the policy value | last valuation date before `EX_TSTMP` (11/11) |
| t4 | 20 | 16 | integer delta on the admin fee (from +7.00 to +147.00) | year = year of `EX_TSTMP` − 1 (16/16) |
| t1 | 0 | 0 | — | — |
| **Total** | **54** | **38 (70%)** | **54/54 integer deltas** | |

The reasons in NREXCP ("manuell korrigiert 2019, Kundenkulanz" with timestamps from other years) are noise: the timestamp is what counts. A t5 based on NREXCP alone would reach at most F1 ≈ 0.82; with the rules at 100% and the integer-delta filter we aim for 1.

### 3.7 Starter kit and evaluation: the practical pitfalls

| Fact | Consequence |
|---|---|
| `scoring.py` uses `zip(strict=True)`: it needs **Python ≥ 3.10**, and the system Python here is 3.9.6 | create a Python 3.14 environment right away (`uv venv --python 3.14`), the version of `.python-version` |
| The stub's `csv.DictReader` loader loads NRBOOK in 6.5 s but takes **about 3 GB of RAM**; polars reads it in 0.2 s | polars for I/O, filter the large tables before conversion, `Decimal` in the arithmetic |
| Only the target keys are evaluated: **extra keys cost nothing**, missing ones do | generate all plausible keys (due dates, years, dates) |
| t3 is evaluated only on `surrender_value`; `policy_value` is diagnostic | the diagnostic serves to separate value and penalty |
| `Decimal`s are compared by value (2.50 = 2.5) | no formatting issue |
| The manual corrections are in the local targets but **excluded** from the official evaluation | locally 100% is unreachable on t0, t2, t3, t4: see the ceilings in §4.0 |
| The maintainability index is computed on **all** the `.py` files in the folder, but the README asks to hand in the tools there too | t6 tools as notebooks or HTML in `my_solution/tools/`; ask the organizers (§4.7) |
| The tax module has an empty `TB_AMOUNT` "like NRBOOK" | it is the natural candidate for the **generalization** score: "tomorrow the client asks for taxes". Do not touch it now, but design the harness and the loader so that a new target can be added in an hour |

---

## 4. Confirmed rules and targets, task by task

### 4.0 Accuracy targets and local ceilings

The goal is **100% on every task from t0 to t4 in the official evaluation**, which excludes manual corrections. Locally, with `check.py`, the corrections remain in the targets, so the official 100% corresponds to these ceilings:

| Task | Train rows | Manual corrections found | Local ceiling (= official 100%) | Status |
|---|---|---|---|---|
| t0 | 225,858 | 10 | 99.9956% | **reached** |
| t1 | 15,028 | 0 | 100% | **reached** |
| t2 | 3,019 | 8 | 99.735% | structure clear, formula to close |
| t3 | 6,153 | at least 16 | 99.740% | bricks ready, AMC and RSK to close |
| t4 | 34,145 | 20 | 99.941% | rule ready, depends on t3 |
| t5 | — | 54 | F1 → 1 | recipe ready |

Rule of thumb: **never chase a row whose delta is a whole number of francs**. It is a manual correction: it does not count for accuracy and it is worth points in t5.

### 4.1 t0 Commissions: 99.9956% (ceiling reached)

```text
rows          NRPREM premium items with PR_STATE = 'P'
version       NRPOLH row valid at PR_RCVDT (VLDFR ≤ d ≤ VLDTO; on a tie, the highest version)
tier          NRBROK[version.PH_BRKNR].BR_TIER
premium type  6th character of RK_TARKEY: L regular, E single
rate          NRCOMR(tier, type) valid at PR_RCVDT
commission    round_era(PR_AMTRC × rate, 2)       (in practice always half-up: no row changes)
```

| Variant | Exact rows |
|---|---|
| broker at the money date, half-up | **225,848 / 225,858 (99.9956%)** |
| broker at the money date, half-even | 225,847 |
| broker at the money date, truncation | 225,846 |
| broker at the due date, half-up | 225,846 |
| current broker | 224,418 (99.36%) |
| first broker | 224,130 (99.23%) |

The 10 residuals all have an integer delta and 6 are in NREXCP: they are manual corrections, so **they are left alone** (Appendix B). Implementation: `my_solution/billing/commission.py`, 1.1–2.1 s.

### 4.2 t1 Next due dates: 100%

```text
population   policies whose version valid at extraction has PH_STATE = 10 and PH_FREQ ≠ 'E'
period       M = 1, Q = 3, H = 6, J = 12 months
anchor       if PH_BEGDT ≥ 2007-08-11: anchor = PH_BEGDT
             otherwise: COBOL chain from PH_BEGDT (previous due date + period, day capped
             at month end, hence with drift) up to the last due date before 2007-08-11;
             that date is the Java anchor
due dates    anchor + k × period, anchor day capped at month end (no drift)
window       extraction < due date ≤ extraction + 1 year, and due date < PH_ENDDT
collection   LS: first Ticino business day ≥ due date (Mon–Fri, TI holidays, Good Friday a business day)
             UB: equal to the due date
```

| Schedule rule | Exact rows |
|---|---|
| anchor from `PH_BEGDT` only | 14,780 / 15,028 (98.35%) |
| chain from `PH_BEGDT` only (always drifts) | 13,916 / 15,028 (92.60%) |
| **hybrid COBOL/Java** | **15,028 / 15,028 (100%)** |

The calendar is generated with `holidays.CH(subdiv="TI")`, which works offline for 2027 too and matches Neuron's on every date checked. No manual corrections in t1. The extraction date comes in as a parameter, so no fixed dates in the code. Implementation: `my_solution/billing/schedule.py` and `collection.py`, 0.7 s.

### 4.3 t2 Projected value: the structure is clear, the formula still has to be closed

**What is certain:**

- one row per policy year, and the number of years equals the term (3,019/3,019);
- the final value coincides with the last year of the trajectory (3,011/3,019): the 8 differing cases are manual corrections with an integer delta;
- **the growth rate is the NRILLU rate at the application date.** The 7 single-premium policies signed before a rate change and started after it grow at the signing rate. For example BL10000598 (signed 7.12.2011 at 4%, start 2.1.2012 at 3%) grows by 1.0304 a year, like the 4% policies (median 1.0309);
- the median net growth of single-premium policies in the second year is 1.0102 / 1.0154 / 1.0205 / 1.0309 / 1.0413 for rates of 2 / 2.5 / 3 / 4 / 5%, i.e. the rate minus about 0.9–1% of charges: pot 2 management charge, admin fee and risk.

**Recommended test order** (on single premiums first, because they have fewer degrees of freedom):

1. monthly rate `(1+i)^(1/12) − 1` or `i/12`, on the first year of FLSP policies without agreements;
2. entry charge by tier at the application date, then admin fee and AMC at the application date versus those at the projected month (the challenge text insists on "parameters valid at the application date");
3. order of operations within the month (growth then charges, or vice versa) and monthly rounding, with the era decided by the application date;
4. risk charge with increasing age, then regular premiums and the initial pot (`PD_INIMON`: 24 months FK, 12 FX, 0 FS);
5. bisection: for each policy, the first year in which the trajectory diverges points to the missing rule. Group those years by product, frequency and era.

### 4.4 t3 Surrender value: the bricks that are ready and those still to close

**Verified bricks** (exact rows on `t3_booking`, `NRBOOK` and `t3_surrender_value`):

```text
round_era       truncation if the date < 2007-08-11, otherwise half-up
PRM trade date  first day after the money date on which the fund has a price in NRFPRC      567,833/567,833
PRM price       fund ask at the trade date (latest publication)                             407,636/407,636
PRM amount      round_era(PR_AMTRC × allocation share × (1 − entry rate), 2)                100% per era
                entry rate = NRAGRE 'ENT' valid at the money date, otherwise NRENTC(tier at the money date)
                allocation share = NRALLO valid at the money date (highest version)
FX rate         cross via CHF, unrounded: (CHF per policy currency) / (CHF per fund currency)
                currency codes in uppercase; premiums: last fixing ≤ trade date − 1; deductions: ≤ trade date
units           round_era(amount × FX rate / price, 6), negative for deductions             100%
deduction price bid at the last price date ≤ deduction date                                 100%
admin fee       sum of the pieces per fund and pot = CG_ADMFEE valid at the deduction date  397,841/397,842
surrender       max(0, round_era(PV × (1 − penalty), 2))                                    4,619/4,635
                penalty = NRSURR(product scale, completed years since PH_BEGDT); 0 in NRWAIV periods
                (the 2020-04-30 valuation date falls in the COVID waiver: no penalty)
```

**Order and dates of the movements, already verified:**

- within a monthly run (event 300) the movements have increasing IDs fund by fund and pot by pot, in the order **ADM → AMC → RSK**;
- deductions fall on the **monthly anniversary** of the start date. For policies starting on the 29th, 30th or 31st the day is capped at month end but returns to the start day in long months: **no drift, not even in the COBOL era**, unlike the premium schedule (56,948 runs out of 56,948; in total 517,711 runs on the start day and 15,949 capped at month end);
- to be **ignored**: the 208 reversed switches (SWO/SWI of events 200 cancelled by a 900), the 123 SWI of the technical corrections (990) and the 14,284 PRM of reversed premiums.

**Bricks still to close**, each with the hypotheses to test first, always "given the true state":

| Brick | Hypotheses to test | Labels available |
|---|---|---|
| **AMC** management charge | base = value of the fund-and-pot position (units × bid × FX rate) before or after the ADM; rate `CG_AMCP1` for pot 1 and `CG_AMCP2` for pot 2, or the NRAGRE `AMC` agreement valid at the date (a single rate: does it apply to both pots?); monthly `rate/12` or `(1+rate)^(1/12) − 1` | 1,833,960 rows |
| **RSK** risk charge | sum at risk by option: A = 1% of the value (benefit 101%, `RK_SUMIN` = 0 for all 1,836 A policies), B = max(sum insured − value, 0), C = sum insured; qx from NRMORT (table `CG_MORTTB` by generation: M94U for 01/02, M12U for 03/04; sex: M → 1, W → 2, U → the person's sex); age at last birthday, at nearest birthday or by integer arithmetic; factor `(1 + RK_LOAD)`; × `CG_SMKFAC` = 1.5 if `PS_SMOKE = 'J'`; qx/12 | 955,746 rows |
| **ADM split** (and AMC/RSK split) across funds and pots | proportional to the value of each position; who gets the rounding remainder (largest piece? last fund?) | 1,827,505 rows |
| **Pot 1 and pot 2** | pot 1 for the premiums of the first `PD_INIMON` months (24 FK, 12 FX, 0 FS): by due date or by trade date? | NRBOOK column `BK_POTCD` |
| **Start of deductions** | the first monthly anniversary with units in the portfolio (BL10000001: first premium item unpaid, first deduction in May and not in April) | deduction dates in NRBOOK |
| **Order within the day** | premium, deduction run and client order on the same day: in which order? (within the run the order is already known) | `t3_holding` |
| **Policy value** | units × bid at the last price ≤ valuation date × FX rate, summed over funds and pots; rounding per position or on the total | `t3_holding`, `policy_value` |
| **States 60/70** | surrender or death before the valuation date: value 0 (1,518 target rows are 0) | `t3_surrender_value` |

### 4.5 t4 Annual statement: exact aggregation of t3

```text
premiums         Σ PR_AMTRC of the 'P' premium items, by year of PR_RCVDT                   100%
entry_charges    Σ, PRM movement by PRM movement, of (PR_AMTRC × allocation share −
                 invested amount), by year of that movement's trade date                    100%
admin_fees       Σ ADM amounts by year of the deduction date                                99.94% (20 manual corrections)
management_fees  Σ AMC amounts by year                                                      100%
risk_charges     Σ RSK amounts by year                                                      100%
total_charges    entry + admin + management + risk
years            from the start year to the year of surrender or death, 2025 at the latest
```

### 4.6 t5 Outliers: the recipe

```text
1. compute with the rules all the task values for the policies present in targets_dir
2. candidates = rows where target − computed value ≠ 0
3. keep only the candidates with a whole-franc delta       ← signature shared by the 54 corrections found
4. add the rows pointed to by NREXCP, mapped via the timestamp:
      t4: year = year(EX_TSTMP) − 1;  t3: last valuation date < EX_TSTMP;
      t0: premium item due just before EX_TSTMP (confirmed by the integer delta);  t2: the policy
5. precision first: a non-integer delta is a missing rule, not a correction
```

The keys must have the target format: `("t3_surrender_value", ("BL…", date))`, `("t4_annual_statement", ("BL…", year))`, `("t0_commission", ("BL…", due_nr))`, `("t2_projected_maturity_value", "BL…")`.

### 4.7 t6 Visualizations and tools: what to hand in

t6 is not done on Sunday: **it is built while we work**, because every tool serves first of all to find the rules. On Sunday it gets packaged. Each of these guided one of tonight's findings or will guide tomorrow's:

| # | Tool | What it makes visible | Status |
|---|---|---|---|
| 1 | **Verification harness** (`data_checks.py`) | every hypothesis becomes a number; table of variants per task | ready |
| 2 | **MI file by file** (`mi_report.py`) | where to act on maintainability, like the residuals do for accuracy | ready |
| 3 | **Residuals by era and by processing date** | the jump at 2007-08-11 (t1, PRM amounts, surrender) | to package |
| 4 | **Calendar heatmap of LS collections** | the Ticino holidays and Good Friday as a "business day" | to do (Saturday, P4) |
| 5 | **Policy timeline**: premiums, deductions, units, value, state | the first tool to build for t3 (BL10000013 and BL10000001 are excellent cases) | to do (Saturday morning, P2) |
| 6 | **Annual statement waterfall**: premiums → entry → admin → AMC → risk | consistency between t3 and t4 | to do (Saturday evening, P2) |
| 7 | **Histogram of deltas per task** | the integer deltas of manual corrections versus rule errors (±0.01, drifts): it is the visual explanation of t5 | to do (Sunday, P1) |

**Where and in what format.** The starter kit README asks to hand in the tools **inside** `my_solution`, but `scoring.py` computes the MI on **all** the `.py` files in that folder, whereas the challenge text says only the task files count. Until the organizers clarify: tools in `my_solution/tools/` as **notebooks (`.ipynb`) and HTML pages**, which do not enter the calculation, and the question put to the organizers on Saturday morning. If the tools must be `.py`, they must be written with the same rules as §5.

---

## 5. Maintainability: how to reach MI 95

### 5.1 How radon computes the index (verified against the radon 6.0.1 source code)

`scoring.py` computes, for every `.py` file in the submission folder (subfolders included):

```text
MI = (171 − 5.2·ln V − 0.23·G − 16.2·ln LLOC + 50·sin(√(2.46 · C in radians))) · 100 / 171,  clamped to [0, 100]
```

and then the **average over files weighted by lines of code**. The four ingredients:

| Symbol | What it measures | How it weighs | Measured fact |
|---|---|---|---|
| **LLOC** | logical lines (statements) of the file | the heaviest term: doubling the file costs ~6.6 points | the same code in a single file scores **11.3**; split into 8 cohesive modules it scores **66.8** per file |
| **V** | Halstead volume: arithmetic, logical and comparison operators and operands | logarithmic | **function calls do not count**: a file of calls only has V = 0 and MI 100 |
| **G** | total cyclomatic complexity (if, for, while, and, or, except, comprehension) | linear, 0.13 points per branch | counts, but less than the others |
| **C** | `#` comment lines + **multi-line** docstring lines, as a % of the lines of code | up to **+29 points**, peaking around 55% | a **one-line docstring is worth zero**: same function, MI 81.1 with a one-line docstring, 100 with two lines |

**The comment curve** (same 20-line function, increasingly long docstring):

| Comment/docstring lines relative to code | 0% | 18% | 36% | **55%** | 73% | 109% | 182% | 273% |
|---|---|---|---|---|---|---|---|---|
| MI | 50.9 | 73.0 | 78.2 | **79.7** | 79.1 | 74.7 | 60.4 | 42.4 |

Too many comments make the index **drop**. The good band is between 40% and 80%.

**A data-only module** (conventions, tables) has V = 0 and MI 100: the document's "rules as data" are also the best choice for the index.

### 5.2 The ten writing rules

1. **One module per business concept**, at most about 30 logical lines. If it grows, split it by concept (`premiums`, `collection`, `valuation`…), never arbitrarily.
2. **Multi-line docstrings** for every module and every non-trivial function: the rule in business language and the evidence ("225,848 exact rows out of 225,858"). They are what the auditor reads, and they raise the index.
3. **Comment/code ratio between 40% and 80% per file**, measured with `mi_report.py`: neither sparse nor verbose.
4. **Conventions are data** in `conventions.py`, each with a comment citing the source: MI 100 and a single page for the auditor.
5. **Arithmetic lives in a few helpers** (`money.py`, `months.py`, `business_days.py`); the rule modules compose calls, which do not weigh in the volume.
6. **Tables instead of `if` chains**: `{"D": day, "N": number}.get(kind, str.strip)`.
7. **Functions with complexity ≤ 5**: comprehensions, `filter` and `itertools` instead of nested loops with conditions.
8. **Standard libraries for standard problems**: `relativedelta` for month arithmetic with month ends, `strptime` for dates, `holidays` for public holidays. Less code, less volume, more trust from the auditor.
9. **Domain names**: `paid_items`, `version_on`, `collection_day`, `pays_premiums`.
10. **No tool or probe `.py` files inside `my_solution`**: `scoring.py` measures all the `.py` files in the folder. Probes live outside; the t6 tools to hand in go into `my_solution/tools/` as notebooks or HTML (§4.7).

**What not to do:** padding with empty comments (beyond 80–120% the index drops, and the auditor notices); fragmenting into three-line modules without a concept; hiding logic in strings or `eval`; removing correctness checks to lower complexity. The index must rise because the code improves, not instead of improving it.

### 5.3 The proof: t0 and t1 from 83.3 to 94.6 without losing a row

Every step is measured with the official `check.py` (accuracy) and `scoring.maintainability` (MI):

| Step | What changed | MI | t0 | t1 |
|---|---|---|---|---|
| 1 | first working version, seven modules | 83.3 | 99.9956% | 100% |
| 2 | docstrings with rule and evidence, comment ratio at 55–65% | 86.8 | = | = |
| 3 | cohesive modules: `formats` (legacy formats), `lookup` (validity), `portfolio` (versions) | 90.4 | = | = |
| 4 | standard libraries: `strptime` (CYYMMDD + 19,000,000), `relativedelta`; collection in `collection` | 91.7 | = | = |
| 5 | reusable concepts: `premiums` (paid premium items, premium type), `pays_premiums` in the portfolio | 92.6 | = | = |
| 6 | `dates` split into `months` and `business_days`; `submission` only composes, the rules work on one premium item or one policy | 93.2 | = | = |
| 7 | comment ratio brought back between 40% and 80% in the small files (with too many docstrings the index was dropping) | **94.6** | **99.9956%** | **100%** |

The MI file by file at the end:

| Module | MI | Module | MI | Module | MI |
|---|---|---|---|---|---|
| `submission.py` | 100 | `conventions.py` | 100 | `money.py` | 100 |
| `months.py` | 100 | `collection.py` | 99.5 | `premiums.py` | 98.5 |
| `lookup.py` | 97.8 | `commission.py` | 96.2 | `formats.py` | 89.9 |
| `business_days.py` | 89.9 | `portfolio.py` | 89.5 | `legacy.py` | 89.3 |
| `schedule.py` | 88.6 | | | | |

### 5.4 The architecture of the complete submission, with each module's budget

> Superseded on 17 October: the code now follows the seven packages of `my_solution/ARCHITECTURE.md`. The table below is the budget planned on Friday.

| Module | Concept | Task | LLOC budget |
|---|---|---|---|
| `submission.py` | the 6 functions, composition only | all | 25 |
| `conventions.py` | the knobs (Appendix C), data only | all | free (MI 100) |
| `formats.py`, `legacy.py`, `lookup.py` | formats, reading, validity | all | 20–25 each |
| `portfolio.py`, `premiums.py` | policies and versions; premium items | all | 20 each |
| `money.py`, `months.py`, `business_days.py`, `collection.py` | rounding and amounts; months; business days; collection | all | 20 each |
| `commission.py`, `schedule.py` | t0, t1 | t0, t1 | 20–25 |
| `market.py` | ask/bid prices at the latest publication, price days, as-of FX rates in uppercase | t3 | 25 |
| `investment.py` | premium → units: trade date, entry, allocation, pot | t3, t4 | 25 |
| `charges.py` | ADM and AMC: amounts and split across funds and pots | t3, t4 | 25 |
| `risk.py` | RSK: sum at risk, qx, age | t2, t3 | 25 |
| `orders.py` | client orders from NRBOOK | t3 | 15 |
| `accounting.py` | positions per fund and pot over time | t3, t4 | 30 |
| `valuation.py` | policy value, penalty, surrender | t3 | 20 |
| `statement.py` | annual sums | t4 | 20 |
| `projection.py` | offer projection | t2 | 30 |
| `outliers.py` | integer deltas and NREXCP | t5 | 25 |

With these budgets and the rules of §5.2 the estimate is an overall MI around 95: the 13-module skeleton is already at 94.6.

### 5.5 The maintainability gate in the process

- **Before every merge:** `python -B $REPO/tools/mi_report.py $REPO/my_solution` (variables as in Appendix D). The overall MI **never drops below 94** (final target ≥ 95); no file below 85; a file above 30 logical lines gets split by concept.
- **MI is maintained, not recovered.** Two hours of refactoring on Sunday are not enough for a 300-line monolith (MI 11 in the §5.1 test). Write in the right style from the start.
- **The same rigor as for accuracy:** every MI intervention is measured, and if accuracy drops by one row it is rolled back.

---

## 6. How I would proceed: the operating method

### 6.1 The 30–45 minute loop

1. **Isolate the smallest sub-problem that has a label.** "Units of PRMs in foreign currency", not "t3".
2. **Write the simplest rule** that follows from the task description.
3. **Count the exact rows.** Only the count decides.
4. **If it is not 100%, group the residuals** by era, year, product, currency, fund, tier, frequency, day of month, day of week, holiday, state. The dimension in which they cluster is the hidden condition. Three examples from tonight: the t1 residuals were all on days 29–31 and in the COBOL era; the unit residuals were on various currencies on specific dates, i.e. the lowercase codes; the trade-date residuals all fell on days without a fund price.
5. **Formulate 2 to 5 concrete variants** and measure them all in the same run.
6. **Accept a variant only if** it improves clearly, does not worsen other rows and can be explained in one business sentence. Then record it in the hypothesis log and in `conventions.py`.
7. **Write it straight away in the §5 style**: the module of its concept, docstring with rule and evidence, MI measured.
8. **If a few isolated rows with an integer delta remain, stop**: they are manual corrections and go into t5.

### 6.2 The rules of engagement

- **No discussion without a number.** "I think it's half-even" is not an argument; "225,847 versus 225,848" is.
- **One knob at a time, but all its variants together.**
- **Never bend a rule for an isolated row.** Manual corrections are excluded from accuracy and are worth points in t5.
- **The public leaderboard is a thermometer, not a compass.** Check it after every submission; do not use it to choose rules.
- **No hard-coded parameters.** Valuation and extraction dates come in as arguments; the regime dates live in `conventions.py`.
- **45-minute time-box per hypothesis family.** If nothing moves, switch sub-problem or call in a second pair of eyes.
- **Two gates for every merge:** the accuracy harness and `mi_report.py`.
- **A single source of truth for conventions**, shared by everyone: every finding immediately improves everyone else's numbers.

### 6.3 The hypothesis log

A Markdown table, updated on every iteration: it becomes the heart of the README and the proof of method for the generalization score. The first rows are tonight's:

| ID | Hypothesis | Test | Result | Decision |
|---|---|---|---|---|
| H01 | Broker valid at the money date | t0, 4 bases × 3 roundings | 99.9956% versus 99.9947% (due date) | adopted |
| H02 | Schedule: COBOL chain, Java anchor | t1, 3 rules | 100% versus 98.35% and 92.60% | adopted |
| H03 | LS on the first TI business day, even past month end | t1 | 100% (261 collections move to the next month) | adopted |
| H04 | PRM amount truncated in COBOL, half-up in Java | 60,000 PRM | 100% / 100% | adopted |
| H05 | Trade date = first day with a fund price | 567,833 PRM | 100% (TI calendar: 99.52%) | adopted |
| H06 | Currency codes in uppercase | 1,548,688 cross-currency movements | 100% (case-sensitive: 99.87%, 454 policies) | adopted |
| H07 | double artifacts in units | 120,000 movements | no difference | rejected |
| H08 | NRILLU at the application date | 7 straddling policies | 7/7 | adopted (t2) |
| H09 | Era rounding for commissions too | t0 | 225,848, unchanged | adopted: a single rounding policy |

### 6.4 AI in the loop

- **The LLM writes the probes, the harness decides.** The most productive prompt contains the harness command, the grouped-residuals report, `conventions.py`, the hypothesis log and the request for "three variants with the rule in one sentence, implemented as configuration".
- **One probe, one hypothesis, one number.** Tonight I ran about thirty of them in a few hours; none required PySR, Z3 or an evolutionary algorithm.
- **The LLM is useful for the MI too:** give it the output of `mi_report.py` and the module, asking it to split by concept and write the docstrings with the rule. Then re-measure accuracy and MI.
- **The heavy tools remain plan B.** If the risk charge resists the grid (age × table × factors × rounding), then yes: interval reasoning for the implicit loading (see the document), decision trees on the residuals (`scikit-learn`), and only then Z3 or symbolic search.
- **Never let generated code into the submission without the two gates.**

### 6.5 The roles

**With four people:**

| Person | Responsibility | Friday night | Saturday | Sunday |
|---|---|---|---|---|
| **P1, data, harness and quality** | `legacy.py`, `conventions.py`, harness, `mi_report`, submissions, timings | copy of the skeleton, first submission | reconstruction of the true state for P2 and P3; integration; MI guardian | t5, robustness, final submission |
| **P2, unit accounting** | `market`, `investment`, `orders`, `accounting`, `valuation` | environment and reading of §4.4 | t3 engine, `t3_holding`, policy value | surrender and t4 (`statement`) |
| **P3, deductions** | `charges`, `risk` | environment and reading of §4.4 | AMC and RSK at 100% given the true state | t3 support, docstrings |
| **P4, projection** | `projection`, then t6 and README | environment and probe on the monthly rate | t2 with the bisection; shares `risk` with P3 | t6, README, hypothesis log |

**With three people:** P1 also takes t2; P2 and P3 stay on t3.

**Ritual:** every three hours, ten minutes in front of the two tables (accuracy per task and MI per file): what changed, what is blocked, who helps whom. **Definition of "done"** for a brick: at least 99.9% on its diagnostic, residuals explained (integer deltas or known cases) and a module with MI ≥ 85.

---

## 7. The plan: the moves until Sunday at 16:00

### 7.0 Coverage of the seven tasks

The plan completes **all seven tasks**: the five scored on accuracy and the two bonus ones.

| Task | Where it closes | Who | Exit criterion | Status on Friday at 23:45 |
|---|---|---|---|---|
| **t0** Commissions | Move 1 | P1 | local ceiling 99.9956% | **done** (`my_solution/`) |
| **t1** Next due dates | Move 1 | P1 | 100% | **done** (`my_solution/`) |
| **t2** Projected value | Moves 3–5, in parallel | P4 | local ceiling 99.735% (= official 100%) | structure and rate known; monthly formula to close |
| **t3** Surrender value | Moves 2–5 | P2 + P3 | local ceiling 99.740% | all bricks at 100% except AMC and RSK |
| **t4** Annual statement | Move 5 | P2 | local ceiling 99.941% | rule verified; comes with t3 |
| **t5** Outliers (bonus) | Move 6 | P1 | on train it recovers the 54 known corrections, no false positives | recipe ready (§4.6) |
| **t6** Visualizations and tools (bonus) | built during the work, packaged in Move 7 | P4 | the seven tools of §4.7 handed in and cited in the README | two out of seven ready (`data_checks.py`, `mi_report.py`) |

The sequence follows the dependencies: **t4 depends on t3**, **t5 depends on the rules of all the other tasks** (every row that does not match is a candidate), and **t2 shares the charge formulas with t3** (`risk.py`, `charges.py`). That is why t3 is the critical path and t5 comes last.

| When | Move | Goal | Done when |
|---|---|---|---|
| Fri 23:30 – 01:30 | **1. Foundations and first points** | shared environment, `my_solution/` checked in place, first submission | `check.py`: t0 99.9956%, t1 100%; MI ≥ 94; leaderboard updated |
| Sat 08:00 – 09:30 | **2. The true state** | positions rebuilt from `t3_booking` and orders; "step by step" harness | every deduction has its "before" value computed |
| Sat 09:30 – 13:00 | **3. The open bricks** | AMC, RSK, split, pots; start of t2 | every movement type ≥ 99.9% given the true state |
| Sat 14:00 – 19:00 | **4. The chain** | month-by-month simulation; `t3_holding`, policy value; t2 with the bisection | `t3_holding` ≥ 99.5%; t2 yearly ≥ 99%; MI ≥ 94 |
| Sat 19:00 – 23:00 | **5. Surrender and t4** | surrender value, t4 by summation, second submission; t2 closed | t3 and t4 at the §4.0 ceilings; MI ≥ 94 |
| Sun 08:00 – 11:00 | **6. t5 and robustness** | t5 recipe; different valuation dates; no crashes; timings | t5 finds the 54 in train; full run measured |
| Sun 11:00 – 13:00 | **7. Polishing** | docstrings, README, t6, MI towards 95 and beyond | MI ≥ 95, README with the hypothesis log |
| Sun 13:00 – 14:00 | **8. Final candidate** | submission, leaderboard check | numbers consistent with the local ones |
| Sun 14:00 – 16:00 | **9. Buffer** | bug fixes only, hand-in by 15:00 | handed in |

### Move 1: foundations and first points (tonight)

- **Why now:** t0 and t1 are already written and measured (`my_solution/`). Submitting them right away earns points and the "perfect match" bonus on t1, and it tests the whole chain: the evaluator's Python, `requirements.txt`, timings.
- **How:**
  1. set `REPO` and `DATA` and create the Python 3.14 environment as in Appendix D;
  2. `python -B $REPO/tools/data_checks.py --data $DATA` (must reproduce `data_checks_expected.txt`);
  3. copy nothing into `$DATA`: the challenge folder stays read-only, `check.py` runs on `--submission $REPO/my_solution`;
  4. `python -B $DATA/starter_kit/check.py --submission $REPO/my_solution --legacy $DATA/legacy --targets $DATA/targets --tasks t0_commission t1_next_due_dates` and `python -B $REPO/tools/mi_report.py $REPO/my_solution`;
  5. submit.
- **Risk:** wanting to rewrite the skeleton. It is fine as it is: extend it, do not redo it.

### Move 2: the true state (early Saturday morning)

- **Why:** it is the multiplier for all of Saturday. With the true positions before every deduction, AMC and RSK become isolated tests instead of a thirty-year simulation.
- **How:** for each policy, sort the `t3_booking` movements and the NRBOOK client orders by date and booking ID; cumulative sum of units per fund and pot; value = units × bid at the movement's price date. It is an analysis tool that reads the targets, so it stays outside `my_solution` (also because of the MI).
- **Done when:** the harness prints, for each deduction type, the exact percentage "given the true state".

### Move 3: the open bricks (Saturday morning)

- **Why:** AMC and RSK are the only real unknowns in t3. Everything else is already at 100%.
- **How:** the §4.4 grid, one knob at a time, residuals grouped. For RSK, start from option A policies (sum at risk = 1% of the value, no sum insured), non-smokers, without medical loading: the cleanest case. Then add smoking (`J`), loading and age. Every closed brick goes straight into its module (`charges.py`, `risk.py`) with its docstring.
- **Risk:** age convention and impossible birth dates. The 8 train policies with impossible dates are the decisive test for choosing between integer arithmetic and calendar arithmetic.

### Move 4: the chain (Saturday afternoon)

- **Why:** only now is simulating worthwhile, because every step is already right given the right state.
- **How:** an event engine per policy: premiums (trade date, ask price, pot), monthly deductions (dates, bid price, order), client orders taken from NRBOOK, exclusion of reversals (900) and technical corrections (990). Comparison with `t3_holding` at the three dates; the first discrepancy per policy points to the wrong step.
- **In parallel:** P4 closes t2 with the yearly bisection.

### Move 5: surrender and t4 (Saturday evening)

- **Why:** with the right positions, surrender and t4 are already verified formulas (§4.4, §4.5).
- **How:** policy value → surrender rule; t4 as a sum per year. Second submission.

### Move 6: t5 and robustness (Sunday morning)

- **t5:** the §4.6 recipe, with precision first.
- **Robustness:** the private valuation dates may be different. Test dates inside the 2008 waiver, straddling the switch (2007-08-10 and 2007-08-11), a Saturday, before the first premium item, after a surrender. The code must never crash on a policy: log the error and carry on.
- **Timings:** full run measured on the entire dataset, with headroom against the limit (unknown: ask the organizers).

### Move 7: polishing (late Sunday morning)

- **MI ≥ 95:** `mi_report.py`, then work on the two or three lowest files, as in §5.3.
- **t6:** the seven tools of §4.7 in `my_solution/tools/`, each with a line in the README on which rule it helped find.
- **README:** approach, rules found, hypothesis log, t6 tools.

### Moves 8 and 9: final candidate and buffer (Sunday from 13:00)

After 14:00 only bug fixes with a test that proves them go in. The last submission must be made by 15:00, not at 15:55.

---

## 8. Risks and submission checklist

| Risk | Likelihood | Impact | Countermeasure |
|---|---|---|---|
| A wrong brick ruins entire policies in t3 (path dependence) | high | high | validate every brick "given the true state" before chaining (Moves 2–4) |
| Private valuation dates different from the train ones | medium | high | parameters; tests on special dates (Move 6) |
| Evaluator time limit exceeded | medium | high | polars, filtering of the large tables, measure from day one, ask the organizers for the limit |
| Different environment (Python < 3.10, library versions) | medium | medium | `requirements.txt` with pinned versions, test in a clean environment |
| MI collapsing when the t3 engine arrives | high | high | line budget per module (§5.4), MI gate at every merge |
| Tool and probe `.py` files inside `my_solution` | high | medium | probes outside the folder; t6 tools as notebooks or HTML; question to the organizers |
| t6 left to Sunday afternoon | medium | medium | tools built during the work (§4.7), only packaged in Move 7 |
| Overfitting to the public leaderboard | medium | medium | rules chosen on train only; the leaderboard serves as a check |
| Divergence between team members | medium | medium | a single harness, a single `conventions.py`, small and frequent merges |
| Crash on a policy with anomalous data | medium | high | try/except per policy with logging; tests on the 10 impossible dates and on the lowercase codes |
| Reading the targets outside t5 | low | disqualification | code review before the final submission |

**Checklist before every submission:**

- [ ] `python check.py` (Python ≥ 3.10) runs on all tasks without errors
- [ ] every task is at its local ceiling (§4.0) or the residual is explained
- [ ] `mi_report.py my_solution`: MI ≥ 95, no file below 85, no file above 30 logical lines
- [ ] total time measured on the entire dataset
- [ ] no reading of target files, except in t5 (`targets_dir`)
- [ ] `valuation_dates` and `extract_date` taken from the arguments
- [ ] no `float` in amounts
- [ ] `requirements.txt` with pinned versions, tested in a clean environment
- [ ] no tool or probe `.py` inside `my_solution`; t6 tools in `my_solution/tools/` as notebooks or HTML
- [ ] README and hypothesis log updated

---

## 9. Appendices

### A. The dataset in numbers

| Item | Value |
|---|---|
| Legacy tables | 27 (23 in the challenge scope + 4 in the tax module) |
| Policies in the export | 4,011: 3,019 train (with targets) and 992 public; about 989 private, not visible |
| Products | FLKL (family FK, initial pot 24 months, scale 1), FLFX (FX, 12 months, scale 2), FLSP (FS, single premium, scale 3) |
| Current states | 10: 2,744 · 20: 91 · 30: 5 · 60: 1,096 · 70: 75 |
| Policy currencies | CHF 2,538 · EUR 1,074 · GBP 199 · USD 200; funds also in SEK |
| Frequencies | M 2,159 · Q 715 · H 100 · J 276 · E 761 |
| Payment | LS 3,269 · UB 742 |
| NRBOOK | 6,797,112 movements (409 MB); the computed ones (PRM, ADM, AMC, RSK) have empty amounts; 24,912 client orders |
| NREVNT | 872,039 events; 946 conversions; 8,130 reversals |
| Targets | t0 225,858 · t1 15,028 · t2 3,019 (+79,040 yearly) · t3 6,153 (+31,578 positions, +5,024,847 movements) · t4 34,145 |

### B. The 54 manual corrections found in train

They are the seed of t5 and the proof that the rules are right: all of them have a whole-franc delta. (N) means the row is listed in NREXCP.

**t0 (policy, premium item, delta):** BL10000237 / 41 / +44.00 (N) · BL10001299 / 103 / +74.00 · BL10001328 / 1 / +77.00 · BL10001567 / 6 / +27.00 (N) · BL10002438 / 11 / +68.00 · BL10002462 / 5 / +16.00 (N) · BL10003175 / 247 / +9.00 (N) · BL10004049 / 6 / +36.00 (N) · BL10004554 / 35 / +11.00 · BL10004722 / 1 / +34.00 (N)

**t2 (policy, delta between final value and last year):** BL10000128 +4,855.00 (N) · BL10001762 +1,574.00 (N) · BL10002196 +1,726.00 · BL10002973 +1,498.00 · BL10003323 +1,947.00 (N) · BL10003583 −1,261.00 (N) · BL10003808 −3,955.00 (N) · BL10004278 +3,294.00

**t3 (policy, valuation date, delta):** BL10000321 / 2025-12-31 / +175.00 · BL10000694 / 2025-12-31 / +358.00 (N) · BL10000768 / 2020-04-30 / +117.00 · BL10001063 / 2020-04-30 / +34.00 (N) · BL10001080 / 2020-04-30 / +158.00 · BL10001756 / 2025-12-31 / +215.00 (N) · BL10001820 / 2025-12-31 / +228.00 (N) · BL10001897 / 2020-04-30 / +114.00 (N) · BL10002328 / 2020-04-30 / +499.00 · BL10002704 / 2025-12-31 / +15.00 (N) · BL10003429 / 2020-04-30 / +498.00 (N) · BL10003599 / 2025-12-31 / +484.00 (N) · BL10004276 / 2025-12-31 / +189.00 (N) · BL10004585 / 2025-12-31 / +262.00 (N) · BL10004896 / 2025-12-31 / +474.00 · BL10004914 / 2020-04-30 / +29.00 (N)

**t4, admin fee (policy, year, delta):** BL10000099 / 2001 / +147.00 (N) · BL10000139 / 2014 / +136.00 (N) · BL10000151 / 2015 / +123.00 (N) · BL10000182 / 2014 / +45.00 (N) · BL10000595 / 2024 / +30.00 (N) · BL10002682 / 2004 / +48.00 (N) · BL10002708 / 2013 / +132.00 (N) · BL10003181 / 2018 / +121.00 (N) · BL10003208 / 2010 / +115.00 (N) · BL10003421 / 2023 / +7.00 (N) · BL10003489 / 2016 / +23.00 (N) · BL10003550 / 2011 / +21.00 (N) · BL10003698 / 2025 / +136.00 (N) · BL10003860 / 2019 / +45.00 (N) · BL10003910 / 2024 / +21.00 · BL10004031 / 2013 / +96.00 · BL10004781 / 2009 / +66.00 (N) · BL10004816 / 2007 / +56.00 (N) · BL10004844 / 2018 / +46.00 · BL10004909 / 2017 / +53.00

### C. The knobs (`conventions.py`) with the values found

| Knob | Value | Source |
|---|---|---|
| `ERA_SWITCH` | 2007-08-11 | NREVNT event 800 |
| `ROUNDING_COBOL` | truncation (`ROUND_DOWN`) | PRM amounts, units, surrender |
| `ROUNDING_JAVA` | half-up (`ROUND_HALF_UP`) | PRM amounts, units, surrender, commissions |
| `UNIT_DECIMALS` | 6 | NRBOOK |
| `PAID` (premium items that count) | `P` | t0, t4 |
| `COMMISSION_BROKER_DATE` | money date | t0 |
| `ENTRY_RATE_DATE`, `ALLOCATION_DATE` | money date | PRM amounts |
| `ADMIN_FEE_DATE` | deduction date | ADM, t4 |
| `ILLUSTRATION_RATE_DATE` | application date | t2 |
| `PREMIUM_TRADE_DATE` | first day with a fund price after the money date | NRBOOK |
| `PREMIUM_PRICE` / `CHARGE_PRICE` | ask / bid | `t3_booking` |
| `PREMIUM_FX_DATE` / `CHARGE_FX_DATE` | trade date − 1 / trade date (last fixing ≤) | `t3_booking` |
| `FX_CODE_CASE` | uppercase | NRFXRT |
| `PRICE_PUBLICATION` | the latest `FP_CHGTS` | NRFPRC |
| `SCHEDULE_COBOL` / `SCHEDULE_JAVA` | chain with drift / fixed anchor | t1 |
| `COLLECTION_LS` / `COLLECTION_UB` | first TI business day ≥ due date / due date | t1 |
| `HOLIDAY_COUNTRY`, `HOLIDAY_REGION` | `CH`, `TI` | t1 |
| `SURRENDER_PENALTY` | NRSURR(scale, completed years since `PH_BEGDT`); 0 in NRWAIV; minimum 0 | t3 |
| `SMOKER_CODE` | `J` | NRPERS |
| `CENTURY_OFFSET` | 19,000,000 (CYYMMDD + 19,000,000 = YYYYMMDD) | SCHEMA.md |

### D. How to reproduce

This folder (the team's repository) and the challenge data live in different places: two variables, to be adapted
to your own machine, keep the commands independent of the paths.

```bash
export REPO=~/Documents/Neural-Wave/ch-Fable-7.4              # this folder
export DATA=~/Downloads/LifewareChallenge/participants        # the challenge data (legacy/, targets/, starter_kit/), read-only
uv venv --python 3.14 .venv && source .venv/bin/activate      # Python 3.14, as in .python-version
uv pip install -r $REPO/my_solution/requirements.txt radon
python -B $REPO/tools/data_checks.py --data $DATA                 # about 6 s; compare with tools/data_checks_expected.txt
python -B $REPO/tools/data_checks.py --data $DATA --sample 0      # all rows in the row-by-row checks (about 30 s)
python -B $DATA/starter_kit/check.py --submission $REPO/my_solution --legacy $DATA/legacy --targets $DATA/targets
python -B $REPO/tools/ledger_checks.py --data $DATA --submission $REPO/my_solution   # every booking: NRBOOK, t3_booking
python -B $REPO/tools/import_map.py $REPO/my_solution             # the package layers
python -B $REPO/tools/mi_report.py $REPO/my_solution
```

`-B` keeps Python from writing `__pycache__` folders, also into the read-only challenge folder.

### E. Quick glossary

- **COBOL era / Java era:** the period when Neuron ran in COBOL (until 10.8.2007) and that of Neuron NG in Java (from 11.8.2007).
- **As-of:** the value valid at a given date, i.e. the last one published on that day or earlier.
- **Money date / trade date:** the day the money arrives / the day the units are bought or sold.
- **Brick:** a single step of the calculation that can be verified on its own (for example "invested amount of a premium").
- **True state:** the actual units before a movement, reconstructed from the diagnostics.
- **Integer delta:** a difference between target and rule equal to a whole number of currency units; the signature of the manual corrections.
- **Local ceiling:** the maximum accuracy achievable with `check.py`, which also counts the manual corrections; it corresponds to 100% in the official evaluation.
- **LLOC, V, G, C:** the four components of the maintainability index (§5.1).
