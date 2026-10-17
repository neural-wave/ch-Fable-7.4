# t7: defects to fix before the next upload

Review of commit `e9d1703` (branch `anto-t0`), 2026-10-17. Paths are relative to
`participants/starter_kit/my_solution/`.

The review used the code, `SCHEMA.md`, `NRCODE`, the non-tax tables and the two examples of the task PDF. It did
not read the tax tables (NRHOLD, NRADDR, NRTAXR, NRTAXB) and did not run t7, because the PDF requires custom or
open-weights models for the tax data. Every check below that needs those tables must be run with an
open-weights model.

Status:

- t0–t5 are unaffected by the changes to the shared modules (`legacy`, `bookings`, `valuation`). With Python
  3.13, polars 2.0.0 and 2 threads they score as before: 225848/225858, 15028/15028, 3011/3019, 6137/6153,
  34125/34145 and 54 outliers, in 14 s and about 3 GB.
- t7 fails example 1 of the task PDF (`BL10000086,121`), as the README says (lines 231–234). Example 2
  (`BL10000044,2019`, 616.11) matches according to the README; not verified here.

## P0: the taxable base of DE and IT payouts fails PDF example 1

**Where:** `payouts.py`: `received_until` (81–87), `premiums_used` (90–93), `gains` (96–100), `taxable_base`
(115–123); `taxpayer.with_tax_currency` (60–70).

**Now:** the gain is computed in the policy currency and converted at the rate of the payout day.

| BL10000086 #121 | now | PDF |
|---|---|---|
| taxable_base | 539.30 | 5628.16 |
| withholding (KST 25 %) | 134.82 | 1407.04 |
| surcharges (SOL 5.5 %) | 7.41 | 77.38 |

**Rule that reproduces the example to the cent.** The policy is in USD, fully surrendered on 2006-07-17, with a
gross of 12'107.36 USD and 28 premiums of 420.00 USD received and not reversed:

    base = trunc(gross converted on the payout day)
         - sum over the received, not reversed premiums of trunc(PR_AMTRC converted on its money date PR_RCVDT)

Each amount is converted as amount x RP / RT (as in `with_tax_currency`) with the rates of that same day
(`rate_of(..., same_day=True)`). The rule gives 5628.16; 25 % of it is 1407.04, and 5.5 % of that, truncated,
is 77.38.

Variants tried around it (Python, exact fractions):

| conversion of the premiums | base |
|---|---|
| each premium truncated to the cent | **5628.16** |
| each premium rounded half up | 5628.01 |
| premiums not rounded | 5628.02 |
| gain converted on the payout day (current code) | 539.30 |

Only the rate of the money date itself matches. The rate of the day before, the due date `PR_DUEDT` and counting
the reversed premium all miss. Evidence level: `examples` (one payout, but its 28 premiums separate the rounding
modes).

**Fix:** convert every premium to the tax currency at its own money date and round it there (truncate in DE),
then sum. The premiums used by earlier payouts (`in_turn`, `premiums_used`) must be carried in the tax currency,
not in the policy currency. Convert the gross on the payout day. Keep the final rounding of the base.

**Scope:** there are 2'493 payout events (1'319 partial withdrawals, 1'099 surrenders, 75 death claims, none
reversed). 1'853 of them are on CHF, GBP or USD policies, and every DE or IT holder among them is affected.

**Still open after the fix:**

1. Is the truncation of each premium a German rule or Neuron's conversion routine? It decides the IT base of
   every CHF, GBP and USD policy; today IT rounds half up (`conventions.TRUNCATED`).
2. Premiums received before 1998-12-31 have no EUR rate, because the EUR rates of `NRFXRT` start on that day.
   Up to 383 payouts of non-EUR policies have such premiums (an upper bound: residence not looked at). Today
   the first EUR rate stands in (`with_tax_currency` 68–70), which is an assumption.
3. Partial withdrawals have no example, and 425 policies have more than one payout: the pro-rata share of the
   premiums is unverified.

## P1: choices without labels

`TB_REMDT` and `TB_AMOUNT` are empty (`SCHEMA.md`), so these columns have no labels. Make each one a named
convention marked as an assumption, so that one upload can change one of them:

- **Remittance date** (`conventions.REMITTANCE`, `taxes.remittance` 86–95). DE on the 10th of the next month
  is confirmed by example 1 (2006-08-10). That day is a Thursday, so a business-day shift is not tested. IT on
  the 16th and CH 30 days after the end of the month are law priors. A row counts only if all six columns
  match, so a wrong rule zeroes every IT or CH row with tax.
- **Half-income rule HEV applied to the withholding** (`payouts.german_factor` 103–112). To our knowledge the
  law ignores it for the KapESt (to be verified). NRTAXR has HEV rates, though, so Neuron may have applied it.
- **taxable_base of payouts without tax** (`taxable_base` 115–123). CH gives the gross even when the payout was
  only reported (`AD_TAXST`) or was below a threshold; LU gives 0, and so do the old German contracts.
- **Rounding of the IT conversion** (see P0, open point 1).

## P1: wrong amounts without an error

These paths drop rows or turn missing data into 0 silently. Add one check that fails loudly: every row of
`NRTAXB` gets a non-null amount, and every payout gets a non-empty country.

- **Dropped rows.** Inner joins drop the tax bookings without a match: `taxes.payout_taxes` (65, payouts),
  `taxes.premium_stamp_duty` (43, NRPREM), `bollo.collected_bollo` (85, payout shares),
  `taxpayer.with_policies` (57).
- **Missing rates become 0.** A missing rate gives a null `TB_AMOUNT`, and the sums of `payout_table` (101–102)
  and `annual_table` (113–114) skip nulls, so the amount becomes 0.
- **Empty country.** `payout_table` (105) fills an unknown residence with `""`.
- **Country never checked.** `country` comes from the residence lookup alone. It is never compared with the
  country of the booked tax types (`conventions.TAXES`), which are labels.
- **Church tax.** The reduction of the KST for church members (`taxes.capital_gains_tax` 51–56) depends on
  `AD_CHURCH` and on a valid KIS rate. It should depend on a KIS booking for that payout, which is the label.
- **Unused NRTAXR columns.** `taxpayer.tax_rates` (37–51) ignores `TX_CNTRY`, which is part of the key of NRTAXR;
  this is harmless only if every `TX_TAXTP` belongs to one country (check it). `TX_THRSH` is never read: check
  what it holds, because a minimum or a cap of the Bollo would change amounts.
- **Version tie.** `legacy.valid_on` (84) keeps the highest version number after a sort that is not stable.
  NRTAXR numbers its versions per validity start (`TX_VLDFR` is in the key), so two valid rows can share a
  number, and the pick may then be arbitrary. Break the tie explicitly: latest `_VLDFR`, then latest `_CHGTS`.
- **Negative Bollo difference (minor).** `money.rounded` assumes numerators that are not negative (27).
  `bollo.fixed_bollo` (68–70) gives a negative difference if a restated rate is lower, and floor division then
  rounds it the wrong way.

## P2: code quality

- **Law constants without a source:** `OLD_CONTRACT`, `HELD_YEARS`, `HALF_INCOME_AGE`, `HALF_INCOME_2012`,
  `REMITTANCE` (IT, CH) and the church formula (`conventions.py` 58–69). Give each its source and its status:
  law prior, confirmed by an example, or confirmed by the actuary.
- **Arithmetic written to please radon:** `math.prod([RATE_UNIT, RATE_UNIT])` (`taxes.py` 28, `payouts.py` 36)
  and the README claim "no Python operators are left" (238–242). Plain `RATE_UNIT * RATE_UNIT` reads better;
  MI is a signal, not a target.
- **Unpinned requirements:** `requirements.txt` has `polars>=1.31` and `holidays>=0.60`, so the evaluator
  installs the newest versions at every run. Pin the tested ones: `polars==2.0.0` and `holidays==0.106`.
- **Commit title:** the t7 commit is titled `feat(t4)`; use `t7` in the next ones.

## Before the next upload

1. Examples 1 and 2 of the PDF are exact. Run this with an open-weights model, since it reads the tax tables.
2. The P1 check passes: no tax booking without an amount, no payout without a country.
3. t0–t5 are unchanged (numbers above).
4. t0–t4 and t7 run in one process well under 5 minutes and 5 GB (the evaluator has 2 CPUs and 5 GB).
5. After that, change one thing per upload, in this order: remittance IT/CH, rounding of the IT conversion,
   HEV, base without tax. The leaderboard returns one accuracy on a few rows that change at every evaluation,
   so only one choice can be read from each upload.
