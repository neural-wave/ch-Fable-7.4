# Neuron migration: rules rebuilt from the export, written to be maintained

`submission.py` computes every task from the files in `legacy_dir` only; it never reads a target
file. Every hidden rule of Neuron is written down once, in the module of its business concept, with
the evidence that fixed it. [ARCHITECTURE.md](ARCHITECTURE.md) is the map of the code: packages,
layers, the path of each task and where each rule lives.

## Results on the train targets (official `check.py`, Python 3.14)

| Task | Exact rows | Local ceiling | Rows missed | Time |
|---|---|---|---|---|
| t0 commissions | 225,848 / 225,858 = 99.9956 % | 99.9956 % | 10, all changed by hand | 2 s |
| t1 next due dates | 15,028 / 15,028 = 100.0000 % | 100 % | 0 | 1 s |
| t2 projected maturity value | 3,011 / 3,019 = 99.7350 % | 99.7350 % | 8, all changed by hand | 4 s |
| t3 surrender value | 6,137 / 6,153 = 99.7400 % | 99.7400 % | 16, all changed by hand | 24 s |
| t4 annual statement | 34,125 / 34,145 = 99.9414 % | 99.9414 % | 20, all changed by hand | 0.1 s after t3 |

The train targets still hold the 54 values that were changed by hand (task t5), and every row we
miss is one of them: target and rule differ by a whole amount of francs. The official evaluation
does not score those rows, so the five tasks are exact on every scored row. On top of the scored
values:

- the unit accounting reproduces every PRM, ADM, AMC and RSK booking of `t3_booking`, amount and
  units (5,024,847 bookings), and every yearly value of `t2_projection_year` (79,040 / 79,040);
- for all 4,011 policies of the export, public ones included, the bookings have exactly the
  skeleton that NRBOOK keeps (type, fund, pot, trade and price date): this is how the tie rule of
  the charge split was found on a public policy.

Maintainability index (radon, as `scoring.py`): **97.3**.

**Speed.** t4 once ran out of the evaluator's time limit, so the runs are timed like the rest. t3
and t4 read the same ledger, about 530,000 monthly runs and 6.8 million bookings: one pass now
gives both (`reports/books.py`), and t4 after t3 in the same process costs nothing. The months are
counted with plain arithmetic instead of dateutil, and the prices of a day are looked up once. In
one process, as `check.py` runs them, the five tasks take 30 s instead of 68 s; on its own, in a
fresh process, t3 or t4 takes 27 s instead of 35 s. `tools/evaluator_check.py` times every task
in a fresh process and proves, value by value on all 4,011 policies, that a change of speed
changed no result.

## How to run

From the repository root, with Python 3.14 (`.python-version`):

```bash
export DATA=~/Downloads/LifewareChallenge/participants      # the challenge data (adapt)
python3.14 -m venv .venv && . .venv/bin/activate
pip install -r my_solution/requirements.txt radon
python -B $DATA/starter_kit/check.py --submission my_solution --legacy $DATA/legacy --targets $DATA/targets
python -B tools/ledger_checks.py --data $DATA               # bookings against NRBOOK and t3_booking
python -B tools/evaluator_check.py --data $DATA --save /tmp/before     # times per task, results kept
python -B tools/evaluator_check.py --data $DATA --compare /tmp/before  # after a change: same values?
python -B tools/mi_report.py my_solution                    # the MI, file by file and term by term
```

## The rules we found

**Eras.** Event 800 (user CONV2007) moved every policy from COBOL Neuron to Neuron NG on
2007-08-11. COBOL truncates every rounding, Neuron NG rounds half up; the day of the business event
decides. Several rules exist in both versions, and a policy keeps the one of the system that
issued it.

**Data traps.** Dates are CYYMMDD, numbers have implied decimals (NRDICT). Ten birth dates do not
exist (30 Feb): the age rules read them as written. `PS_SMOKE` is J/N, not Y/N. 80 exchange rates
carry the currency in lower case and count. 664 prices were restated: the latest publication
(`FP_CHGTS`) is the price. Reversed events (900) and technical corrections (990) never happened.

