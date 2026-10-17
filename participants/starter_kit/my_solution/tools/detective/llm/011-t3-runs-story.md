# 011 · t3 · the run dates, the simulation and the surrender value

**Step:** story → sketch → findings → holes → search, for the three parts that make t3 from the rules alone.
**LLM:** Claude Code. Every hole was decided by `formulas.fill_holes` on 80 % of the policies, checked on the
other 20 %.

## Input

The task text of t3 (`007-t3-story.md`): charges on every monthly anniversary; the glossary: "Monthly anniversary:
the same day in every month as the start date"; the surrender value: the units at the redemption price, the last
price on or before the valuation date, in the policy currency, less the penalty; surrendered policies and policies
of insured persons who died are worth 0. Tables: NRSURR (penalty rate per scale and completed policy years),
NRWAIV (waiver periods), NRPROD (PD_SRPSCL, the surrender scale of a product), NREVNT (410 full surrender, 500
death claim, 300 the runs).

What `010-t3-charges-findings.md` left: the charges are right on the units Neuron held (teacher forcing). A new
system must know when the runs happen and which units they see, without NRBOOK's skeleton.

## Prompt 1: the run dates

Make the run dates from the policy: every monthly anniversary until the policy ends. The events 300 are only the
diagnostic: every anniversary up to the last run of the export and every run event is a candidate, run is 1 when
NREVNT has it (`diagnostics.marked`, `reports/charge_runs`).

Output: `runs.py` (`charge_dates`). Holes: the first run (after the start, on or after the first trade date of a
premium, after it), the run on the day of a surrender or death claim, the run on the maturity date.

- `charge_runs/r1-search`: **S1** the first anniversary after the trade date of the first premium, no run on the
  day of a surrender or death claim: 548855 / 548977, held out 126269 / 126269 (after the start: 548463)
- `charge_runs/r2`: 122 wrong, **r2/T1** paid-up policies (premium changed to 0): runs after the value ran out.
  That needs the units, so it waits for the simulation.

## Prompt 2: the simulation

Make the whole fund accounting from the rules: the premium bookings, the customer orders (complete in NRBOOK), and
the runs, each on the units that the bookings before its day and the earlier runs left. A run depends on the
earlier runs, so the runs go in turn; all that does not depend on the units is made once.

Output: `charges.py` split into `run_rows` (system, policy, tariff, prices, rates, death probability) and
`charges_of` (the arithmetic on the units; the teacher-forced check is unchanged: `t3_booking_charges/r2`,
4617211 / 4617211); `accounting.py` (`accounting`, `charged`: the k-th run of every policy at once).

- `t3_booking_simulated/r1`: 5024847 / 5024847 premium and charge bookings right, without teacher forcing
- every booking of NRBOOK (all policies) has its twin and no twin is left over: PRM 553549, ADM 2460334, AMC
  2471099, RSK 1272934
- `charge_runs/r3`: a run happens when it takes a charge: 675246 / 675246
- `t3_holding/r1-search`: **S1** the bookings traded on the valuation date count: 25660 / 25660, held out 5918 /
  5918 (not counting them: 23961)

## Prompt 3: the surrender value

Write the surrender value the story describes. Holes: the rounding by system, per fund or once, the cross rate,
the penalty rounding, the day a claim makes a policy worth 0.

Output: `surrender.py`.

- `t3_surrender_value/r1`: the policy value right in every row; **r1/C1** a change point at the valuation dates:
  31.4 % wrong on 2006-12-31 (old system), 0.5 % after. `r1-search`: **S1** rounding by system, per fund and
  pot, exact cross rate: 4800 / 5009
- `r2-search-penalty`: **S1** the old system rounded the penalty up: 4990 / 5009. 7 missing rows are policies
  without units on the date: worth 0
- `r3.md`: 5 surrender values of Neuron NG one cent too low, all with a penalty of an exact half cent (132330 x
  5 % = 6616.5, Neuron 6616); 125713.5, the surrender value itself, rounded half up is right. And the old system's
  "penalty up" is the same as its rest cut off. BL10001005 has a value of −3 cents (the charges used it up) and a
  surrender value of 0. `r3-search-net`: **S1** the surrender value is the value at (1 − penalty rate), rounded by
  the system, never below 0: 4996 / 5009, held out 1141 / 1144
- `r4.md`: the 16 rows left differ by whole francs; 11 are listed in NREXCP (**r4/T1** EX_TARGET =
  t3_surrender_value.surrender_value): hand edits, for t5

`check.py`: t3_surrender_value 6137 / 6153, the 16 hand edits.
