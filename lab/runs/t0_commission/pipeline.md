# lab run t0_commission

profile  t0_commission    0.6s
frame    t0_commission    0.5s
cluster  t0_commission    2.1s
tree     t0_commission   10.3s
pool     t0_commission    2.9s
iterate  t0_commission    0.1s
report   t0_commission    0.0s
# t0_commission

Grain: NRPREM {'policy_id': 'PR_POLNR', 'due_nr': 'PR_DUENR'} (reverse coverage 94.8%; others: NREVNT 34.9%, NRBOOK 4.5%)
Filter: PR_STATE in ['P'] (excluded rows {'R': 5816, 'W': 3056, 'O': 3614}, errors 0)

## amount

Relation: value / PR_AMTRC: 6 clusters, noise 10, ambiguous 0
| center | rows | roundings that reproduce all rows |
|---|---|---|
| 0.005 | 137 | HALF_UP UP CEILING |
| 0.01 | 253 | HALF_UP HALF_EVEN HALF_DOWN DOWN UP FLOOR CEILING |
| 0.015 | 185 | HALF_UP HALF_EVEN HALF_DOWN DOWN UP FLOOR CEILING |
| 0.02 | 53683 | HALF_UP HALF_EVEN HALF_DOWN DOWN UP FLOOR CEILING |
| 0.03 | 102865 | HALF_UP HALF_EVEN HALF_DOWN DOWN UP FLOOR CEILING |
| 0.04 | 68725 | HALF_UP HALF_EVEN HALF_DOWN DOWN UP FLOOR CEILING |
Other relation: value / PR_AMTDU: 18 clusters, 223728 rows exact, noise 2130
Other relation: value / PH_PREMI@PR_DUEDT: 18 clusters, 223728 rows exact, noise 2130
Optimal trees: errors 0, leaves 6; smallest feature sets: {EC_RATE@PR_RCVDT, PH_PRDCD}; {EC_RATE@PR_RCVDT, PH_FREQ}; {EC_RATE@PR_RCVDT, RK_TARKEY[6]}; {PH_PRDCD, BR_TIER@PR_RCVDT}; {PH_FREQ, BR_TIER@PR_RCVDT}; {RK_TARKEY[6], BR_TIER@PR_RCVDT}
  EC_RATE@PR_RCVDT is interchangeable with: BR_TIER@PR_RCVDT
  PH_PRDCD is interchangeable with: PD_INIMON, PD_INIMON@PR_DUEDT, PD_INIMON@PR_RCVDT, PD_SRPSCL, PD_SRPSCL@PR_DUEDT, PD_SRPSCL@PR_RCVDT, PD_TARFAM, PD_TARFAM@PR_DUEDT
CART for comparison: 6 leaves on BR_TIER@PR_DUEDT, BR_TIER@PR_RCVDT, PH_FREQ, RK_TARKEY[6]
Best candidate C3.1.1: NRCOMR.CR_RATE[CR_TIER = BR_TIER@PR_RCVDT, CR_PAYTP = RK_TARKEY[6]], ROUND_HALF_UP; total 225848/225858, holdout 44051/44052
Same train rows (the data cannot tell them apart): C3.1.1/UP, C3.1.1/CEILING, C2.1, C2.2, C2.3, C2.4
  C3.1.1/BR_TIER@PR_DUEDT: NRCOMR.CR_RATE[CR_TIER = BR_TIER@PR_DUEDT, CR_PAYTP = RK_TARKEY[6]], ROUND_HALF_UP: total 225846
  C2.1/EC_RATE@PR_DUEDT: 6 constants on EC_RATE@PR_DUEDT, PH_PRDCD, ROUND_HALF_UP: total 225846
  C2.2/EC_RATE@PR_DUEDT: 6 constants on EC_RATE@PR_DUEDT, PH_FREQ, ROUND_HALF_UP: total 225846
  C2.3/EC_RATE@PR_DUEDT: 6 constants on EC_RATE@PR_DUEDT, RK_TARKEY[6], ROUND_HALF_UP: total 225846
  card L1: EC_RATE@PR_RCVDT = 0.020000 and PH_PRDCD = FLSP -> 0.005 (137 rows, e.g. [['BL10000034', 1]])
  card L2: EC_RATE@PR_RCVDT = 0.020000 and PH_PRDCD != FLSP -> 0.02 (53683 rows, e.g. [['BL10000001', 2]])
  card L3: EC_RATE@PR_RCVDT != 0.020000 and EC_RATE@PR_RCVDT = 0.050000 and PH_PRDCD = FLSP -> 0.015 (185 rows, e.g. [['BL10000007', 1]])
  card L4: EC_RATE@PR_RCVDT != 0.020000 and EC_RATE@PR_RCVDT = 0.050000 and PH_PRDCD != FLSP -> 0.04 (68725 rows, e.g. [['BL10000003', 1]])
  card L5: EC_RATE@PR_RCVDT != 0.020000 and EC_RATE@PR_RCVDT != 0.050000 and PH_PRDCD = FLSP -> 0.01 (253 rows, e.g. [['BL10000012', 1]])
  card L6: EC_RATE@PR_RCVDT != 0.020000 and EC_RATE@PR_RCVDT != 0.050000 and PH_PRDCD != FLSP -> 0.03 (102865 rows, e.g. [['BL10000013', 1]])
Residuals: 10 rows. Fit another cluster (a condition is missing): none. Noise 10 (whole-unit deltas 10, listed in NREXCP 6), ambiguous 0
  ['BL10000237', 41] noise: target 49.40, computed 5.40, delta 44.00
  ['BL10001299', 103] noise: target 79.70, computed 5.70, delta 74.00
  ['BL10001328', 1] noise: target 936.00, computed 859.00, delta 77.00
  ['BL10001567', 6] noise: target 28.50, computed 1.50, delta 27.00
  ['BL10002438', 11] noise: target 310.40, computed 242.40, delta 68.00
  ['BL10002462', 5] noise: target 101.80, computed 85.80, delta 16.00
  ['BL10003175', 247] noise: target 20.70, computed 11.70, delta 9.00
  ['BL10004049', 6] noise: target 75.15, computed 39.15, delta 36.00


# lab score t0_commission

# score of t0_commission (code:dc98a153707d)

Exact rows: 225848 / 225858 (holdout 44051 / 44052); keys computed for target policies but not in the target: 0; 1.7 s

## amount

ok 225848, missing 0, noise 10 (policies listed in NREXCP: 6)
| label | rows | examples |
|---|---|---|
| noise | 10 | [('BL10000237', 41), ('BL10001299', 103), ('BL10001328', 1)] |
Trees: one cluster only, no conditions needed

