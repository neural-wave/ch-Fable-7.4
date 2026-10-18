# lab run t7_payout_taxes

profile  t7_payout_taxes    0.6s
frame    t7_payout_taxes    0.1s
cluster  t7_payout_taxes    0.0s
tree     t7_payout_taxes   35.1s
pool     t7_payout_taxes    0.1s
iterate  t7_payout_taxes    0.0s
report   t7_payout_taxes    0.0s
# t7_payout_taxes

Grain: NREVNT {'policy_id': 'EV_POLNR', 'event_nr': 'EV_EVTNR'} (reverse coverage 100.0%; others: NRBOOK 0.1%, NRPREM 1.5%)
Filter: EV_EVTTP in ['400', '410', '500'] (excluded rows {'100': 1977, '800': 676, '990': 89, '300': 275721, '600': 52, '900': 4201, '210': 1864, '110': 162583, '200': 2227, '700': 33, '610': 40, '620': 35}, errors 0)

## KST

Relation: value: 2 clusters, noise 0, ambiguous 0
| center | rows | roundings that reproduce all rows |
|---|---|---|
| no | 2405 | HALF_UP |
| yes | 88 | HALF_UP |
Optimal trees: errors 73, leaves 7; smallest feature sets: {AD_REGIO@EV_EFFDT, EV_PCTG, PH_FREQ}
  PH_FREQ is interchangeable with: PH_FREQ@EV_EFFDT
  conflicting vectors (same features, different clusters): 24
  conflicting vector (AD_REGIO@EV_EFFDT = BY, EV_PCTG = 1.000000, PH_FREQ = M): clusters no x 18, yes x 6; example ['BL10001241', 273]
  conflicting vector (AD_REGIO@EV_EFFDT = BW, EV_PCTG = 1.000000, PH_FREQ = M): clusters no x 12, yes x 4; example ['BL10000992', 76]
  conflicting vector (AD_REGIO@EV_EFFDT = NW, EV_PCTG = 1.000000, PH_FREQ = M): clusters no x 10, yes x 3; example ['BL10002508', 159]
  conflicting vector (AD_REGIO@EV_EFFDT = BY, EV_PCTG = 1.000000, PH_FREQ = E): clusters no x 6, yes x 5; example ['BL10000306', 291]
  conflicting vector (AD_REGIO@EV_EFFDT = HE, EV_PCTG = 1.000000, PH_FREQ = M): clusters no x 8, yes x 2; example ['BL10002604', 258]
CART for comparison: 5 leaves on AD_CNTRY@EV_EFFDT, EV_PCTG, PH_FREQ, RK_TARKEY[3]
Best candidate C2.1: 7 constants on AD_REGIO@EV_EFFDT, EV_PCTG, PH_FREQ, ROUND_HALF_UP; total 2420/2493, holdout 461/474
  C1: 5 constants on AD_CNTRY@EV_EFFDT, EV_PCTG, PH_FREQ, RK_TARKEY[3], ROUND_HALF_UP: total 2418
  C2.1/AD_REGIO: 7 constants on AD_REGIO, EV_PCTG, PH_FREQ, ROUND_HALF_UP: total 2416
  C1/AD_CNTRY: 5 constants on AD_CNTRY, EV_PCTG, PH_FREQ, RK_TARKEY[3], ROUND_HALF_UP: total 2411
  card L1: AD_REGIO@EV_EFFDT = HE and EV_PCTG = 1.000000 and PH_FREQ = M -> no (10 rows, e.g. [['BL10000246', 47]])
  card L2: AD_REGIO@EV_EFFDT = HE and EV_PCTG = 1.000000 and PH_FREQ != M -> yes (14 rows, e.g. [['BL10000162', 102]])
  card L3: AD_REGIO@EV_EFFDT = HE and EV_PCTG != 1.000000 and EV_PCTG = 0.110000 -> yes (2 rows, e.g. [['BL10003287', 176]])
  card L4: AD_REGIO@EV_EFFDT = HE and EV_PCTG != 1.000000 and EV_PCTG != 0.110000 -> no (23 rows, e.g. [['BL10000171', 307]])
  card L5: AD_REGIO@EV_EFFDT != HE and AD_REGIO@EV_EFFDT = BY and PH_FREQ = E -> yes (21 rows, e.g. [['BL10000231', 33]])
  card L6: AD_REGIO@EV_EFFDT != HE and AD_REGIO@EV_EFFDT = BY and PH_FREQ != E -> no (84 rows, e.g. [['BL10000055', 77]])
  card L7: AD_REGIO@EV_EFFDT != HE and AD_REGIO@EV_EFFDT != BY -> no (2339 rows, e.g. [['BL10000003', 201]])
