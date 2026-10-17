# Neuron migration: rules as code

`submission.py` computes everything from the export in `legacy_dir` and nothing else. It does not read any
target file and has no values written into it. The rules were found in the data with the tools in `tools/`, handed
in too.

| | |
|---|---|
| t0 commission | 225'848 / 225'858 train rows exact (99.9956 %). The 10 other rows are manual corrections, proven below |
| t1 next due dates | 15'028 / 15'028 train rows exact (100 %); backtest on 18 past years: no wrong due date |
| t2 projected maturity value | 3'011 / 3'019 train rows exact (99.735 %), and all 79'040 yearly values of the diagnostic. The 8 other rows are manual corrections |
| t3 surrender value | 6'137 / 6'153 train rows exact (99.74 %), and every link of the diagnostics: all 5'024'847 calculated bookings (amount and units), all 23'052 holdings, all 6'153 policy values. The 16 other rows are manual corrections |
| t4 – t5 | not solved yet: the functions return empty results |
| Maintainability index | 100 for the task files; 99.2 for the whole folder with the tools (radon, weighted by lines) |

```
python check.py --tasks t0_commission t1_next_due_dates t2_projected_maturity_value t3_surrender_value   # from starter_kit/
```

## Layout

```
my_solution/
├── submission.py      entry point: thin task functions that compose the modules below
├── conventions.py     the conventions of Neuron as data (states, frequencies, conversion, tariff key, ...)
├── legacy.py          reading the export by the types of NRDICT, the version valid on a date
├── dates.py           calendar: schedules of whole months, business days of canton Ticino, policy years
├── money.py           exact money arithmetic: cents x millionths, units x prices, splits over positions
├── market.py          unit prices and exchange rates as known on a date
├── tariff.py          the policy as signed and its parameters valid on the application date
├── charges.py         the charges: entry charge, risk charge, death benefit, ages and mortality
├── projection.py      t2: the offer month by month, its steps in Neuron's order
├── bookings.py        t3: the counted bookings, the premiums bought in units, the units moved by events
├── charge_run.py      t3: the monthly charge runs (admin fee, management and risk charge) one after another
├── valuation.py       t3: holdings, policy value and surrender value on a date
├── requirements.txt   polars >= 1.31 (128-bit integers), holidays; tested with polars 1.31 and 2.0
└── tools/neuron/      the tools that found the rules (not used by the submission)
    ├── load.py, codes.py, policy.py   tables decoded for exploring, code texts, history of one policy
    ├── targets.py                     train targets and official scoring, for exploring only
    ├── schema/                        keys and relations found with Desbordante, and their diagram
    ├── solver/                        Z3: proofs (UNSAT), interval reasoning, rate recovery (MaxSMT)
    ├── backtest.py                    t1 on past extract dates against the real due dates PR_DUEDT
    ├── bisection.py                   the first step where a calculation leaves a diagnostic target (t2)
    └── account_check.py               the unit account link by link against the diagnostics (t3)
```

## Approach

1. **Formats from the data dictionary.** Every column is converted by its NRDICT type. Amounts stay integers in
   cents and rates integers in millionths, so the arithmetic is exact. `CYYMMDD` dates stay integers too, since
   they sort like dates (`970630` < `1070326` < `9999999`, the open end).
2. **Relations found by a tool, not by hand.** Desbordante finds the candidate keys (HyUCC) and the inclusion
   dependencies between all tables (Faida exact, also over two columns; Spider approximate). Every IND is
   checked exactly; it counts as a relation when it can be a foreign key (`schema/relations.py`).
3. **Rules checked against the targets.** A candidate rule is scored with the official scoring. Every row it
   misses is examined.
4. **Proofs with Z3.** MaxSMT recovers a parameter from the targets alone. An UNSAT answer proves that no rule of
   a whole space (bases x rates x rounding modes) gives a target value, so the value was corrected by hand.
5. **Search over conventions, then bisection.** For t2 a grid of conventions (monthly rate, order of the steps,
   rounding, age, management charge: 768 combinations) was scored on the first policy year; the diagnostic of the
   yearly values then shows the first year in which a policy leaves the target (`bisection.py`), and the
   policies that share it point at the missing condition.
6. **One link at a time.** t3 is a chain: calculated bookings, holdings, policy value, surrender value. Each link
   was matched with its diagnostic (`t3_booking`, `t3_holding`, `policy_value`) before the next one was built
   (`account_check.py`), so every miss pointed at one rule.

## Rules found

**t0 commission.** One commission per premium item whose money was received:

- received: money date `PR_RCVDT` > 0, and the receipt event `PR_EVTNR` not reversed by an event 900
  (`EV_REVNR`);
