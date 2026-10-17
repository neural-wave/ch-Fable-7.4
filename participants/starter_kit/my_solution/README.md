# Neuron migration: the rules, found by one discovery loop

`submission.py` calculates every task from the export alone. The rules were not written from a reading of the
data by hand: an LLM (Claude Code) turned each task's story into a first rule with holes, and a generic toolkit
(`tools/detective`) found where the rule was wrong, searched the holes, and checked every step. Every rule in
the code cites the finding it comes from; the findings, the prompts and the answers of the LLM are in the repository.

## Results on the train targets (`python check.py`)

| Task | Right | The rows left |
| --- | --- | --- |
| t0 commission | 225848 / 225858 | 10 hand edits |
| t1 next due dates | 15028 / 15028 | none |
| t2 projected maturity value | 3011 / 3019 | 8 hand edits |
| t3 surrender value | 6137 / 6153 | 16 hand edits |
| t4 annual statement | 34125 / 34145 | 20 hand edits |
| t5 outliers | 54 found | the 54 rows above |

The diagnostic targets agree to the last row: every projected policy year (79040), every premium and charge
booking (5024847) and every holding (31578), all calculated without the answers. Every task module has a
maintainability index of 100 (radon).

## The approach (§6 of the task, one loop for every target)

1. **Understand the data**, with tools that know no table: `load` (types from the data dictionary), `profile`
   (generic checks: impossible dates, case variants, columns empty for some codes), `schema` (keys and foreign
   keys found with Desbordante), `codes`, `timeline` (every row of one policy in date order).
2. **A target becomes a `TaskSpec`** (`spec`): its keys, its values and the export table it describes, found
   from the file alone.
3. **The story becomes a sketch** (LLM): a first rule whose open choices are parameters ("holes"): which date a
   lookup uses, how an amount is rounded, which system made a row.
4. **One round** (`discover`): the rule's values against the target (`residuals`), what the export knows about
   every row as of each of its dates (`features`), a decision tree on the wrong rows and change points along
   every date (`conditions`), written as a report with finding ids (`report`, `reports/`).
5. **Search** (`formulas.fill_holes`, program synthesis by sketching): every combination of holes, scored on 80 %
   of the policies and checked on the other 20 %.
6. **Diagnostics** for the deep tasks (`diagnostics`, `bookings`, `replay`): NRBOOK's dates and the customer
   orders as targets of their own; the holdings Neuron had before every charge run (teacher forcing), so each
   run can be checked alone; the presence of a booking as a target, so a booking Neuron never made counts.
7. **Find the formula** (`regression`): robust regression and Z3 recover rates from inputs and outputs (they
   found the management charge rates and the penalty table back, exactly).
8. **Find the structure and the noise** (`structure`: permutation importance and clusters of policies; `noise`:
   an isolation forest on the differences that are left, separating hand edits from rules not found yet).
9. **Show it** (`visuals`, `tools/visuals/index.html`).

The LLM's prompts, inputs and outputs, step by step: `tools/detective/llm/001` to `014`. The reports cited
below are in `tools/detective/reports/<target>/`.

## The rules found

**t0 commission** (`commission.py`): the received amount times the rate of the broker tier and premium type,
half up; the broker and the rate of the policy version valid on the money date (`t0_commission/r1/T1`,
`r1-search/S2`).

**t1 next due dates** (`schedule.py`): whole periods from the first past due date on or after the system
conversion (`t1_next_due_dates/r2-due-search/S1`); direct debits are collected on the next business day of
canton Ticino, bank transfers on the due date (`r2-collection-search/S1`).

**t2 projection** (`projection.py`): one pot; the system that made the offer (old before the conversion of
2007-08-11, Neuron NG from that day) decides the rounding (cut off / half up) and the entry age (days / 365 /
nearest birthday) (`t2_projection_year/r3-search-era/S1`, `r5-search-era-age/S1`, `r6-search-boundary/S1`);
28-digit decimal growth; the sum at risk of option A kept exact (`r4-search-risk/S1`).

**t3 surrender value**, from the whole fund accounting:

- premiums (`premiums.py`): the entry charge of the broker tier or an agreement, cut off; each fund's amount one
  rounding of premium × (1 − rate) × share (`t3_booking_prm/r7-search-split/S1`); traded on the fund's first
  price day after the money date (`r3-search-trade/S1`) at the ask price; the exchange rate of the eve of the
  trade date, exact (`r5-search-fx/S1`); the pot by the money date (`r6-search-pot/S1`); the system by the trade
  date (`r8-search-era/S1`)
- charges (`charges.py`): the admin fee shared by value, the remainder to the largest
  (`t3_booking_adm/r2-search-remainder/S1`); the management charge a twelfth a year (days since the last monthly
  anniversary / 360 in the old system, `t3_booking_amc/r1-search-accrual/S1`, `r5-search-accrual/S1`); the risk
  charge on the value after both (`t3_booking_rsk/r1-search-value/S1`) at the age convention of the system that
  made the offer (`r2-search-age/S1`); a charge never more than the value left
  (`t3_booking_charges/r1-search-limit/S1`); only positive amounts booked (`charge_bookings/r1-search-booked/S1`)
- runs (`runs.py`, `accounting.py`): every monthly anniversary after the first premium's trade date, none on the
  day of a surrender or death claim (`charge_runs/r1-search/S1`); each run sees the bookings traded before its day
  (`t3_booking_adm_amc/r3-search-order/S1`); reversed events and technical corrections ignored
- surrender value (`surrender.py`): the units at the bid price of the valuation date in the policy currency, per
  fund and pot rounded by the system; the surrender value the policy value × (1 − penalty of the scale and the
  completed years), rounded by the system, never below 0, no penalty in a waiver period
  (`t3_surrender_value/r3-search-net/S1`)

**t4 annual statement** (`statement.py`): the premiums by money date; each premium booking carries its share of
the entry charge into the year of its trade date (`t4_annual_statement/r2-search-entry/S1`); the charges of the
runs by run date.

**t5 outliers** (`outliers.py`): a target value that differs from the rules by whole francs. Every difference
the rules leave is one, NREXCP lists part of them, and a rule not found yet left cents instead
(`t3_surrender_value/r1-noise`, `013-t5-story.md`).

## Running it

    python check.py                                 # the starter kit's scoring, from participants/starter_kit
    uv run python -m detective.visuals              # the pictures, from my_solution/tools

The submission needs `polars` and `holidays` (`requirements.txt`). The tools need the project environment
(`pyproject.toml` at the repository root: scikit-learn, Desbordante, Z3, matplotlib).
