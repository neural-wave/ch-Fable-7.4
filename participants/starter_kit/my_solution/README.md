# Neuron migration: rules as code

`submission.py` computes everything from the export in `legacy_dir` and nothing else. It does not read any
target file and has no values written into it. The rules were found in the data with the tools in `tools/`, handed
in too.

| | |
|---|---|
| t0 commission | 225'848 / 225'858 train rows exact (99.9956 %). The 10 other rows are manual corrections, proven below |
| t1 next due dates | 15'028 / 15'028 train rows exact (100 %); backtest on 18 past years: no wrong due date |
| t2 – t5 | not solved yet: the functions return empty results |
| Maintainability index | 100 for the task files; 95.9 for the whole folder with the tools (radon, weighted by lines) |

```
python check.py --tasks t0_commission t1_next_due_dates      # from starter_kit/, needs requirements.txt
```

## Layout

```
my_solution/
├── submission.py      entry point: thin task functions that compose the modules below
├── conventions.py     the conventions of Neuron as data (states, frequencies, conversion date, calendar, ...)
├── legacy.py          reading the export by the types of NRDICT, the version valid on a date
├── dates.py           calendar: schedules of whole months, business days of canton Ticino
├── money.py           exact money arithmetic: cents x millionths, rounded half up
├── requirements.txt   polars, holidays (tested with polars 1.30 and 2.0, holidays 0.60 and 0.106)
└── tools/neuron/      the tools that found the rules (not used by the submission)
    ├── load.py, codes.py, policy.py   tables decoded for exploring, code texts, history of one policy
    ├── targets.py                     train targets and official scoring, for exploring only
    ├── schema/                        keys and relations found with Desbordante, and their diagram
    ├── solver/                        Z3: proofs (UNSAT) and rate recovery (MaxSMT), used for t0
    └── backtest.py                    t1 on past extract dates against the real due dates PR_DUEDT
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

**Manual corrections (input for t5).** The 10 rows that the rule misses are UNSAT for every base (`PR_AMTDU`,
`PR_AMTRC`), every NRCOMR rate and every rounding mode. Each differs from the rule by whole francs. Six of
them are listed in NREXCP. Four are not: BL10001299 #103, BL10001328 #1, BL10002438 #11, BL10004554 #35.

## Code quality

As the strategy suggests: thin task functions, small modules with one job each, the conventions as data instead
of branches, and docstrings that state the rule in business terms. The task files score 100 in the
maintainability index (radon, weighted by lines of code); with the tools the folder scores 95.9. The two Z3
modules score about 77, because operators are the natural notation of Z3 constraints.

## Running the tools

```
pip install -r requirements.txt -r tools/requirements.txt
PYTHONPATH="$PWD:$PWD/tools" python -c "from neuron.backtest import backtests; print(backtests())"
```

The tools look for the data in `$NEURON_DATA`, by default the `participants` folder that contains this
hand-in. They cache decoded tables as parquet in `cache/` next to it. Only the tools read the train targets,
for exploring and checking.