Residuals: 73 rows. Fit another cluster (a condition is missing): no -> yes x 62, yes -> no x 11. Noise 0 (whole-unit deltas 0, listed in NREXCP 0), ambiguous 0
  ['BL10000086', 121] other regime: target yes, computed no, delta None
  ['BL10000228', 175] other regime: target yes, computed no, delta None
  ['BL10000247', 37] other regime: target yes, computed no, delta None
  ['BL10000262', 168] other regime: target yes, computed no, delta None
  ['BL10000301', 76] other regime: target yes, computed no, delta None
  ['BL10000352', 203] other regime: target yes, computed no, delta None
  ['BL10000435', 61] other regime: target no, computed yes, delta None
  ['BL10000435', 72] other regime: target no, computed yes, delta None

## SOL

Relation: value: 2 clusters, noise 0, ambiguous 0
| center | rows | roundings that reproduce all rows |
|---|---|---|
| no | 2405 | HALF_UP |
| yes | 88 | HALF_UP |
Optimal trees: errors 73, leaves 7; smallest feature sets: {AD_REGIO@EV_EFFDT, EV_PCTG, PH_FREQ}
  PH_FREQ is interchangeable with: PH_FREQ@EV_EFFDT
  conflicting vectors (same features, different clusters): 24
  conflicting vector (AD_REGIO@EV_EFFDT = BY, EV_PCTG = 1.000000, PH_FREQ = M): clusters no x 18, yes x 6; example ['BL10001241', 273]
  conflicting vector (AD_REGIO@EV_EFFDT = BW, EV_PCTG = 1.000000, PH_FREQ = M): clusters no x 12, yes x 4; example ['BL10000992', 76]
  conflicting vector (AD_REGIO@EV_EFFDT = NW, EV_PCTG = 1.000000, PH_FREQ = M): clusters no x 10, yes x 3; example ['BL10002508', 159]
  conflicting vector (AD_REGIO@EV_EFFDT = BY, EV_PCTG = 1.000000, PH_FREQ = E): clusters no x 6, yes x 5; example ['BL10000306', 291]
  conflicting vector (AD_REGIO@EV_EFFDT = HE, EV_PCTG = 1.000000, PH_FREQ = M): clusters no x 8, yes x 2; example ['BL10002604', 258]
CART for comparison: 5 leaves on AD_CNTRY@EV_EFFDT, EV_PCTG, PH_FREQ, RK_TARKEY[3]
Best candidate C2.1: 7 constants on AD_REGIO@EV_EFFDT, EV_PCTG, PH_FREQ, ROUND_HALF_UP; total 2420/2493, holdout 461/474
  C1: 5 constants on AD_CNTRY@EV_EFFDT, EV_PCTG, PH_FREQ, RK_TARKEY[3], ROUND_HALF_UP: total 2418
  C2.1/AD_REGIO: 7 constants on AD_REGIO, EV_PCTG, PH_FREQ, ROUND_HALF_UP: total 2416
  C1/AD_CNTRY: 5 constants on AD_CNTRY, EV_PCTG, PH_FREQ, RK_TARKEY[3], ROUND_HALF_UP: total 2411
  card L1: AD_REGIO@EV_EFFDT = HE and EV_PCTG = 1.000000 and PH_FREQ = M -> no (10 rows, e.g. [['BL10000246', 47]])
  card L2: AD_REGIO@EV_EFFDT = HE and EV_PCTG = 1.000000 and PH_FREQ != M -> yes (14 rows, e.g. [['BL10000162', 102]])
  card L3: AD_REGIO@EV_EFFDT = HE and EV_PCTG != 1.000000 and EV_PCTG = 0.110000 -> yes (2 rows, e.g. [['BL10003287', 176]])
  card L4: AD_REGIO@EV_EFFDT = HE and EV_PCTG != 1.000000 and EV_PCTG != 0.110000 -> no (23 rows, e.g. [['BL10000171', 307]])
  card L5: AD_REGIO@EV_EFFDT != HE and AD_REGIO@EV_EFFDT = BY and PH_FREQ = E -> yes (21 rows, e.g. [['BL10000231', 33]])
  card L6: AD_REGIO@EV_EFFDT != HE and AD_REGIO@EV_EFFDT = BY and PH_FREQ != E -> no (84 rows, e.g. [['BL10000055', 77]])
  card L7: AD_REGIO@EV_EFFDT != HE and AD_REGIO@EV_EFFDT != BY -> no (2339 rows, e.g. [['BL10000003', 201]])