**t0.** The broker holding the policy on the money date `PR_RCVDT` earns the NRCOMR rate of the
broker's tier for the premium type of the tariff (`RK_TARKEY[5]`), on the received amount.

**t1.** Policies in force (state 10) with regular premiums, on the extract date. COBOL moved each
due date from the previous one (the day drifts at month ends), Neuron NG counts whole periods from
an anchor; due dates in (extract, extract + 12 months], before maturity. Direct debits (LS) are
collected on the next Ticino business day (Good Friday is a working day), transfers (UB) on the
due date.

**t2.** The projection of the offer: the first version, with the tariff, the illustration rate
(NRILLU) and the entry charge of the broker's tier valid on the application date, which also
decides the rounding. Month by month from nothing: premium after entry charge, less ADM, less AMC
at the pot-2 rate / 12, less the risk charge, then growth by rate / 12; everything to the cent.

**t3.** A unit account per policy, in this order:

- *Premiums (PRM).* Allocation, entry charge (NRAGRE ENT, else the NRENTC rate of the broker's
  tier) and pot are those of the money date: pot 1 in the first PD_INIMON months, pot 2 after.
  Each fund buys on its first price day after the money date, at the ask price, at the exchange
  rate of the day before the trade.
- *Customer orders.* Switches, withdrawals, surrender and death are booked in NRBOOK with their
  units.
- *Monthly charge runs.* On every monthly anniversary after the first investment, until maturity,
  surrender or death, or the extract date, on the units traded before the run day:
  - ADM: the monthly fee of the tariff, split by value, never above the value;
  - AMC: the pot rate (or NRAGRE AMC), ACT/360 under COBOL and 1/12 under Neuron NG;
  - RSK: sum at risk (A 1 % of the value, B the sum insured above it, C the sum insured) times qx,
    times 1 + loading, times the smoker factor for smokers, / 12. It is computed on the value
    left after ADM and AMC, capped at it, and split by what is left in each position.
  - Splits give the rounding difference to the largest position, on equal values to the first by
    fund and pot, and drop pieces of zero or less.
- *Insurance age.* COBOL: days lived / 365 to the nearest year, so leap days do not count.
  Neuron NG: completed months to the nearest year. Then plus the completed policy years.
- *Valuation.* Units traded up to the valuation date, at the bid price and in the policy currency
  via CHF. The surrender penalty is the NRSURR rate of the product scale by completed years, none
  in the NRWAIV periods; a surrender value is never below zero.

**t4.** The yearly sums of the same bookings: premiums by money date, entry charges (premium share
less invested amount) by trade date, ADM, AMC and RSK by run date. There is one row per calendar
year, from the start to the exit, maturity or closing year, at most up to the last full year
before the extract.

## How the code is organised

Seven packages, one business area each, and three modules at the top
([ARCHITECTURE.md](ARCHITECTURE.md) has the full map):

| Package | Business area | Tasks |
|---|---|---|
| `core/` | money by era, months, validity lookups, totals | all |
| `legacy/` | reading the export: tables, formats, policy versions, premium items, market | all |
| `insurance/` | insurance age, sum at risk, mortality, risk charge | t2, t3, t4 |
| `accounting/` | the unit account: premiums, orders, monthly charge runs, ledger | t3, t4 |
| `reports/` | surrender value and annual statement, read from the ledger in one pass | t3, t4 |
| `billing/` | commissions, due dates and their anchor, Ticino holidays, collection days | t0, t1 |
| `maturity/` | the projection of the offer | t2 |

`submission.py` is the entry point, `conventions.py` holds every constant of Neuron next to its
evidence, and `export.py` groups the export by policy. A package imports only the packages below
it (`tools/import_map.py` checks it).

Inside the packages there are two kinds of modules. **Flow modules** apply the rules and carry no
arithmetic at all, **formula modules** each hold one small family of formulas with its evidence.
That keeps every file short, simple and documented, which is what the maintainability index
measures.
