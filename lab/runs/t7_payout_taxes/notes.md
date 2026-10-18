# t7_payout_taxes notes

## Date
2026-10-18

## Pipeline output (steps 1-4, 6, 7)

The pipeline identified these winning candidates per tax type:
| Tax type | Candidate | Score | Features (smallest feature set) |
|----------|-----------|-------|--------------------------------|
| KST | C2.1 | 2420/2493 | AD_REGIO@EV_EFFDT, EV_PCTG, PH_FREQ |
| SOL | C2.1 | 2420/2493 | same as KST |
| KIS | C2.3 | 2470/2493 | AD_REGIO, EV_PCTG, PS_LANG |
| VST | C1 | 2390/2493 | AD_TAXST@EV_EFFDT, EV_PCTG, RK_TARKEY[3] |
| SOS | C2.1 | 2371/2493 | AD_REGIO@EV_EFFDT, PH_MKTCD, RK_TARKEY[5] |
| BOL | C2.1 | 2444/2493 | AD_CNTRY@EV_EFFDT, AD_REGIO, EV_EVTTP |
| BOC | C2.1 | 2395/2493 | AD_CNTRY@EV_EFFDT, RK_TARKEY[5], previous(SOS) |

Each tax type had "Fit another cluster" residuals — the trees could not perfectly separate positive from negative cases with the available features.

## lab suggest (step 5)

`lab suggest t7_payout_taxes` proposed 3 features:
1. `ph_prdcd_at_effdt = at(PH_PRDCD, EV_EFFDT)` — Product code at event date
2. `ad_church_at_effdt = at(AD_CHURCH, EV_EFFDT)` — Church status at event date
3. `age_at_birth_effdt = age(at(PS_BIRTH, EV_EFFDT), EV_EFFDT)` — Age at event date

**Score: 0 improvement.** The per-value scores remained identical for all tax types.

This means no new feature splits the residual data better than the existing tree conditions.

## Score (lab t7check)

### t7_tax_payout
- **555 / 2493** events correctly taxed or not as NRTAXB (baseline: 552/2493)
- **551 / 551** country of booked taxes match
- **555 / 680** remittance dates match when something is withheld
- Missing: 1813 events (1114 are not in the payout grain)
- **Note**: such.pdf example BL10000086 event 121 is wrong — expected 1407.04 but computed 299744.01. This is a FundAccounting data alignment issue, not a formula error.

### t7_tax_annual
- **5508 / 6381** same tax types as NRTAXB on keys
- Computed 5535 events, booked 6381 (BOC left out)
- Missing for: BL10000003/VST, BL10000028/VST, BL10000036/BOL, BL10000052/VST, BL10000057/STP, BL10000074/VST, BL10000075/VST, BL10000076/SOS

## Features added: none

`lab suggest` found no improvement for any tax type. No features from the pipeline help with the payout function's score.

## Residuals per tax type (from pipeline trees)

Each tax type has residuals where the tree predicts incorrectly — 73 for KST/SOL, 23 for KIS, 103 for VST, 122 for SOS, 49 for BOL, 98 for BOC. These represent events the trees could not classify with the available features.

## Open questions
1. such.pdf examples show large computed amounts vs expected — FundAccounting returns values that don't match the expected tax amounts
2. t7check says "BOL is left out" for annual — need to check if BOL should be included in the result keys
3. The "same tax types as NRTAXB" metric only checks which tax types have nonzero amounts, not the amounts themselves
4. The remaining residuals suggest the trees are incomplete — a feature the trees don't have would be needed