Residuals: 73 rows. Fit another cluster (a condition is missing): no -> yes x 62, yes -> no x 11. Noise 0 (whole-unit deltas 0, listed in NREXCP 0), ambiguous 0
  ['BL10000086', 121] other regime: target yes, computed no, delta None
  ['BL10000228', 175] other regime: target yes, computed no, delta None
  ['BL10000247', 37] other regime: target yes, computed no, delta None
  ['BL10000262', 168] other regime: target yes, computed no, delta None
  ['BL10000301', 76] other regime: target yes, computed no, delta None
  ['BL10000352', 203] other regime: target yes, computed no, delta None
  ['BL10000435', 61] other regime: target no, computed yes, delta None
  ['BL10000435', 72] other regime: target no, computed yes, delta None

## KIS

Relation: value: 2 clusters, noise 0, ambiguous 0
| center | rows | roundings that reproduce all rows |
|---|---|---|
| no | 2464 | HALF_UP |
| yes | 29 | HALF_UP |
Optimal trees: errors 23, leaves 7; smallest feature sets: {EV_PCTG, AD_CHURCH, AD_REGIO}; {EV_PCTG, PS_LANG@EV_EFFDT, AD_REGIO}; {EV_PCTG, PS_LANG, AD_REGIO}
  conflicting vectors (same features, different clusters): 12
  conflicting vector (EV_PCTG = 1.000000, AD_CHURCH = J, AD_REGIO = BY): clusters no x 14, yes x 4; example ['BL10000247', 37]
  conflicting vector (EV_PCTG = 1.000000, AD_CHURCH = J, AD_REGIO = BW): clusters no x 10, yes x 5; example ['BL10000228', 175]
  conflicting vector (EV_PCTG = 1.000000, AD_CHURCH = J, AD_REGIO = NW): clusters no x 10, yes x 1; example ['BL10004928', 195]
  conflicting vector (EV_PCTG = 1.000000, AD_CHURCH = J, AD_REGIO = HE): clusters no x 6, yes x 3; example ['BL10001204', 10]
  conflicting vector (EV_PCTG = 1.000000, AD_CHURCH = J, AD_REGIO = BE): clusters no x 5, yes x 1; example ['BL10000626', 234]
CART for comparison: 5 leaves on AD_CHURCH@EV_EFFDT, EV_PCTG, PH_FREQ, PS_CNTRY
Best candidate C2.3: 7 constants on AD_REGIO, EV_PCTG, PS_LANG, ROUND_HALF_UP; total 2470/2493, holdout 470/474
Same train rows (the data cannot tell them apart): C2.2
  C1: 5 constants on AD_CHURCH@EV_EFFDT, EV_PCTG, PH_FREQ, PS_CNTRY, ROUND_HALF_UP: total 2470
  C1/AD_CHURCH: 5 constants on AD_CHURCH, EV_PCTG, PH_FREQ, PS_CNTRY, ROUND_HALF_UP: total 2468
  C2.1: 7 constants on AD_CHURCH, AD_REGIO, EV_PCTG, ROUND_HALF_UP: total 2470
  card L1: AD_CHURCH = J and EV_PCTG = 0.110000 and AD_REGIO = BW -> no (2 rows, e.g. [['BL10002371', 300]])
  card L2: AD_CHURCH = J and EV_PCTG = 0.110000 and AD_REGIO != BW -> yes (3 rows, e.g. [['BL10000301', 76]])
  card L3: AD_CHURCH = J and EV_PCTG != 0.110000 and EV_PCTG = 0.260000 -> yes (2 rows, e.g. [['BL10001721', 123]])
  card L4: AD_CHURCH = J and EV_PCTG != 0.110000 and EV_PCTG != 0.260000 -> no (119 rows, e.g. [['BL10000055', 77]])
  card L5: AD_CHURCH != J and EV_PCTG = 0.300000 and AD_REGIO = PIE -> yes (1 rows, e.g. [['BL10004687', 32]])
  card L6: AD_CHURCH != J and EV_PCTG = 0.300000 and AD_REGIO != PIE -> no (68 rows, e.g. [['BL10000007', 132]])
  card L7: AD_CHURCH != J and EV_PCTG != 0.300000 -> no (2298 rows, e.g. [['BL10000003', 201]])
