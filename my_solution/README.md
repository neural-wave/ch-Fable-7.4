# Neuron migration: rules rebuilt from the export, written to be maintained

`submission.py` computes every task from the files in `legacy_dir` only; it never reads a target
file. Every hidden rule of Neuron is written down once, in the module of its business concept, with
the evidence that fixed it.

## Results on the train targets (official `check.py`)

| Task | Exact rows | Local ceiling | Rows missed | Time |
|---|---|---|---|---|
| t0 commissions | 225,848 / 225,858 = 99.9956 % | 99.9956 % | 10, all changed by hand | 1 s |
| t1 next due dates | 15,028 / 15,028 = 100.0000 % | 100 % | 0 | 1 s |
| t2 projected maturity value | 3,011 / 3,019 = 99.7350 % | 99.7350 % | 8, all changed by hand | 4 s |
| t3 surrender value | 6,137 / 6,153 = 99.7400 % | 99.7400 % | 16, all changed by hand | 26 s |
| t4 annual statement | 34,125 / 34,145 = 99.9414 % | 99.9414 % | 20, all changed by hand | 25 s |

The train targets still hold the 54 values that were changed by hand (task t5), and every row we
miss is one of them: target and rule differ by a whole amount of francs. The official evaluation
does not score those rows, so the five tasks are exact on every scored row. On top of the scored
values, the unit accounting reproduces every PRM, ADM, AMC and RSK booking of `t3_booking` and
every yearly value of `t2_projection_year` (79,040 / 79,040).

Maintainability index (radon, as `scoring.py`): **97.1**.

## How to run

```bash
export DATI=~/Downloads/LifewareChallenge/participants     # the challenge data (adapt)
pip install -r requirements.txt radon                      # Python >= 3.10
python -B $DATI/starter_kit/check.py --submission . --legacy $DATI/legacy --targets $DATI/targets
python -B ../verifica_dati/mi_report.py .                  # the MI, file by file and term by term
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
  - Splits give the rounding difference to the largest position and drop pieces of zero or less.
- *Insurance age.* COBOL: days lived / 365 to the nearest year, so leap days do not count.
  Neuron NG: completed months to the nearest year. Then plus the completed policy years.
- *Valuation.* Units traded up to the valuation date, at the bid price and in the policy currency
  via CHF. The surrender penalty is the NRSURR rate of the product scale by completed years, none
  in the NRWAIV periods; a surrender value is never below zero.

**t4.** The yearly sums of the same bookings: premiums by money date, entry charges (premium share
less invested amount) by trade date, ADM, AMC and RSK by run date. There is one row per calendar
year, from the start to the exit, maturity or closing year, at most up to the last full year
before the extract.

## How the code is organised for maintainability

Two kinds of modules, one business concept each:

- **Flow modules** apply the rules and carry no arithmetic at all: `submission`, `export`
  (tables and contract of a policy), `market` (prices and rates), `account` (bookings and
  positions), `ledger` (all bookings of a policy), `investment`, `orders`, `charges` (the monthly
  run), `statement`, `valuation` and `offer`.
- **Formula modules** each hold one family of formulas, with its evidence:
  - `money` and `sharing` (rounding by era, pro-rata splits);
  - `conversion` and `trades` (values and units);
  - `purchase`, `fees` (AMC), `cover` and `risk` (RSK);
  - `ages` and `age_rules`;
  - `runs` (calendar), `surrender`, `instalments` and `illustration` (t2);
  - t0/t1: `commission`, `schedule`, `collection`, `business_days`, `months`.

Every constant of Neuron lives in `conventions.py`, next to the evidence that fixed it.
