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
  the actuary found wrong. The gross of a full surrender (SUR) is the value before the penalty, so the Bollo of the
  year of a payout takes the penalty off it as well.
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

It prints only PASS/FAIL, seconds and gigabytes; `--debug` adds counts and tracebacks. Upload when it says
`ALL PASS`, then change one convention per table and upload, in this order: base without tax
(`BASE_WITHOUT_TAX`, now `False`: the payout table) with the base of the Bollo (`BOLLO_ON_SURRENDER_VALUE`, now
`True`: the annual table, which the base does not touch), rounding by system (`ROUNDED_BY_SYSTEM`), stamp duty
alone without a remittance day (`STAMP_DUTY_REMITTED`), business-day shift (`REMITTANCE_SHIFTED`), remittance
IT/CH, rounding of the IT conversion, HEV. `t7lab/t7_variants.py` counts the rows each one changes. The
leaderboard returns one accuracy per table on a few rows that change at every evaluation, so only one choice per
table can be read from each upload.