Residuals: 23 rows. Fit another cluster (a condition is missing): no -> yes x 23. Noise 0 (whole-unit deltas 0, listed in NREXCP 0), ambiguous 0
  ['BL10000228', 175] other regime: target yes, computed no, delta None
  ['BL10000231', 33] other regime: target yes, computed no, delta None
  ['BL10000247', 37] other regime: target yes, computed no, delta None
  ['BL10000262', 168] other regime: target yes, computed no, delta None
  ['BL10000301', 76] other regime: target yes, computed no, delta None
  ['BL10000352', 203] other regime: target yes, computed no, delta None
  ['BL10000435', 141] other regime: target yes, computed no, delta None
  ['BL10000626', 234] other regime: target yes, computed no, delta None

## VST

Relation: value: 2 clusters, noise 0, ambiguous 0
| center | rows | roundings that reproduce all rows |
|---|---|---|
| no | 2236 | HALF_UP |
| yes | 257 | HALF_UP |
Optimal trees: errors 98, leaves 5; smallest feature sets: {AD_TAXST@EV_EFFDT, EV_PCTG, RK_TARKEY[3]}
  conflicting vectors (same features, different clusters): 37
  conflicting vector (AD_TAXST@EV_EFFDT = E, EV_PCTG = 1.000000, RK_TARKEY[3] = W): clusters yes x 63, no x 6; example ['BL10000328', 32]
  conflicting vector (AD_TAXST@EV_EFFDT = E, EV_PCTG = 1.000000, RK_TARKEY[3] = M): clusters yes x 57, no x 4; example ['BL10000554', 7]
  conflicting vector (AD_TAXST@EV_EFFDT = E, EV_PCTG = 1.000000, RK_TARKEY[3] = U): clusters yes x 35, no x 17; example ['BL10000393', 64]
  conflicting vector (AD_TAXST@EV_EFFDT = E, EV_PCTG = 0.120000, RK_TARKEY[3] = M): clusters yes x 4, no x 3; example ['BL10002724', 98]
  conflicting vector (AD_TAXST@EV_EFFDT = E, EV_PCTG = 0.140000, RK_TARKEY[3] = W): clusters yes x 5, no x 2; example ['BL10000685', 109]
CART for comparison: 5 leaves on AD_TAXST@EV_EFFDT, EV_PCTG, RK_TARKEY[3]
Best candidate C1: 5 constants on AD_TAXST@EV_EFFDT, EV_PCTG, RK_TARKEY[3], ROUND_HALF_UP; total 2390/2493, holdout 453/474
  C2.1: 5 constants on AD_TAXST@EV_EFFDT, EV_PCTG, RK_TARKEY[3], ROUND_HALF_UP: total 2395
  C1/AD_TAXST: 5 constants on AD_TAXST, EV_PCTG, RK_TARKEY[3], ROUND_HALF_UP: total 2380
  C2.1/AD_TAXST: 5 constants on AD_TAXST, EV_PCTG, RK_TARKEY[3], ROUND_HALF_UP: total 2387
  card L1: AD_TAXST@EV_EFFDT = E and RK_TARKEY[3] = W and EV_PCTG = 0.100000 -> no (4 rows, e.g. [['BL10000368', 214]])
  card L2: AD_TAXST@EV_EFFDT = E and RK_TARKEY[3] = W and EV_PCTG != 0.100000 -> yes (152 rows, e.g. [['BL10000028', 369]])
  card L3: AD_TAXST@EV_EFFDT = E and RK_TARKEY[3] != W and EV_PCTG = 1.000000 -> yes (113 rows, e.g. [['BL10000003', 201]])
  card L4: AD_TAXST@EV_EFFDT = E and RK_TARKEY[3] != W and EV_PCTG != 1.000000 -> no (117 rows, e.g. [['BL10000058', 95]])
  card L5: AD_TAXST@EV_EFFDT != E -> no (2107 rows, e.g. [['BL10000004', 31]])
