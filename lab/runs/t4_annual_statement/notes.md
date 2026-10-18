# t4_annual_statement

## 2026-10-17

**Winner:** written function (step 4b), `code:` fingerprint in `ledger.jsonl`, scored with `lab score`:
**34122 / 34145 total, holdout 6735 / 6737.** `check.py --tasks t4_annual_statement` with the system Python
gives the same, 34122 / 34145, 30 s. No feature was added; no `~llm` run.

The pipeline report (relations on PH_PREMI, previous(admin_fees)) found no complete rule: entry, management and
risk charges have no dense clusters. The statement is the yearly sum of the t3 fund accounting, so the function
reuses `FundAccounting` through a subclass, `AnnualStatement`, that adds up each charge as it is booked.
`FundAccounting` (t3) and `neuron.py` are unchanged.

| Step | Change | Exact rows (holdout) |
|---|---|---|
| start | `return {}` | 0 / 34145 (0 / 6737) |
| 1 | AnnualStatement + rows rule (below) | 34121 / 34145 (6735 / 6737) |
| 2 | risk charge at most the value left after admin + management | 34122 / 34145 (6735 / 6737) |

Rules:
- **Rows:** every policy, one row per calendar year from year(PH_BEGDT) to min(2025, year of PH_VLDFR of the
  first version in state 60/70). Exact on all 3019 target policies (no row too many or missing).
- **premiums:** sum of PR_AMTRC of the NRPREM items with PR_STATE P, by year of **PR_RCVDT**.
- **entry_charges:** per premium and fund share: PR_AMTRC x AL_PCTG - the net amount invested
  (cents(PR_AMTRC x (1 - entry rate) x AL_PCTG), era rounding), so the rounding of the net amount goes into the
  charge. By year of the **trade date** (first price date after PR_RCVDT), not the receipt date: a premium
  received at the end of December has its entry charge in January (144 / 2343 rows of a sample differ).
  By the receipt year 2199 / 2343, cents(premium x rate) 1954 / 2343.
- **admin_fees:** CG_ADMFEE per charge run that has holdings, by year of the run (EV_EFFDT).
- **management_fees, risk_charges:** the AMC and RSK amounts of the t3 charge run, by year of the run.
  The risk charge is at most the value left after the admin fee and the management charge, never below 0
  (BL10004387 2020-12-01: risk 6.35 on 1.99 left, the statement has 1.99).
- **total_charges** = entry + admin + management + risk (exact identity in the report).

Verification: `uv run pytest -q`: 95 passed, 2 skipped, 1 failed: `test_t5_reports_the_manual_corrections` (expects
10 outliers, all t0; already failing since t2, see the t2 and t3 notes; not changed). NRBOOK is not read.

t5: t4 is in `CHECKED` (keys str, int; six Decimal values). `check.py --tasks t5_outlier_detection`: 57 outliers
(t0 10, t2 8, t3 16, t4 23), 54 s.

Maintainability index (radon mi): submission.py 33.1 -> 29.9, neuron.py 49.8 (unchanged).

## Residuals (23 rows)

- **20 manual corrections of admin_fees:** whole-franc increases (+7 to +147), 16 of the policies listed in
  NREXCP, e.g. BL10000099 2001 +147.00, BL10000139 2014 +136.00. Not listed: BL10003910 2024 +21,
  BL10004031 2013 +96, BL10004844 2018 +46, BL10004909 2017 +53. They go to t5.
- **BL10001005 2021, admin_fees -0.96** (85.00 computed, 84.04 target): the last run (2021-10-01) has a value of
  7.54 and Neuron charges an admin fee of 7.54 instead of 8.50 (management 0.02 is still charged). The admin fee
  is capped at the value of the holdings. The fix belongs in `FundAccounting.charge_run` (the split of
  CG_ADMFEE), which is shared with t3. It was left alone because this session could change only t4. It would
  probably also explain the open t3 question (BL10001005 policy value: target -0.03, computed -1.13).
  The risk cap of step 2 also belongs there and would fix the other t3 case (BL10004387 policy value: target 0.00,
  computed -4.38).
- **BL10000775: 2012 risk_charges +0.01, 2020 management_fees -0.01.** One-cent differences, cause not found;
  maybe one of the 0.3 % ADM/RSK splits that fail in t3.

## Open questions

- Move the admin and risk caps into `FundAccounting.charge_run` (t3 and t4 together): +1 t4 row expected, and the
  two negative t3 policy values (diagnostic only; their surrender value is already 0).
- Runtime: t4 replays the whole accounting (about 30 s), and t5 now runs both t3 and t4 (54 s). If time is
  tight, t3 and t4 could share one replay.
