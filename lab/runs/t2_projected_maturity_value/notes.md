# t2_projected_maturity_value: notes

## 2026-10-17, written function (step 4b): 3011 / 3019, holdout 622 / 622

No lab candidate: `lab run` reports "No relation with dense clusters" for `maturity_value` (and for the diagnostic
`t2_projection_year`). The value comes from a monthly simulation, not from one relation, so I wrote the function
by hand and worked through the yearly diagnostic in scratch scripts (outside the repo). No feature was added (no
`~llm` run), nothing was frozen.

Score history (`lab score`, all in ledger.jsonl):

| change | exact | holdout |
|---|---|---|
| premium, admin, AMC p2, risk, growth i/12, round the value after growth, age at start of policy year | 811 | 180 |
| + smoker factor CG_SMKFAC for PS_SMOKE in {Y, J} | 1003 | 219 |
| + medical loading x (1 + RK_LOAD) | 1132 | 245 |
| age at the nearest birthday (start of the policy year + 6 months) | 2184 | 469 |
| COBOL era (PH_APPDT < 2007-08-11) rounds down (ROUND_DOWN) | 2990 | 618 |
| COBOL entry age = round(days(birth, start) / 365), plus policy years | 3011 | 622 |

check.py with the system Python gives the same 3011 / 3019 in 2 s. NRBOOK is not read.

Rules:
- **Grain:** one projection per NRRISK row. The offer is the **first** NRPOLH version (lowest PH_VRSNR): later
  changes (premium holiday, paid-up, broker change) do not change the projection.
- **Parameters on PH_APPDT:** NRILLU rate, NRCHRG row of (tariff family RK_TARKEY[1:2], generation [4:5]), and
  the NRENTC rate of the broker's tier.
- **Months:** `months_between(PH_BEGDT, PH_ENDDT)` steps. In month m:
  1. premium on the due months (m % 1/3/6/12 == 0; single premium E only in month 0):
     `+ cents(PH_PREMI x (1 - entry rate))`;
  2. `- CG_ADMFEE`;
  3. `- cents(value x CG_AMCP2 / 12)`: the whole value is one amount, so only the pot 2 rate applies. With pot 1
     for the first PD_INIMON months the score falls (tested: year 1 off by about 30);
  4. risk: `- cents(sum at risk x qx x (1 + RK_LOAD) x smoker factor / 12)`. Sum at risk by RK_TARKEY[7]:
     A = 1 % of the value, B = max(RK_SUMIN - value, 0), C = RK_SUMIN. qx = NRMORT[CG_MORTTB, sex, entry age +
     completed policy years]. Sex from RK_TARKEY[3] (M/W), PS_SEX for U;
  5. growth: `value = cents(value x (1 + IL_RATE / 12))`, a nominal twelfth, not (1 + i)^(1/12).
- **System change (PH_APPDT < 2007-08-11 = COBOL):** every rounding is ROUND_DOWN, and the entry age is
  `(days(PS_BIRTH, PH_BEGDT) + 182) // 365`, i.e. days / 365 rounded. The fraction of days/365 separates the
  boundary cases cleanly (all < 0.5 fit the lower age, all > 0.5 the higher). Recomputing days/365 at every
  anniversary is worse (812 of 829 old offers); entry age + policy years gives 827 of 829.
  Java (from the change on): ROUND_HALF_UP, entry age = completed years at PH_BEGDT + 6 months.
- **Impossible birth dates** (10 in NRPERS, e.g. 690631): read as the month end. In train both readings, month end
  and the first of the next month, give the same values; all 8 train policies with one are exact.
  `neuron.day(n, month_end=True)` does this. `neuron.table` keeps such numbers in `<column>_RAW`, like the lab
  store; `day()` without the flag still returns None, so the loader parity test still passes.
- New helpers in neuron.py: `months_between`, `age`, and `day(..., month_end)`. t0/t1 are unchanged (225848 and
  15028).

Residuals (8, all manual corrections):
- in NREXCP: BL10001762, BL10003323, BL10003583, BL10003808;
- not listed, whole-number differences at maturity, with every yearly value of t2_projection_year exact:
  BL10000128 (-4855), BL10002196 (-1726), BL10002973 (-1498), BL10004278 (-3294).

t5: t2 is now in `CHECKED` (key `str`, value `Decimal`). check.py t5 finds 18 outliers: 10 from t0, 8 from t2.
`lab/tests/test_submission.py::test_t5_reports_the_manual_corrections` asserts exactly 10 outliers, all from t0,
so it now fails (95 passed, 1 failed, 2 skipped). The test was not changed: it has to be updated to expect the 8 t2
outliers too.

Open questions:
- Hidden policies with PH_APPDT exactly on 2007-08-11: the rule takes the Java branch (`applied < SYSTEM_CHANGE`
  is COBOL). Train has no case that tests the boundary day.
- Whether the era is set by PH_APPDT or by the processing timestamp of version 1 (PH_CHGTS, 3 days after
  PH_APPDT in the samples): not separable in train.
- Ages above the last NRMORT age would raise KeyError; none occur in train.