Residuals: 103 rows. Fit another cluster (a condition is missing): yes -> no x 86, no -> yes x 17. Noise 0 (whole-unit deltas 0, listed in NREXCP 0), ambiguous 0
  ['BL10000058', 95] other regime: target no, computed yes, delta None
  ['BL10000075', 62] other regime: target yes, computed no, delta None
  ['BL10000174', 127] other regime: target no, computed yes, delta None
  ['BL10000267', 99] other regime: target no, computed yes, delta None
  ['BL10000328', 32] other regime: target no, computed yes, delta None
  ['BL10000368', 214] other regime: target no, computed yes, delta None
  ['BL10000393', 64] other regime: target no, computed yes, delta None
  ['BL10000419', 84] other regime: target no, computed yes, delta None

## SOS

Relation: value: 2 clusters, noise 0, ambiguous 0
| center | rows | roundings that reproduce all rows |
|---|---|---|
| no | 2340 | HALF_UP |
| yes | 153 | HALF_UP |
Optimal trees: errors 122, leaves 7; smallest feature sets: {RK_TARKEY[5], AD_REGIO@EV_EFFDT, PH_MKTCD}
  PH_MKTCD is interchangeable with: PH_MKTCD@EV_EFFDT
  conflicting vectors (same features, different clusters): 33
  conflicting vector (RK_TARKEY[5] = 2, AD_REGIO@EV_EFFDT = LOM, PH_MKTCD = None): clusters no x 23, yes x 17; example ['BL10000076', 43]
  conflicting vector (RK_TARKEY[5] = 1, AD_REGIO@EV_EFFDT = LOM, PH_MKTCD = None): clusters no x 21, yes x 17; example ['BL10000795', 225]
  conflicting vector (RK_TARKEY[5] = 1, AD_REGIO@EV_EFFDT = LOM, PH_MKTCD = BANK21): clusters yes x 19, no x 3; example ['BL10001536', 536]
  conflicting vector (RK_TARKEY[5] = 2, AD_REGIO@EV_EFFDT = LOM, PH_MKTCD = BANK21): clusters no x 11, yes x 8; example ['BL10000125', 171]
  conflicting vector (RK_TARKEY[5] = 2, AD_REGIO@EV_EFFDT = LOM, PH_MKTCD = WEB14): clusters no x 12, yes x 5; example ['BL10001720', 525]
CART for comparison: 5 leaves on AD_CNTRY@EV_EFFDT, EV_PCTG, PH_PRDCD, RK_TARKEY[3]
Best candidate C2.1: 7 constants on AD_REGIO@EV_EFFDT, PH_MKTCD, RK_TARKEY[5], ROUND_HALF_UP; total 2371/2493, holdout 452/474
  C2.1/AD_REGIO: 7 constants on AD_REGIO, PH_MKTCD, RK_TARKEY[5], ROUND_HALF_UP: total 2366
  C1: 5 constants on AD_CNTRY@EV_EFFDT, EV_PCTG, PH_PRDCD, RK_TARKEY[3], ROUND_HALF_UP: total 2366
  C1/AD_CNTRY: 5 constants on AD_CNTRY, EV_PCTG, PH_PRDCD, RK_TARKEY[3], ROUND_HALF_UP: total 2353
  card L1: PH_MKTCD = TV2017 and AD_REGIO@EV_EFFDT = LAZ and RK_TARKEY[5] = 1 -> yes (6 rows, e.g. [['BL10000862', 157]])
  card L2: PH_MKTCD = TV2017 and AD_REGIO@EV_EFFDT = LAZ and RK_TARKEY[5] != 1 -> no (2 rows, e.g. [['BL10001679', 177]])
  card L3: PH_MKTCD = TV2017 and AD_REGIO@EV_EFFDT != LAZ and AD_REGIO@EV_EFFDT = PIE -> yes (14 rows, e.g. [['BL10001013', 71]])
  card L4: PH_MKTCD = TV2017 and AD_REGIO@EV_EFFDT != LAZ and AD_REGIO@EV_EFFDT != PIE -> no (387 rows, e.g. [['BL10000004', 31]])
  card L5: PH_MKTCD != TV2017 and RK_TARKEY[5] = 1 and AD_REGIO@EV_EFFDT = LOM -> yes (87 rows, e.g. [['BL10000044', 667]])
  card L6: PH_MKTCD != TV2017 and RK_TARKEY[5] = 1 and AD_REGIO@EV_EFFDT != LOM -> no (582 rows, e.g. [['BL10000003', 201]])
  card L7: PH_MKTCD != TV2017 and RK_TARKEY[5] != 1 -> no (1415 rows, e.g. [['BL10000005', 54]])