- rate from NRCOMR, by the broker tier and the premium type, valid on the money date `PR_RCVDT`;
- broker tier: `NRBROK.BR_TIER` of the broker `PH_BRKNR` of the policy version valid on `PR_RCVDT`. If several
  versions are valid, the highest `PH_VRSNR` wins, so a broker change counts from its validity date even when it
  was entered later;
- premium type: `E` for single premium policies (`PH_FREQ` = E), `L` for regular premiums;
- commission = `PR_AMTRC` x rate, rounded half up to the cent.

Z3 recovers the six rates from the targets alone, and they equal NRCOMR: A/L 4 %, A/E 1.5 %, B/L 3 %, B/E 1 %,
C/L 2 %, C/E 0.5 %. Each interval of feasible rates closes on a single value.

**t1 next due dates.** For every policy that pays regular premiums on the extract date, the due dates of the
following year with their collection dates:

- policies: state 10 and frequency other than `E` in the policy version **valid on the extract date** (not the
  version marked current: BL10001854 has a current version that ended in 2021);
- schedule: COBOL computed every due date from the previous one, so a day 29 to 31 sank in a short month and
  stayed there (31 -> 28 -> 28). Since the conversion to Neuron NG on 11.8.2007 the schedule is its first due date
  plus whole periods of the frequency (M 1, Q 3, H 6, J 12 months), so a day 31 comes back after a short month.
  The anchor is the first past due date `PR_DUEDT` on or after the conversion. No due date on or after maturity;
- collection: direct debit (`LS`) on the due date if it is a business day, else on the next one; bank transfer
  (`UB`) on the due date. Business days are the weekdays without a public holiday of canton Ticino (library
  `holidays`, `CH`/`TI`): Good Friday is a business day there, 26.3.2027 is collected on the day.

The target window has dues on all 365 days; the moved weekdays are exactly the Ticino holidays. The export keeps
no past collection dates (`PR_RCVDT` is when the money arrived), but it keeps the past due dates: computing t1
for 30 June of every year from 2008 to 2025 reproduces the real due dates of 28'366 of 28'386 unchanged policies.
In the other 20 the real list is the start of the predicted one: the policy stopped paying without a new version.

**t2 projected maturity value.** The offer simulates the policy month by month from the start date to the
maturity date, as one amount (no fund prices, currencies or individual agreements):

- the policy as signed: its first version (`PH_VRSNR` 1), later changes do not count; the insured person of the
  main risk;
- the parameters valid on the application date `PH_APPDT`: charges NRCHRG by tariff family and generation (from
  the tariff key `RK_TARKEY`), entry charge NRENTC by broker tier, growth rate NRILLU;
- every month, in this order: the premium due (every 1, 3, 6 or 12 months from the start; a single premium once)
  less the entry charge; the admin fee `CG_ADMFEE`; the management charge at the pot 2 rate `CG_AMCP2` / 12 (one
  amount has no initial units); the risk charge; the growth at `IL_RATE` / 12 (not the compound monthly rate);
- risk charge = sum at risk x qx x smoker factor (`CG_SMKFAC` if `PS_SMOKE` = J) x (1 + `RK_LOAD`) / 12. The sum
  at risk is the death benefit less the value: option A 101 % of the value, B the higher of sum insured and value,
  C value plus sum insured. qx comes from the table `CG_MORTTB`, for the sex of the tariff key (U: the sex of the
  person) and the entry age plus the policy year;
- COBOL made the offers signed before the conversion (11.8.2007), Neuron NG the later ones. Neuron NG rounds the
  charges and the growth half up to the cent, and its entry age is the completed months since birth / 12, rounded
  half up. COBOL truncates them, and its entry age is the days since birth / 365, rounded half up: with the leap
  days its age goes up a little earlier. With the Java rules the first policy year matched 0 to 11 % of the offers
  per month of application up to July 2007, 80 % in August 2007 and nearly all after it;
- the growth multiplies by 1 + rate / 12 in decimal arithmetic of 28 significant digits. For 4 % the factor
  1.00333...3 is a bit less than 1 + 1/300, so a value that would end on exactly half a cent (or a whole cent, for
  COBOL) may end just below it; the 28 digits round it back only when the error is small enough. The exact
  fraction misses a cent in 22 % of the policies, an 18-digit rate in 7 %, the 28 digits in none;
- birth dates that do not exist (31 November, 8 policies) run on into the next month, like a lenient calendar.
  Taking the last day of the month gives the same values for all 8, so the train data cannot tell them apart.

**t3 surrender value.** NRBOOK has a row for every booking with its fund, pot and dates. Switches, withdrawals,
surrenders and death claims carry their units; the premiums (`PRM`) and the charges (`ADM`, `AMC`, `RSK`) are
blank, since the nightly job that calculated them is not in the extract. The submission recalculates them:

- counted: the bookings of events not reversed by an event 900 and not entered as a manual correction (event
  990, online, at the timestamps of NREXCP);
- prices: the bid or ask price of the last price date of the fund on or before the trade date (that is always
  `BK_PRCDT`), and of that day the last publication `FP_CHGTS`. Exchange rates `NRFXRT` in francs per unit, the
  lower case currencies included; units = amount x rate of the policy currency / rate of the fund currency /
  price, rounded to the millionth;
- premium (event 110): one booking per fund of the allocation. Amount = `PR_AMTRC` x (1 - entry charge rate) x
  `AL_PCTG`, rounded once; the entry charge is an individual agreement (`NRAGRE` ENT) or the rate of the broker
  tier of the policy version, the allocation and both rates valid on the money date `BK_RCVDT`. Units at the ask
  price, with the exchange rates of the day **before** the trade date;
- charge run (event 300, at 01:30): it values every position with the units traded **before** its trade date, at
  the bid price and the exchange rates of the day, rounded to the cent position by position. Then:
  - ADM: `CG_ADMFEE` valid on the trade date (not the application date), at most the value; split over the
    positions by value, the cents of the rounding to the largest position (the first fund and pot on a tie).
    Positions too small for a cent of fee count in the split too;
  - AMC per position: the rate of its pot (`CG_AMCP1` initial, `CG_AMCP2` base) or of an agreement (`NRAGRE`
    AMC), on its value. Neuron NG takes a twelfth; COBOL took the days of the month (from the previous monthly
    date of the start date) / 360;
  - RSK: the risk charge of t2 on the value left after ADM and AMC, at most that value, split by that value.
    The age is the entry age as the system that issued the policy counted it (COBOL days / 365 before the
    conversion, months / 12 after) plus the policy years completed on the trade date. A start on 29 February
    has its anniversary on 28 February;
- Neuron NG rounds half up, COBOL truncated, by the trade date of the booking. The runs of a policy depend on each
  other through the units, so they run one after another: the first run of every policy at once, then the
  second, and so on (6 seconds for 533'660 runs);
- policy value on a valuation date: the units traded on or before it, at the bid price of the last price date
  and the exchange rates of the day, rounded position by position;
- surrender value = policy value x (1 - penalty), rounded once, never below 0. The penalty `NRSURR` comes from
  the scale of the product for the policy years completed on the valuation date; there is none after the last
  year of the scale and in the waiver periods `NRWAIV`. BL10001005 shows the floor: its value no longer covered
  the run of October 2021, the admin fee took all of it and the management charge 2 cents more, so its policy
  value at the end of 2025 is -0.03 and its surrender value 0.

**Manual corrections (input for t5).** The 10 rows of t0 that the rule misses are UNSAT for every base
(`PR_AMTDU`, `PR_AMTRC`), every NRCOMR rate and every rounding mode. Each differs from the rule by whole francs.
Six of them are listed in NREXCP. Four are not: BL10001299 #103, BL10001328 #1, BL10002438 #11, BL10004554 #35.

The 8 maturity values of t2 that the rule misses have a projection that is right in every year; only the final
value differs, by whole francs with the cents of the projection (`bisection.corrected_maturities`). Five are
listed in NREXCP (BL10000128, BL10001762, BL10003323, BL10003583, BL10003808). Three are not: BL10002196
(+1'726.00), BL10002973 (+1'498.00), BL10004278 (+3'294.00).

The 16 surrender values of t3 that the rule misses have the right policy value and holdings; only the surrender
value is higher, by whole francs (`account_check.surrender_mismatches`). Eleven are listed in NREXCP. Five are
not: BL10000321 2025 (+175.00), BL10000768 2020 (+117.00), BL10001080 2020 (+158.00), BL10002328 2020 (+499.00),
BL10004896 2025 (+474.00).

## Code quality

As the strategy suggests: thin task functions, small modules with one job each, the conventions as data instead
of branches, and docstrings that state the rule in business terms. The task files score 100 in the
maintainability index (radon, weighted by lines of code); with the tools the folder scores 99.2. The three Z3
modules score 85 to 90, because operators are the natural notation of Z3 constraints.

## Running the tools

```
pip install -r requirements.txt -r tools/requirements.txt
PYTHONPATH="$PWD:$PWD/tools" python -c "from neuron.backtest import backtests; print(backtests())"
PYTHONPATH="$PWD:$PWD/tools" python -c "from neuron.bisection import corrected_maturities; print(corrected_maturities())"
PYTHONPATH="$PWD:$PWD/tools" python -c "from neuron.account_check import surrender_mismatches; print(surrender_mismatches())"
```

The tools look for the data in `$NEURON_DATA`, by default the `participants` folder that contains this
hand-in. They cache decoded tables as parquet in `cache/` next to it. Only the tools read the train targets,
for exploring and checking.
