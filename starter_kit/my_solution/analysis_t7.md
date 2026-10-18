# T7 Tax Module - Data Analysis Report

## Executive Summary

This analysis covers the derivation of rules for the two t7 functions from the Neuron legacy data tables and the example output values provided in the task description.

## Key Findings

### 1. Function Signatures Added to submission.py
```python
def t7_tax_payout(legacy_dir) -> dict[tuple[str, int], tuple]
def t7_tax_annual(legacy_dir) -> dict[tuple[str, int], tuple[Decimal, ...]]
```

### 2. Data Table Relationships Discovered

#### NRTAXB (Tax Bookings)
- **Contains:** (policy_id, event_nr) → tax_type, effective_date
- **Does NOT contain:** amounts or remittance dates (all fields are empty)
- Serves as the **mapping** between events and tax treatments
- Tax types found: KST, SOL, KIS (German); VST, STP (Swiss); SOS, BOL, BOS (Italian); BOG (corrections)
- 1794 unique (policy, event, tax_type) combinations produce output

#### NREVNT (Event Registry) - CRITICAL
- Maps event number to event type:
  - 100 = issue, 110 = premium receipt
  - 400 = partial withdrawal, 410 = full surrender
  - 500 = death claim
- German KST/SOL events are always event types 400 or 410
- Swiss STP events are event type 110 (premium receipt)
- Italian SOS/BOS events appear on various events

#### NRBOOK (Bookings) - CRITICAL
- BK_EVENTNR directly maps to NRTAXB TB_EVTNR  
- BK_AMTPC gives the monetary amount for each booking (in cents)
- BK_FUNDID, BK_POTCD identify which fund the amount belongs to
- BK_BKTYP identifies booking type: SUR (surrender), PRM (premium), etc.
- For BL10000086 event 121: 8 SUR entries totaling 12,107.36 CHF

#### NRHOLD → NRADDR (Policyholder → Residence)
- NRHOLD HD_POLNR → HD_PERNR links policy to person
- NRADDR per person gives residence history (country, region, tax status, church membership)
- **Date format issue:** dates are stored as 6-digit (YYMMDD) or 7-digit (1YYMMDD) integers
  - 900101 = 1990-01-01, 1060717 = 2006-07-17
- The "9999999" end-date means "still valid / no end"

#### NRTAXR (Tax Rates)
- Rate format: raw_value / 10000 = percentage
  - 250000 → 25%, 55000 → 5.5%, 80000 → 8%, 260000 → 26%
  - 25000 (STP) → 2.5%, 2000 (BOL) → 0.2%
- Threshold format: raw_value / 100 = CHF
  - VST threshold: 500000 → 5000.00 CHF
- Multiple valid versioned rates per tax type (historical tax changes)

#### NRPREM (Premiums)
- Total premiums per policy needed for gain calculation
- BL10000086: 28 premiums totaling 11,760.00 CHF

## Example Analysis: BL10000086 (German KST/SOL)

| Field | Expected | Computed | Match? |
|-------|----------|----------|--------|
| Country | DE | DE | ✓ |
| Taxable Base | 5628.16 | 347.36 | ✗ |
| Withholding | 1407.04 | 0.00 | ✗ |
| Surcharges | 77.38 | 0.00 | ✗ |
| Stamp Duty | 0.00 | 0.00 | ✓ |
| Remittance | 2006-08-10 | 2006-08-10 | ✓ |

### Key Insight: The Taxable Base Formula

For BL10000086 event 121 (full surrender):
- **Payout** = 12,107.36 CHF (from NRBOOK event 121)
- **Total premiums** = 11,760.00 CHF (from NRPREM)
- **Gain** (payout - premiums) = 347.36 CHF
- **Expected taxable_base** = 5628.16 CHF (from example)

**Discrepancy:** The gain (347.36) does NOT equal the taxable base (5628.16). The taxable base is **not** simply payout minus total premiums.

**Likely formula:** For German life insurance payouts, the taxable base should be computed using the **fund-based** approach:
- `taxable_base = payout / fund_accumulation_factor - accumulated_premiums`
- Or: taxable_base = insurance_gain using the German "Anwartschaftsverhältnis" formula
- This requires historical fund prices from NRFPRC and the fund price at each premium payment date

### Example Analysis: BL10000044, 2019 (Italian BOL)

| Field | Expected | Computed | Match? |
|-------|----------|----------|--------|
| ch_stp | 0.00 | 0.00 | ✓ |
| ch_vst | 0.00 | 0.00 | ✓ |
| it_sos | 0.00 | 0.00 | ✓ |
| it_bol | 616.11 | 0.20 | ✗ |
| de_kst | 0.00 | 0.00 | ✓ |
| de_sol | 0.00 | 0.00 | ✓ |
| de_kis | 0.00 | 0.00 | ✓ |

**Issue:** Outputting the rate (0.20) instead of the tax amount (616.11).

**Likely formula:** The annual Italian tax amounts should be:
- `it_bol = fund_value × rate` where fund_value is the current fund value
- For example: 3080.55 × 0.20 = 616.11

But the fund_value at year-end cannot be derived without fund price history.

## Rules Confirmed

1. **Country** = policyholder's residence at TB_EFFDT (from NRHOLD → NRADDR)
2. **Remittance date** = 10th of the month after TB_EFFDT
3. **Rate extraction** = raw_value / 10000; threshold = raw_value / 100
4. **KST withholding** = rate × taxable_base (25%)
5. **SOL surcharge** = SOL_rate × KST_withholding (5.5%)
6. **VST withholding** = rate × max(0, payout - threshold) (8%)
7. **STP stamp duty** = rate × payout (2.5% for CH)
8. **Date parsing**: 6-digit = YYMMDD, 7-digit = 1YYMMDD (century prefix), 8-digit = YYYYMMDD

## Open Items / Uncertainties

1. **taxable_base for German KST**: The exact formula requires fund price history. The gain formula (payout - premiums) underestimates the base for BL10000086.

2. **t7_tax_annual amounts**: Need to compute actual tax amounts from base × rate, not just output the rate. The base for annual Italian taxes likely involves fund values or policy values.

3. **Rate scaling for Italian taxes**: The BOL rate (2000) might be per mille (2 per thousand = 0.2%) rather than percentage (0.2% also).

4. **No target data available**: The PDF confirms "we do not have all target data" for t7. Evaluation is done by an actuary who manually computes targets (taking up to 2 hours).

## Implementation Status

- ✅ t7_tax_payout function implemented with country detection, rate lookup, and remittance date
- ✅ t7_tax_annual function implemented with year-based aggregation
- ⚠️ Taxable base formula needs refinement (fund-based computation required)
- ⚠️ Annual tax amounts need rate × base computation (need to derive the base)
- ✅ check_t7.py created for scoring
- ✅ Function signatures added to submission.py
- ✅ __all__ updated to include t7_tax_payout and t7_tax_annual
- ✅ COLUMNS dictionary updated for both tasks

## Recommended Next Steps

1. Implement fund-based taxable base computation using NRFPRC (historical fund prices)
2. Derive the annual tax base from fund accounting data (similar to t3_holding)
3. Test against the actuary-provided targets after submission
4. Refine the rules based on scoring feedback