Residuals: 122 rows. Fit another cluster (a condition is missing): no -> yes x 84, yes -> no x 38. Noise 0 (whole-unit deltas 0, listed in NREXCP 0), ambiguous 0
  ['BL10000036', 20] other regime: target no, computed yes, delta None
  ['BL10000036', 101] other regime: target no, computed yes, delta None
  ['BL10000036', 258] other regime: target no, computed yes, delta None
  ['BL10000051', 48] other regime: target no, computed yes, delta None
  ['BL10000076', 43] other regime: target yes, computed no, delta None
  ['BL10000093', 158] other regime: target no, computed yes, delta None
  ['BL10000125', 171] other regime: target yes, computed no, delta None
  ['BL10000168', 147] other regime: target yes, computed no, delta None

## BOL

Relation: value: 2 clusters, noise 0, ambiguous 0
| center | rows | roundings that reproduce all rows |
|---|---|---|
| no | 2359 | HALF_UP |
| yes | 134 | HALF_UP |
Optimal trees: errors 49, leaves 4; smallest feature sets: {AD_CNTRY@EV_EFFDT, EV_EVTTP, AD_REGIO}; {AD_CNTRY@EV_EFFDT, EV_PCTG, AD_REGIO}
  conflicting vectors (same features, different clusters): 4
  conflicting vector (AD_CNTRY@EV_EFFDT = IT, EV_EVTTP = 410, AD_REGIO = LOM): clusters yes x 86, no x 33; example ['BL10000051', 48]
  conflicting vector (AD_CNTRY@EV_EFFDT = IT, EV_EVTTP = 410, AD_REGIO = PIE): clusters yes x 26, no x 8; example ['BL10000455', 17]
  conflicting vector (AD_CNTRY@EV_EFFDT = IT, EV_EVTTP = 410, AD_REGIO = LAZ): clusters yes x 10, no x 5; example ['BL10002217', 173]
  conflicting vector (AD_CNTRY@EV_EFFDT = IT, EV_EVTTP = 410, AD_REGIO = TI): clusters yes x 3, no x 2; example ['BL10001378', 57]
CART for comparison: 6 leaves on AD_CNTRY, AD_CNTRY@EV_EFFDT, AD_REGIO@EV_EFFDT, EV_PCTG, PS_CNTRY
Best candidate C2.1: 4 constants on AD_CNTRY@EV_EFFDT, AD_REGIO, EV_EVTTP, ROUND_HALF_UP; total 2444/2493, holdout 466/474
Same train rows (the data cannot tell them apart): C2.2
  C1: 6 constants on AD_CNTRY, AD_CNTRY@EV_EFFDT, AD_REGIO@EV_EFFDT, EV_PCTG, PS_CNTRY, ROUND_HALF_UP: total 2444
  C1/AD_REGIO: 6 constants on AD_CNTRY, AD_CNTRY@EV_EFFDT, AD_REGIO, EV_PCTG, PS_CNTRY, ROUND_HALF_UP: total 2443
  C2.1/AD_CNTRY: 4 constants on AD_CNTRY, AD_REGIO, EV_EVTTP, ROUND_HALF_UP: total 2427
  C2.2/AD_CNTRY: 4 constants on AD_CNTRY, AD_REGIO, EV_PCTG, ROUND_HALF_UP: total 2427
  card L1: AD_CNTRY@EV_EFFDT = IT and EV_EVTTP = 400 -> no (210 rows, e.g. [['BL10000036', 20]])
  card L2: AD_CNTRY@EV_EFFDT = IT and EV_EVTTP != 400 and AD_REGIO = GR -> no (1 rows, e.g. [['BL10001626', 53]])
  card L3: AD_CNTRY@EV_EFFDT = IT and EV_EVTTP != 400 and AD_REGIO != GR -> yes (181 rows, e.g. [['BL10000036', 258]])
  card L4: AD_CNTRY@EV_EFFDT != IT -> no (2101 rows, e.g. [['BL10000003', 201]])
