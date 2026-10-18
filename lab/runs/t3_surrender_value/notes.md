# t3_surrender_value: notes

## 2026-10-17, written function (step 4b): 6137 / 6153, holdout 1238 / 1241

No lab candidate is usable: the best one, C2.2/DOWN (5548 / 6153, holdout 1118 / 1241), is a relation to
`policy_value`, a diagnostic column the submission may not read. The policy value is a full unit accounting, so I
wrote the function by hand (step 4b). I checked each step in isolation in scratch scripts outside the repo: first
against the diagnostic files (`t3_holding`, `t3_booking` joined to NRBOOK on a tenth of the train policies), then
as one simulation. No feature was added (no `~llm` run), nothing was frozen.

Step by step, each measured with the true inputs of the step before:

| step | rule | exact |
|---|---|---|
| holdings | sum of booking units with BK_TRDDT <= valuation date, without reversed (900) and 990 events | 3129 / 3129 sample holdings |
| policy value | sum per fund and pot of cents(units x bid x FX); COBOL dates (before 2007-08-11) ROUND_DOWN | 6153 / 6153 |
| surrender value | policy value x (1 - penalty), see below | 6137 / 6153 |
| PRM amount | cents(PR_AMTRC x (1 - entry rate) x allocation share) per fund | 24309 / 24309 sample events |
| ADM split | CG_ADMFEE pro rata to the fund values, the largest holding takes the rounding difference | 41353 / 41459 runs |
| RSK | t2 formula on the value after ADM and AMC, split pro rata to the values after ADM and AMC | 30590 / 30598 runs |
| simulation, 1 in 10 train policies | everything, from the legacy tables only | 607 / 607 policy values |

`lab score` history (ledger.jsonl): the first scored version gave 6137 / 6153 (holdout 1238 / 1241). check.py with
the system Python gives the same, 27 s. NRBOOK is not read (it is only named in a docstring).

Rules (in `FundAccounting` in submission.py, `Market` in neuron.py):
- **Market:** the latest publication (FP_CHGTS) of a price counts. Prices are looked up on the last price date on
  or before the day. FX = CHF rate of the fund currency / CHF rate of the policy currency, on the last rate date on
  or before the day, not rounded. Some NRFXRT codes are in lower case (`chf`, `eur`, ...): upper-case them.
- **Units** = amount / (price x FX), rounded to 6 decimals (ROUND_DOWN before 2007-08-11, half up after), one
  rounding per booking. Every booking uses the same formula; only the price side and the FX day differ.
- **Order of processing:** by trade date. On the same day the charge run (300) comes first, then premiums and
  orders by event number. A premium traded on the day of a charge run is not charged that month. An order on that
  day sells after the charges.
- **Premiums (PRM):** NRPREM items with PR_STATE P (state R items are the reversed ones). Entry rate: NRAGRE ENT
  valid on PR_RCVDT, else NRENTC of the broker tier of the policy version valid on PR_RCVDT. Allocation: the
  NRALLO version valid on PR_RCVDT. Amount per fund = cents(PR_AMTRC x (1 - entry rate) x share), era rounding of
  the trade date. Trade date = the first price date of the fund **after** PR_RCVDT. Price = ask on the trade date.
  FX on the day **before** the trade date: it equals the money date except when a fund has no price on the next
  day (35 of 8000 foreign premiums told them apart). Pot 1 when PR_RCVDT < PH_BEGDT + PD_INIMON months, else pot 2.
- **Charge run (300, EV_EFFDT):** on every holding with units > 0; values = cents(units x bid x FX) on the run date.
  - ADM: CG_ADMFEE (NRCHRG of RK_TARKEY family + generation, valid on the run date), split pro rata to the values.
  - AMC per holding: NRAGRE AMC rate if valid, else CG_AMCP1 for pot 1, CG_AMCP2 for pot 2.
    Java: cents(value x rate / 12). COBOL: ROUND_DOWN(value x rate x days / 360), days from the previous monthly
    anniversary add_months(PH_BEGDT, n - 1) (not the previous run: the first anniversary often has no units).
  - RSK: the t2 risk formula (sum at risk A/B/C, qx of CG_MORTTB, 1 + RK_LOAD, smoker factor, / 12) on the value
    after ADM and AMC. Ages as in t2: COBOL offers (PH_APPDT < 2007-08-11) take round(days / 365) at the start plus
    completed policy years, Java offers the age at the nearest birthday at the start of the policy year. Split pro
    rata to the values after ADM and AMC (with the value of the holdings themselves: 827 runs wrong).
  - Three bookings per holding (ADM, AMC, RSK), each with its own unit rounding.
- **Customer orders (200 switch, 400 withdrawal, 410 surrender, 500 death claim, on EV_EFFDT):** units sold per
  pot = round6(units x EV_PCTG) (of EV_FNDID for a switch), amount = cents(units x bid x FX). A switch buys
  EV_TOFND in the same pot with that amount, at the **bid** price (not the ask).
- **Surrender value:** penalty = NRSURR[PD_SRPSCL, completed policy years], 0 inside an NRWAIV period (2020-04-30 is
  in the COVID waiver), 0 when the policy version valid on the valuation date is in state 60/70, never below 0. Era
  rounding of the valuation date. Policy years count anniversaries with add_months, so a policy that starts on
  29 February completes a year on 28 February (BL10002904).
- **Rows:** every policy whose PH_BEGDT <= valuation date (0 keys too many or too few on train).

t5: t3 is now in `CHECKED`; its valuation dates come from the t3 file in `targets_dir`. check.py t5 finds 34
outliers: 10 from t0, 8 from t2, 16 from t3.

Residuals: 16 rows, all whole-franc increases of the target (+15 to +499), 11 of them listed in NREXCP. They are
manual corrections and go to t5. Examples: BL10000321 2025-12-31 +175, BL10002328 2020-04-30 +499.

Open questions:
- Two negative policy values differ (diagnostic only, surrender value 0 is right): BL10001005 2025-12-31 target
  -0.03, computed -1.13; BL10004387 target 0.00, computed -4.38. Neuron may stop the charges at 0 units.
- The 0.3 % of ADM/RSK splits that fail on the true holdings (106 / 41459 runs) did not change a policy value in
  the sample; a tie or a same-day booking may be the reason.
- `lab/tests/test_submission.py::test_t5_reports_the_manual_corrections` still expects 10 outliers, all from t0.
  It already failed after t2 (see the t2 notes) and now finds 34. The test was not changed.
- Maintainability index (radon mi): submission.py 56.8 -> 33.1, neuron.py 54.3 -> 49.8. The accounting adds about
  200 lines. Moving `FundAccounting` into its own module would raise the index of submission.py; t4 needs the same
  charges, so it should reuse `FundAccounting` (e.g. a hook that records the charge amounts per year).
- Runtime: about 27 s for t3 (reading NREVNT and NRPREM takes most of it).
