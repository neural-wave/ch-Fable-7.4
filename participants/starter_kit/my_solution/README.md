# Neuron migration: rules as code

`submission.py` computes everything from the export in `legacy_dir` and nothing else. It does not read any
target file and has no values written into it. The rules were found in the data with tools that are handed in
too: `tools/` and `notebooks/`.

| | |
|---|---|
| t0 commission | 225'848 / 225'858 train rows exact (99.9956 %). The 10 other rows are manual corrections, proven below |
| t1 – t5 | not solved yet: the functions return empty results |
| Maintainability index | 95.8 (`scoring.maintainability`, radon, weighted over all `.py` files of this folder) |

```
python check.py --tasks t0_commission      # from starter_kit/, needs only requirements.txt (polars)
```

## Layout

```
my_solution/
├── submission.py      entry point: one function per task
├── legacy.py          reading the export by the types of NRDICT, the version valid on a date
├── money.py           exact money arithmetic: cents x millionths, rounded half up
├── requirements.txt   polars (tested with 1.30, 1.35 and 2.0)
├── tools/neuron/      the tools that found the rules (not used by the submission)
│   ├── load.py, codes.py, policy.py   tables decoded for exploring, code texts, history of one policy
│   ├── targets.py                     train targets and official scoring, for exploring only
│   ├── schema/                        keys and relations found with Desbordante, and their diagram
│   └── solver/                        Z3: proofs (UNSAT) and rate recovery (MaxSMT)
└── notebooks/
    ├── 00_explore.ipynb               EDA: tables, codes, keys and relations, data quality, dates, versions
    └── 01_t0_commission.ipynb         t0: rates recovered from the targets alone, proofs of the outliers
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

**Manual corrections (input for t5).** The 10 rows that the rule misses are UNSAT for every base (`PR_AMTDU`,
`PR_AMTRC`), every NRCOMR rate and every rounding mode. Each differs from the rule by whole francs. Six of
them are listed in NREXCP. Four are not: BL10001299 #103, BL10001328 #1, BL10002438 #11, BL10004554 #35.

## Code quality

Small modules with one job each, docstrings that explain the why, and polars expressions over Python loops.
The maintainability index of this folder is 95.8, measured as the organizers do: radon per file, weighted by
lines of code. The submission modules and most tools score 100. The two Z3 modules score about 77, because
operators are the natural notation of Z3 constraints.

## Running the tools

```
pip install -r tools/requirements.txt
PYTHONPATH="$PWD:$PWD/tools" jupyter lab notebooks/      # from my_solution/
```

The tools look for the data in `$NEURON_DATA`, by default the `participants` folder that contains this
hand-in. They cache decoded tables as parquet in `cache/` next to it. Only the tools read the train targets,
for exploring and checking.