Residuals: 49 rows. Fit another cluster (a condition is missing): yes -> no x 48, no -> yes x 1. Noise 0 (whole-unit deltas 0, listed in NREXCP 0), ambiguous 0
  ['BL10000051', 48] other regime: target no, computed yes, delta None
  ['BL10000076', 43] other regime: target no, computed yes, delta None
  ['BL10000093', 199] other regime: target no, computed yes, delta None
  ['BL10000256', 9] other regime: target no, computed yes, delta None
  ['BL10000455', 17] other regime: target no, computed yes, delta None
  ['BL10000487', 96] other regime: target yes, computed no, delta None
  ['BL10000506', 190] other regime: target no, computed yes, delta None
  ['BL10000795', 225] other regime: target no, computed yes, delta None

## BOC

Relation: value: 2 clusters, noise 0, ambiguous 0
| center | rows | roundings that reproduce all rows |
|---|---|---|
| no | 2198 | HALF_UP |
| yes | 295 | HALF_UP |
Optimal trees: errors 98, leaves 5; smallest feature sets: {AD_CNTRY@EV_EFFDT, previous(SOS), RK_TARKEY[5]}
  conflicting vectors (same features, different clusters): 17
  conflicting vector (AD_CNTRY@EV_EFFDT = CH, previous(SOS) = None, RK_TARKEY[5] = 2): clusters no x 510, yes x 3; example ['BL10000550', 229]
  conflicting vector (AD_CNTRY@EV_EFFDT = CH, previous(SOS) = None, RK_TARKEY[5] = 1): clusters no x 398, yes x 1; example ['BL10000316', 517]
  conflicting vector (AD_CNTRY@EV_EFFDT = CH, previous(SOS) = None, RK_TARKEY[5] = 3): clusters no x 271, yes x 2; example ['BL10000389', 135]
  conflicting vector (AD_CNTRY@EV_EFFDT = CH, previous(SOS) = None, RK_TARKEY[5] = 4): clusters no x 137, yes x 1; example ['BL10003014', 31]
  conflicting vector (AD_CNTRY@EV_EFFDT = CH, previous(SOS) = no, RK_TARKEY[5] = 1): clusters no x 132, yes x 1; example ['BL10001600', 497]
CART for comparison: 8 leaves on AD_CNTRY@EV_EFFDT, AD_REGIO@EV_EFFDT, AD_VRSNR@EV_EFFDT, EC_RATE@EV_EFFDT, RK_TARKEY[5], previous(SOS)
Best candidate C2.1: 5 constants on AD_CNTRY@EV_EFFDT, RK_TARKEY[5], previous(SOS), ROUND_HALF_UP; total 2395/2493, holdout 457/474
  C1/EC_RATE: 8 constants on AD_CNTRY@EV_EFFDT, AD_REGIO@EV_EFFDT, AD_VRSNR@EV_EFFDT, EC_RATE, RK_TARKEY[5], previous(SOS), ROUND_HALF_UP: total 2373
  C1/AD_REGIO: 8 constants on AD_CNTRY@EV_EFFDT, AD_REGIO, AD_VRSNR@EV_EFFDT, EC_RATE@EV_EFFDT, RK_TARKEY[5], previous(SOS), ROUND_HALF_UP: total 2391
  C1/AD_VRSNR: 8 constants on AD_CNTRY@EV_EFFDT, AD_REGIO@EV_EFFDT, AD_VRSNR, EC_RATE@EV_EFFDT, RK_TARKEY[5], previous(SOS), ROUND_HALF_UP: total 2391
  C1: 8 constants on AD_CNTRY@EV_EFFDT, AD_REGIO@EV_EFFDT, AD_VRSNR@EV_EFFDT, EC_RATE@EV_EFFDT, RK_TARKEY[5], previous(SOS), ROUND_HALF_UP: total 2391
  card L1: AD_CNTRY@EV_EFFDT = IT and previous(SOS) = None and RK_TARKEY[5] = 1 -> no (90 rows, e.g. [['BL10000036', 20]])
  card L2: AD_CNTRY@EV_EFFDT = IT and previous(SOS) = None and RK_TARKEY[5] != 1 -> yes (228 rows, e.g. [['BL10000102', 25]])
  card L3: AD_CNTRY@EV_EFFDT = IT and previous(SOS) != None -> yes (74 rows, e.g. [['BL10000036', 258]])
  card L4: AD_CNTRY@EV_EFFDT != IT and previous(SOS) = yes -> yes (1 rows, e.g. [['BL10003517', 218]])
  card L5: AD_CNTRY@EV_EFFDT != IT and previous(SOS) != yes -> no (2100 rows, e.g. [['BL10000003', 201]])
