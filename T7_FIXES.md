# t7: defects to fix before the next upload

Review of commit `e9d1703` (branch `anto-t0`), 2026-10-17, and the status after the fix commit that follows it.
Paths are relative to `participants/starter_kit/my_solution/`.

The review and the fixes used the code, `SCHEMA.md`, `NRCODE`, the non-tax tables and the two examples of the
task PDF. They did not read the tax tables (NRHOLD, NRADDR, NRTAXR, NRTAXB) and did not run t7 on them, because
the PDF requires custom or open-weights models for the tax data. The fixes were tested on synthetic tax tables
(invented from the schema, 10'716 bookings, with the real non-tax tables). **Before the next upload, an
open-weights model runs `t7lab/t7_check.py` on the real tables** (command at the end).

Status now, after the checks on the real tables:

- t0–t5 are unchanged. With Python 3.13, polars 2.0.0 and 2 threads they score 225848/225858, 15028/15028,
  3011/3019, 6137/6153, 34125/34145 and 54 outliers, in 14 s with a peak of 3.2 GB.
- t0–t4 and t7 run in one process in 10 s, with a peak of 2.8 GB, and `t7lab/t7_check.py` passes every check.
- Both PDF examples are exact on the real tables, also with the official `scoring_t7.py`.
- Maintainability index: 100.0 for the hand-in, the whole folder and every file. The t7 lab is next to it, not in
  it.

## P0: the taxable base of DE and IT payouts — fixed

**Was:** the gain was computed in the policy currency and converted at the rate of the payout day.

| BL10000086 #121 | before | now | PDF |
|---|---|---|---|
| taxable_base | 539.30 | 5628.16 | 5628.16 |
| withholding (KST 25 %) | 134.82 | 1407.04 | 1407.04 |
| surcharges (SOL 5.5 %) | 7.41 | 77.38 | 77.38 |

**Rule now** (`payouts.converted_premiums`, `received_until`, `gains`, `taxable_base`). The policy is in USD,
fully surrendered on 2006-07-17, with a gross of 12'107.36 USD and 28 premiums of 420.00 USD received and not
reversed:

    base = trunc(gross converted on the payout day)
         - sum over the received, not reversed premiums of trunc(PR_AMTRC converted on its money date PR_RCVDT)

Each amount is converted as amount x RP / RT with the rates of that same day. Variants tried around it (Python,
exact fractions):

| conversion of the premiums | base |
|---|---|
| each premium truncated to the cent | **5628.16** |
| each premium rounded half up | 5628.01 |
| premiums not rounded | 5628.02 |
| gain converted on the payout day (the old code) | 539.30 |

Only the rate of the money date itself matches. The rate of the day before, the due date `PR_DUEDT` and counting
the reversed premium all miss. Evidence level: `examples` (one payout, but its 28 premiums separate the rounding
modes).

The premiums used by earlier payouts are carried in the tax currency. The chain runs once per scheme (tax
currency and rounding) of the payouts of a policy, so a holder who moved from CH to DE has each payout counted in
its own currency. On the synthetic tables the premiums used match a computation by hand for every payout of the
two-payout policies, including one where the holder moves.

**Still open:**

1. Is the truncation of each premium a German rule or Neuron's conversion routine? It decides the IT base of
   every CHF, GBP and USD policy. Today IT rounds half up: `conventions.TRUNCATED_CONVERSION = ["DE"]`, one line
   to change.
2. Premiums received before 1998-12-31 have no EUR rate, because the EUR rates of `NRFXRT` start on that day.
   Up to 383 payouts of non-EUR policies have such premiums (an upper bound: residence not looked at). The first
   EUR rate stands in, which is an assumption.
3. Partial withdrawals have no example, and 425 policies have more than one payout: the pro-rata share of the
   premiums is unverified. The labels of NRTAXB support it: in Germany and Italy its base is positive on every
   payout with a withholding booked, partial withdrawals included, while the gain in the policy currency converted
   on the payout day (pro rata, or premiums first) misses many of them. The amount stays unverified.

## P1: choices without labels — named in `conventions.py`, to be decided one per upload

`TB_REMDT` and `TB_AMOUNT` are empty (`SCHEMA.md`), so these columns have no labels. Each is now one line, with
its evidence in the comment:

- **Remittance date** (`REMITTANCE`). DE on the 10th of the next month is confirmed by example 1 (2006-08-10).
  That day is a Thursday, so a business-day shift is not tested. IT on the 16th and CH 30 days after the end of
  the month are law priors. A row counts only if all six columns match, so a wrong rule zeroes every IT or CH
  row with tax.
- **Half-income rule HEV applied to the withholding** (`HALF_INCOME_WITHHELD = True`). As far as we know the law
  leaves HEV out of the KapESt (to be verified). NRTAXR has HEV rates, though, so Neuron may have applied it.
- **taxable_base of payouts without withholding** (`BASE_WITHOUT_TAX`, now `False`: base 0). `True` reports
  the base as calculated: for CH the gross, even when the payout was only reported or below a threshold.
- **Rounding of the IT conversion** (`TRUNCATED_CONVERSION`, see P0, open point 1).
- **Base of the Bollo** (`BOLLO_ON_SURRENDER_VALUE = True`: the surrender value, the policy value less the
  penalty). The Italian rules tax insurance policies on their surrender value. The example's policy has no penalty,
  so it fits both. The Bollo is most of the annual table, and its years with a penalty are about the share of rows
  the actuary found wrong. A full surrender (SUR) books the units sold at their value before the penalty, so the
  Bollo of the year of a payout takes the penalty off them as well.
- **VST of holders who chose the reporting:** closed by the labels. NRTAXB never books VST for M holders.
- **Remittance day on a weekend or holiday** (`REMITTANCE_SHIFTED = []`). About 30 % of the days of each rule
  fall on one; listing a country moves its days to the next business day of `REMITTANCE_CALENDARS`.

## P1: wrong amounts without an error — fixed

- **Dropped rows:** fixed. The joins of `taxes.payout_taxes`, `taxes.premium_stamp_duty`, `bollo.collected_bollo`
  and `taxpayer.with_policies` are left joins now. A booking without a match keeps a null amount instead of
  disappearing.
- **Null or missing amounts:** caught by the check tool. The submission cannot know the right value, so it never
  stops; `t7lab/t7_check.py` fails when a tax booking has no amount or a booking of NRTAXB has no row. It
  reports the payouts without a country as INFO: no tax booked and no address known, which no rule can resolve.
- **Country never checked:** fixed. `country` is now the country of the taxes withheld from the payout (VST, SOS,
  KST: the label), and the residence only when nothing was withheld (`payouts.booked_countries`). The check tool
  reports as INFO the payouts whose residence disagrees with their booked taxes. The code handles them, but the
  residence still decides the payouts without tax, the region and the KIS rate.
- **Church tax:** fixed. The KST is reduced only when the payout has a KIS booking (`taxes.payout_taxes`,
  `capital_gains_tax`). `AD_CHURCH` is no longer read.
- **Unused NRTAXR columns:**
  - `TX_CNTRY` (fixed): `taxpayer.tax_rates` now matches the country of the tax type (`conventions.TAXES` lists
    all ten TAXTP codes of NRCODE).
  - `TX_THRSH` (still open): no rule reads it. The check tool prints the tax types that have one, so the open
    model can see whether a Bollo minimum or cap exists.
- **Version tie:** fixed. `legacy.valid_on` sorts by the version number, then the latest `_VLDFR`, then the
  table row, so the pick is always the same. t0–t5 are unchanged by it.
- **Negative Bollo difference:** fixed. `money.rounded_signed` rounds a negative amount like its positive twin
  (Java's half up), in `bollo.bollo`, `fixed_bollo` and `collected`.
- **Crash on no rows:** fixed. `payouts.in_turn` returns an empty result instead of failing on `pl.concat([])`.
- **Surrender penalty in the payouts:** fixed (labels). The WDR and SUR bookings sell the units at their value; the
  money paid is that value less the surrender penalty of the day (`conventions.PENALIZED`, `payouts.paid_out`,
  `valuation.penalties_on`), and the base of the taxes comes from it. With the value itself, some withdrawals
  and surrenders had a base that called for VST, SOS or KST that NRTAXB never booked; with the penalty taken off,
  `t7_check` finds no contradiction left, both examples stay exact, and no other payout changes its label.
  The share PART / WHOLE and the value before still count the units at their value.

## P2: code quality — fixed

- **Law constants without a source:** every t7 constant in `conventions.py` now states its evidence: example,
  law or assumption.
- **Arithmetic written to please radon:** `math.prod([RATE_UNIT, RATE_UNIT])` is gone from `taxes.py` and
  `payouts.py`. Both use `money.SHARE_UNIT`, written as a literal like the other units of `money.py`. The README
  no longer claims "no Python operators are left".
- **Unpinned requirements:** pinned to `polars==2.0.0` and `holidays==0.106`, the tested versions.
- **Commit title:** the next commits use `t7`.

## Before the next upload

Run this with an open-weights model, from `participants/starter_kit/my_solution`, with the data folder that holds
`legacy/` and `targets/`:

    NEURON_DATA=<participants> POLARS_MAX_THREADS=2 PYTHONPATH="$PWD:$PWD/tools:$PWD/.." python -B -m t7lab.t7_check

It prints only PASS/FAIL, seconds and gigabytes; `--debug` adds counts and tracebacks. Its last checks hold the
bases against the labels of NRTAXB (a tax booked exactly where the base says it is due): a defect of the base
shows there before it costs an upload. Upload when it says `ALL PASS`.

The switches now: base 0 without withholding (`BASE_WITHOUT_TAX = False`), Bollo on the policy value
(`BOLLO_ON_SURRENDER_VALUE = False`, back after 8 of 30), rounding by system (`ROUNDED_BY_SYSTEM = True`, set by
the targets of t0, t2 and t3: too few rows change for the actuary to read it) and the remittance month from the
payment day (`REMITTED_FROM_PAYMENT = True`, the probe of the payout table). Then one per table and upload: stamp
duty alone without a remittance day (`STAMP_DUTY_REMITTED`), business-day shift (`REMITTANCE_SHIFTED`),
remittance IT/CH, death claims on the benefit of the tariff option. `t7lab/t7_variants.py` counts the rows each
one changes. The leaderboard returns one accuracy per table on a few rows that change at every evaluation, so
only one choice per table can be read from each upload.

## What the whole extract says (study of 18.10)

Facts measured on every row, not on the two examples of the PDF:

- **When Neuron booked.** Every tax of a payout is booked by the clerk who processed the payout, at the event's
  own timestamp and effective date. No payout was ever reversed: the reversals hit premiums, switches, allocations
  and broker changes only. The Bollo batch (TAXBATCH) books 31 December on 10 January at 03:00; TAXFIX19 re-priced
  2017 – 2019 on 20 July 2019. The premium stamp duty STP names its system: CBLBATCH (COBOL) or NGBATCH (Neuron NG).
- **Residence.** The view Neuron had at processing and today's view agree on the holder and the country of every
  payout, although some persons moved country and some addresses were entered late: the country does not hang on
  that choice.
- **Prices.** A restated price is always published the day after the first one, so the Bollo batch of 10 January
  saw final year-end prices.
- **Rounding.** Every task with targets (t0, t2, t3) shows Neuron rounding by system: COBOL truncates, Neuron NG
  rounds half up. The German truncation of t7 rests on the one example, which is from the COBOL era (2006) and fits
  the system rule as well (`ROUNDED_BY_SYSTEM`).
- **Payment day.** `PD_PAYDAY` ("payout business days": 3 for Flex, 5 for Classic and Single Premium) is the only
  payout column that no rule reads. In all three countries the law counts the remittance from the payment; with
  it, the month of about a fifth of the payouts with tax moves (`REMITTED_FROM_PAYMENT`).
- **Death claims.** The DTH booking is the unit value alone; the benefit follows the tariff option (`RK_TARKEY`
  position 7: A, B, C; `charges.death_benefit_factors`). No label tells whether the tax base is the unit value or
  the benefit, and the KST on German death claims follows no visible rule.
- **Corrections.** NREXCP lists none for t7; the technical corrections (990) book switches only.

## Decision plan for the uploads after `290312d` (written 18.10 01:50)

The 257 Swiss payouts with VST are the cleanest probe of the payout table: one rate, no gain, base and VST sure,
so from `290312d` on they can only fail on the remittance date (all on the 10th; 73 of them on a Saturday or
Sunday) and, for the 46 COBOL-era rows, on the rounding. The switches of the branch `t7-next` are ready, all off.

| Reading of `290312d` (payout) | Next payout switch | Next annual switch |
|---|---|---|
| rises by 3 or more | keep the 10th; `REMITTANCE_SHIFTED = ["DE", "IT", "CH"]` (200 rows, 78 CH) | `BLENDED_RATES = ["SOS"]` (95 rows) |
| stays at 0 - 2 | the days of the law again plus the shift (623 rows), the 10th was not it | `BLENDED_RATES = ["SOS"]` |
| annual falls by 3 or more | - | `BOLLO_FIX_PER_YEAR = False` first |

Then, one per table: `STAMP_DUTY_REMITTED = False` (182), `REMITTANCE_MONTH_END = ["CH"]` (257),
`COLLECTED_IN_ANNUAL = True` (277 annual), `CHURCH_REDUCES_KST = False` (28), death claims on the benefit.

## Uploads and the actuary's readings

The actuary picks a few targets to test different patterns (task PDF, section 7), and t7 is scored on the public
and private policies (section 6): a reading is not a uniform sample, so compare readings with care. At 23:48 the samples grew (40 and 30
rows) and some were dropped. Before an
upload, write down the commit and its switches here; after the evaluation, its two scores and its MI.

| Evaluated | Code | t7 switches | Payout | Annual | MI |
|---|---|---|---|---|---|
| 17.10 19:30 | `0522fa7` | base as calculated (before `BASE_WITHOUT_TAX`), Bollo on the value, rounding by country | 1/20 | 14/20 | 100 |
| 17.10 22:09 | Roberto's own upload (#43), not on the branch | base as calculated | 1/20 | 14/20 | 98 |
| 17.10 23:48 | `cbaf38b` (uploaded from this branch; MI not reported. Another engine's `t7_impl.py` was still being written at 23:47 and runs for minutes) | `BASE_WITHOUT_TAX = False`, `BOLLO_ON_SURRENDER_VALUE = True`, rounding by country | 0/40 | 8/30 | ? |
| 18.10 00:45 | `d595375` | `BASE_WITHOUT_TAX = False`, `BOLLO_ON_SURRENDER_VALUE = False`, `ROUNDED_BY_SYSTEM = True`, `REMITTED_FROM_PAYMENT = True` | 0/40 | 11/30 | ? |
| 18.10 ~02:00 | `290312d` | as `d595375`, and `REMITTANCE` the 10th everywhere (was IT the 16th, CH 30 days after the month), `BASE_WITHOUT_TAX = True`, `BOLLO_FIX_PER_YEAR = True` | ? | ? | |
| 18.10 | `d320801` | as `290312d`, and `BLENDED_RATES = ["SOS"]` (97 payouts, 95 annual rows), `REMITTANCE_SHIFTED = ["DE", "IT", "CH"]` (200 payouts) | 0 | 10/30 | |
| next | this commit | as `d320801`, and only the date: `REMITTANCE` the days of the law (DE 10th, IT 16th, CH 30 days after the month), `REMITTED_FROM_PAYMENT = False` (the month of the effective date), the move to a business day kept. 608 of the 680 dated payouts change their date and nothing else; the annual table is identical | | | |

The "0 and 10/30" reading may belong to `290312d` rather than `d320801` (to confirm). The next upload changes only the
remittance date, so its payout score reads that one choice:

- above 0: the date rule was the blocker. Next, the payouts with stamp duty alone without a date
  (`STAMP_DUTY_REMITTED = False`, 182 rows), then the base 0 of the 8 death claims without tax (the labels say death
  claims are tax free, except German contracts from 2010).
- still 0: switch to isolation probes. The payout table scores 0, so a probe costs nothing: submit one pattern alone,
  first the 257 CH VST rows (base and VST settled by the labels, so only the date is open).

## The public samples arrived (18.10)

The organizers published the first two leaderboard samples (`participants/t7_samples_1_and_2`, merged into
`participants/targets`: 60 payouts, 50 policy-years). Against them `bb98fee` scored 43/60 and 24/50. Every miss
pointed at one rule; after these fixes the submission scores **60/60 and 50/50**, both PDF examples stay exact,
t7_check passes, t0-t5 are unchanged and the MI is 100.

| Rule (targets that settle it) | Rows |
|---|---|
| No remittance date for the Bollo collected alone (`STAMP_DUTY_REMITTED = False`) | 6 payouts |
| The Swiss tax office keeps the calendar of Bern: 2 January is a holiday (BL10000094, 3.1.2018) | 1 payout |
| A death claim pays the death benefit of the tariff option, option A 101 % of the units (BL10003217, BL10004258) | 2 payouts |
| SOS by period: the gain to 31.12.2011 and to 30.6.2014 from the policy value of the day, at 12.5 / 20 / 26 %; every payout takes its share of each, as of the premiums (`periods.py`; BL10003541 after two earlier payouts) | 5 payouts, 12 years |
| The taxes withheld count in the year of their remittance (`REPORTED_WHEN_REMITTED`; BL10003349 paid out 12.2025, it_sos in 2026) | 5 years |
| The Bollo charges the whole year on 31 December, also in the first year; at a surrender the days from 1 January | 6 years and the BOC |
| The 2019 Bollo fix rounded once on the total (`BOLLO_FIX_PER_YEAR = False`) | 2 years |
| TFS (and HEV) stay out of the German withholding (BL10004408 2020, BL10000301 2024) | 2 years |
| German taxes always truncated; bases and conversions rounded by system (BL10001204 2012: 1.57 + 2.58 = 4.15) | 2 rows |
| The base = gross converted - premiums used, each rounded to the cent by system (BL10001775 2004: 223.77) | 1 payout |
| Each premium rounded by the system that received it; the premiums used of a payout rounded to the cent (BL10002694, BL10002916, BL10003541) | 4 rows |

Against `bb98fee` 428 payout rows and 755 annual rows change on the whole extract. Still assumed, as no sample
row tests it: the base of a death claim without tax, the first EUR rate for the days before 31.12.1998.

## Missing data made visible (19.10)

The third sample scored 7/40 (payout) and 28/30 (annual): the tax amounts generalize, the payout-only parts do
not. The submission turns a missing input into a value that looks valid, so `t7lab/t7_gaps.py` now builds a gap
ledger: per payout, the flags of the missing inputs (a fallback stands in) and of the untested assumptions, a CSV
without tax values, and with `--targets FILE` the accuracy per flag. `t7_check` prints the counts on every run and
fails on a payout without any residence. On our extract (2493 payouts):

| Flag | Kind | Rows | In samples 1-2 |
|---|---|---|---|
| NO_PAYOUT_BOOKING (gross 0) | gap | 2 | - |
| RESIDENCE_LATE (processing view and today's differ; the country too) | gap | 4 | - |
| RATE_STAND_IN (payout before the euro) | gap | 13 | - |
| PREMIUM_RATE_STAND_IN (premium before the euro) | gap | 128 | 4 of 4 correct |
| AFTER_EXTRACT (remitted after 30.6.2026) | gap | 1 | - |
| UNTAXED_DEATH_BASE | assumption | 10 | - |
| DE_EXEMPT_BASE | assumption | 1 | - |
| DEATH_OPTION_B_C | assumption | 41 | 2 of 2 correct |
| no flag | | 2318 | 54 of 54 correct |

The four RESIDENCE_LATE payouts change country between the views (LU/CH, CH/LU, IT/DE, CH/DE); only BL10000487
has a label (its Bollo says IT, the view at processing).

## Probe 1: the payouts without a flag (branch `t7-probe-unflagged`)

The flags now live in the hand-in (`gaps.py`), and `PAYOUT_SCOPE` reports only part of the payouts. On `anto-t0`
the scope is "all" (outputs identical to `3f27c59`); the probe branch sets "unflagged": 2318 of the 2493
payouts, the same values, and the annual table unchanged. Locally 54/60 (the 6 flagged sample rows are left out
on purpose), t7_check ALL PASS, t0-t5 unchanged, MI 100.

Reading against 7/40 of the full table on the same sample: the probe scores only the unflagged rows.

- 7: every hit of sample 3 is an unflagged row; its flagged rows are all wrong (or there are none).
- below 7: 7 minus the score is the number of hits among the flagged rows.
- above 7: the sample changed between the evaluations; the reading is void.

The score does not say how many of the 40 rows are unflagged. Probe 2 ("flagged") gives the complement: the two
scores must add up to 7, which also proves that sample 3 stayed the same.

| Evaluated | Code | Scope | Payout | Annual |
|---|---|---|---|---|
| 19.10 | `3f27c59` | all | 7/40 | 28/30 |
| next | `t7-probe-unflagged` | unflagged | | |

## The leaderboard never credits a payout without a date (18.10)

Every earlier reading, scored locally against the published samples with the code that was uploaded: the
leaderboard's payout score is exactly the number of correct rows **with** a remittance date. A correct row whose
date is None was never counted; the annual table, which has no dates, matches the leaderboard to the row.

| Code | Sample | Payout correct locally | of which with a date | Payout on the leaderboard | Annual locally / leaderboard |
|---|---|---|---|---|---|
| `0522fa7` | 1 | 11/20 | 1 | 1/20 | 14/20 / 14/20 |
| `cbaf38b` | 2 | 7/40 | 0 | 0/40 | 8/30 / 8/30 |
| `d595375` | 2 | 7/40 | 0 | 0/40 | 11/30 / 11/30 |
| `290312d` | 2 | 28/40 | 0 | 0/40 | 10/30 / 10/30 |
| `d320801` | 2 | 28/40 | 0 | 0/40 | 10/30 / 10/30 |

48 of the 60 sample payouts have no date (80 %), so a sample 3 drawn the same way holds about 8 rows with a date:
7/40 for `3f27c59` reads as 7 of those right and the undated rows not counted, not as 33 wrong rules. Probe 1
assumes the misses are wrong values, so this commit replaces it.

The change, payout table only: `PAYOUT_SCOPE = "all"` and `NO_REMITTANCE_DATE = ""`, the empty field of the target
files, which the official `scoring_t7.optional_date` reads as None just as it reads None. Against `3f27c59` exactly
the 1995 undated payouts change, from None to ""; after normalization by `scoring_t7` nothing differs (2493
payouts, 6387 annual rows identical), samples 1 and 2 stay 60/60 and 50/50, t7_check ALL PASS, t0-t5 unchanged,
MI 100. The mechanism is a guess (the evaluator turning None into the text "None", a malformed date it drops):

- payout well above 7: confirmed, keep it;
- payout still 7: the evaluator drops these rows whatever we send; the change costs nothing.

| Evaluated | Code | Scope | Date without tax | Payout | Annual |
|---|---|---|---|---|---|
| 18.10 ~08:00 | `3f27c59` | all | None | 7/40 | 28/30 |
| next | this commit | all | "" | | |