Residuals: 98 rows. Fit another cluster (a condition is missing): yes -> no x 53, no -> yes x 45. Noise 0 (whole-unit deltas 0, listed in NREXCP 0), ambiguous 0
  ['BL10000036', 101] other regime: target no, computed yes, delta None
  ['BL10000044', 667] other regime: target yes, computed no, delta None
  ['BL10000076', 43] other regime: target no, computed yes, delta None
  ['BL10000093', 199] other regime: target no, computed yes, delta None
  ['BL10000168', 103] other regime: target no, computed yes, delta None
  ['BL10000256', 9] other regime: target no, computed yes, delta None
  ['BL10000305', 179] other regime: target yes, computed no, delta None
  ['BL10000316', 517] other regime: target yes, computed no, delta None


# lab suggest t7_payout_taxes

model qwen3.6:35b-a3b-coding: 3 valid proposals, 0 rejected
  + ph_prdcd_at_effdt = at(PH_PRDCD, EV_EFFDT)  (Product code at event date often dictates payout eligibility and tax rules, resolving identical feature conflicts in KST/SOL.)
  + ad_church_at_effdt = at(AD_CHURCH, EV_EFFDT)  (Church tax status is a key differentiator for German policies, clarifying ambiguous regional and frequency combinations.)
  + age_at_birth_effdt = age(at(PS_BIRTH, EV_EFFDT), EV_EFFDT)  (Age at event date is a fundamental underwriting factor frequently missing from static feature sets, helping separate age-dependent payout clusters.)
best before: C2.1 2420 rows exact; after: C2.1 2420 rows exact; per value: KST 2420 -> 2420, SOL 2420 -> 2420, KIS 2470 -> 2470, VST 2390 -> 2390, SOS 2371 -> 2371, BOL 2444 -> 2444, BOC 2395 -> 2395

# lab t7check

# t7check (no targets: examples of such.pdf and consistency with NRTAXB)

## t7_tax_payout

  rows the scoring drops (wrong format): 0 of 1794
Payouts (NRTAXB, 2493 payout events): computed 680, missing 1813, not payouts 1114
  taxed or not as NRTAXB: 552 / 2493
  country of the booked taxes: 548 / 548
  remittance date exactly when something is withheld: 552 / 680
  ('BL10000004', 31) missing, NRTAXB books nothing
  ('BL10000005', 54) missing, NRTAXB books nothing
  ('BL10000006', 13) missing, NRTAXB books nothing
  ('BL10000007', 132) missing, NRTAXB books nothing
  ('BL10000007', 202) missing, NRTAXB books nothing
  ('BL10000016', 108) missing, NRTAXB books nothing
  ('BL10000021', 274) missing, NRTAXB books nothing
  ('BL10000029', 13) missing, NRTAXB books nothing
  examples of such.pdf (2 rows, a sanity check only):
  example ('BL10000086', 121): WRONG; expected ('DE', '5628.16', '1407.04', '77.38', '0.00', '2006-08-10'), computed ('DE', '11989.76', '299744.01', '1648592.05', '0.00', '2006-08-10')

## t7_tax_annual

  rows the scoring drops (wrong format): 0 of 5535
Annual (policy, year): same tax types as NRTAXB on 5508 / 6381 keys (computed 5535, booked 6381; BOC is left out)
  ('BL10000003', 2005) computed [], NRTAXB books ['VST']
  ('BL10000028', 2024) computed [], NRTAXB books ['VST']
  ('BL10000036', 2016) computed [], NRTAXB books ['BOL']
  ('BL10000052', 2003) computed [], NRTAXB books ['VST']
  ('BL10000057', 2021) computed [], NRTAXB books ['STP']
  ('BL10000074', 2020) computed [], NRTAXB books ['VST']
  ('BL10000075', 2021) computed [], NRTAXB books ['VST']
  ('BL10000076', 2010) computed [], NRTAXB books ['SOS']
  examples of such.pdf (2 rows, a sanity check only):
  example ('BL10000044', 2019): WRONG; expected ('0.00', '0.00', '0.00', '616.11', '0.00', '0.00', '0.00'), computed ('0.00', '0.00', '0.00', '33448.48', '0.00', '0.00', '0.00')

