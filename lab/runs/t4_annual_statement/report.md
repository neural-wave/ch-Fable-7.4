# t4_annual_statement

Grain: NRRISK {'policy_id': 'RK_POLNR'} (reverse coverage 100.0%; others: )

## premiums

Relation: value / PH_PREMI@RK_BEGDT: 14 clusters, noise 2085, ambiguous 0
| center | rows | roundings that reproduce all rows |
|---|---|---|
| 0 | 6684 | HALF_UP HALF_EVEN HALF_DOWN DOWN UP FLOOR CEILING |
| 1 | 3058 | HALF_UP HALF_EVEN HALF_DOWN DOWN UP FLOOR CEILING |
| 2 | 1105 | HALF_UP HALF_EVEN HALF_DOWN DOWN UP FLOOR CEILING |
| 3 | 1369 | HALF_UP HALF_EVEN HALF_DOWN DOWN UP FLOOR CEILING |
| 4 | 4506 | HALF_UP HALF_EVEN HALF_DOWN DOWN UP FLOOR CEILING |
| 5 | 235 | HALF_UP HALF_EVEN HALF_DOWN DOWN UP FLOOR CEILING |
| 6 | 177 | HALF_UP HALF_EVEN HALF_DOWN DOWN UP FLOOR CEILING |
| 7 | 182 | HALF_UP HALF_EVEN HALF_DOWN DOWN UP FLOOR CEILING |
| 8 | 219 | HALF_UP HALF_EVEN HALF_DOWN DOWN UP FLOOR CEILING |
| 9 | 444 | HALF_UP HALF_EVEN HALF_DOWN DOWN UP FLOOR CEILING |
| 10 | 1671 | HALF_UP HALF_EVEN HALF_DOWN DOWN UP FLOOR CEILING |
| 11 | 5008 | HALF_UP HALF_EVEN HALF_DOWN DOWN UP FLOOR CEILING |
| 12 | 7168 | HALF_UP HALF_EVEN HALF_DOWN DOWN UP FLOOR CEILING |
| 13 | 234 | HALF_UP HALF_EVEN HALF_DOWN DOWN UP FLOOR CEILING |
Other relation: value / PH_PREMI: 14 clusters, 31567 rows exact, noise 2578
Other relation: value / PH_PREMI@RK_ENDDT: 14 clusters, 31556 rows exact, noise 2589
Optimal trees: errors 12384, leaves 8; smallest feature sets: {PH_FREQ, PH_STATE, PH_VRSNR@RK_ENDDT}; {PH_FREQ, PH_STATE, PH_VRSNR}
  PH_FREQ is interchangeable with: PH_FREQ@RK_BEGDT, PH_FREQ@RK_ENDDT
  conflicting vectors (same features, different clusters): 38
  conflicting vector (PH_FREQ = M, PH_STATE = 10, PH_VRSNR@RK_ENDDT = 1): clusters 12 x 5360, 11 x 3711, 10 x 1217, 9 x 308, 13 x 179, 8 x 119, 2 x 112, 3 x 96, 4 x 95, 7 x 94, 1 x 92, 5 x 79, 6 x 71, 0 x 7; example ['BL10000001', 2007]
  conflicting vector (PH_FREQ = E, PH_STATE = 10, PH_VRSNR@RK_ENDDT = 1): clusters 0 x 4427, 1 x 402; example ['BL10000012', 2006]
  conflicting vector (PH_FREQ = Q, PH_STATE = 10, PH_VRSNR@RK_ENDDT = 1): clusters 4 x 3017, 3 x 759, 2 x 151, 1 x 95, 5 x 35, 0 x 7; example ['BL10000039', 2020]
  conflicting vector (PH_FREQ = M, PH_STATE = 60, PH_VRSNR@RK_ENDDT = 2): clusters 12 x 1196, 11 x 873, 10 x 330, 9 x 95, 6 x 76, 8 x 74, 3 x 71, 4 x 69, 5 x 68, 7 x 64, 0 x 53, 2 x 52, 1 x 48, 13 x 35; example ['BL10000029', 1998]
  conflicting vector (PH_FREQ = E, PH_STATE = 60, PH_VRSNR@RK_ENDDT = 2): clusters 0 x 1298, 1 x 152; example ['BL10000007', 2006]
CART for comparison: 8 leaves on PH_FREQ, PH_STATE, PH_STATE@RK_ENDDT, RK_TARKEY[5]
Best candidate C2.2: 8 constants on PH_FREQ, PH_STATE, PH_VRSNR, ROUND_HALF_UP; total 19676/34145, holdout 3849/6737
Same train rows (the data cannot tell them apart): C2.2/HALF_EVEN, C2.2/DOWN, C2.2/HALF_DOWN, C2.2/UP, C2.2/FLOOR, C2.2/CEILING
  C2.1/PH_VRSNR@RK_BEGDT: 8 constants on PH_FREQ, PH_STATE, PH_VRSNR@RK_BEGDT, ROUND_HALF_UP: total 19665
  C1/PH_STATE: 8 constants on PH_FREQ, PH_STATE, RK_TARKEY[5], ROUND_HALF_UP: total 19634
  C1: 8 constants on PH_FREQ, PH_STATE, PH_STATE@RK_ENDDT, RK_TARKEY[5], ROUND_HALF_UP: total 19634
  C1/PH_STATE@RK_BEGDT: 8 constants on PH_FREQ, PH_STATE, PH_STATE@RK_BEGDT, RK_TARKEY[5], ROUND_HALF_UP: total 19634
  card L1: PH_FREQ = M and PH_STATE = 60 and PH_VRSNR@RK_ENDDT = 3 -> 0 (163 rows, e.g. [['BL10000186', 2025]])
  card L2: PH_FREQ = M and PH_STATE = 60 and PH_VRSNR@RK_ENDDT != 3 -> 12 (3215 rows, e.g. [['BL10000029', 1999]])
  card L3: PH_FREQ = M and PH_STATE != 60 and PH_STATE = 20 -> 0 (522 rows, e.g. [['BL10000220', 2017]])
  card L4: PH_FREQ = M and PH_STATE != 60 and PH_STATE != 20 -> 12 (12485 rows, e.g. [['BL10000001', 2010]])
  card L5: PH_FREQ != M and PH_FREQ = Q and PH_STATE = 20 -> 0 (208 rows, e.g. [['BL10000271', 2010]])
  card L6: PH_FREQ != M and PH_FREQ = Q and PH_STATE != 20 -> 4 (5988 rows, e.g. [['BL10000036', 2001]])
  card L7: PH_FREQ != M and PH_FREQ != Q and PH_FREQ = E -> 0 (6456 rows, e.g. [['BL10000007', 2007]])
  card L8: PH_FREQ != M and PH_FREQ != Q and PH_FREQ != E -> 1 (3023 rows, e.g. [['BL10000005', 2010]])
Residuals: 14469 rows. Fit another cluster (a condition is missing): 12 -> 11 x 4891, 12 -> 10 x 1640, 4 -> 3 x 1146, 1 -> 2 x 630, 0 -> 1 x 591, 12 -> 9 x 430. Noise 2085 (whole-unit deltas 2085, listed in NREXCP 0), ambiguous 0
  ['BL10000001', 2009] noise: target 2231.00, computed 2220.00, delta 11.00
  ['BL10000003', 1999] noise: target 5550.00, computed 5520.00, delta 30.00
  ['BL10000003', 2002] noise: target 5544.00, computed 5520.00, delta 24.00
  ['BL10000010', 2022] noise: target 586.00, computed 780.00, delta -194.00
  ['BL10000022', 1998] noise: target 2035.00, computed 3480.00, delta -1445.00
  ['BL10000022', 2000] noise: target 3524.00, computed 3480.00, delta 44.00
  ['BL10000022', 2002] noise: target 3237.00, computed 3480.00, delta -243.00
  ['BL10000022', 2004] noise: target 3215.00, computed 3480.00, delta -265.00

## entry_charges

No relation with dense clusters: a feature or a different relation is missing.

## admin_fees

Relation: value / previous(admin_fees): 20 clusters, noise 6731, ambiguous 8
| center | rows | roundings that reproduce all rows |
|---|---|---|
| 0 | 11 | HALF_UP HALF_EVEN HALF_DOWN DOWN UP FLOOR CEILING |
| 0.0833 | 53 | HALF_UP HALF_EVEN HALF_DOWN UP CEILING |
| 0.1667 | 54 | HALF_UP HALF_EVEN HALF_DOWN DOWN FLOOR |
| 0.25 | 55 | HALF_UP HALF_EVEN HALF_DOWN DOWN UP FLOOR CEILING |
| 0.3333 | 57 | HALF_UP HALF_EVEN HALF_DOWN UP CEILING |
| 0.4167 | 64 | HALF_UP HALF_EVEN HALF_DOWN DOWN FLOOR |
| 0.5 | 63 | HALF_UP HALF_EVEN HALF_DOWN DOWN UP FLOOR CEILING |
| 0.5833 | 58 | HALF_UP HALF_EVEN HALF_DOWN UP CEILING |
| 0.6667 | 44 | HALF_UP HALF_EVEN HALF_DOWN DOWN FLOOR |
| 0.75 | 65 | HALF_UP HALF_EVEN HALF_DOWN DOWN UP FLOOR CEILING |
| 0.8333 | 62 | HALF_UP HALF_EVEN HALF_DOWN UP CEILING |
| 0.9167 | 53 | HALF_UP HALF_EVEN HALF_DOWN DOWN FLOOR |
| 1 | 24151 | HALF_UP HALF_EVEN HALF_DOWN DOWN UP FLOOR CEILING |
| 1.0714 | 168 | HALF_UP HALF_EVEN HALF_DOWN UP CEILING |
| 1.0909 | 211 | HALF_UP HALF_EVEN HALF_DOWN UP CEILING |
| 1.1333 | 551 | HALF_UP HALF_EVEN HALF_DOWN UP CEILING |
| 1.1765 | 986 | HALF_UP HALF_EVEN HALF_DOWN DOWN FLOOR |
| 1.2 | 271 | HALF_UP HALF_EVEN HALF_DOWN DOWN UP FLOOR CEILING |
| 1.3333 | 421 | HALF_UP HALF_EVEN HALF_DOWN UP CEILING |
| 1.4118 | 8 | HALF_UP HALF_EVEN HALF_DOWN DOWN FLOOR |
Optimal trees: errors 3253, leaves 4; smallest feature sets: {PH_STATE@RK_ENDDT, RK_TARKEY[5], PH_FREQ}; {PH_STATE, RK_TARKEY[5], PH_FREQ}
  PH_FREQ is interchangeable with: PH_FREQ@RK_BEGDT, PH_FREQ@RK_ENDDT
  conflicting vectors (same features, different clusters): 63
  conflicting vector (PH_STATE@RK_ENDDT = 10, RK_TARKEY[5] = 2, PH_FREQ = M): clusters 1 x 4005, 1.1765 x 179, 1.1333 x 153, 1.2 x 24, 1.3333 x 24, 1.0909 x 20; example ['BL10000001', 2013]
  conflicting vector (PH_STATE@RK_ENDDT = 10, RK_TARKEY[5] = 1, PH_FREQ = M): clusters 1 x 3071, 1.1333 x 90, 1.1765 x 90, 1.0714 x 59, 1.2 x 10, 1.3333 x 8, 1.0909 x 8; example ['BL10000022', 2003]
  conflicting vector (PH_STATE@RK_ENDDT = 10, RK_TARKEY[5] = 3, PH_FREQ = M): clusters 1 x 2212, 1.1765 x 196, 1.0909 x 28, 1.3333 x 21, 1.2 x 20; example ['BL10000025', 2023]
  conflicting vector (PH_STATE@RK_ENDDT = 10, RK_TARKEY[5] = 2, PH_FREQ = E): clusters 1 x 1441, 1.3333 x 101, 1.2 x 12, 1.0909 x 12; example ['BL10000012', 2007]
  conflicting vector (PH_STATE@RK_ENDDT = 10, RK_TARKEY[5] = 2, PH_FREQ = Q): clusters 1 x 1234, 1.1765 x 64, 1.1333 x 47, 1.2 x 6, 1.3333 x 3, 1.0909 x 3; example ['BL10000058', 2023]
CART for comparison: 8 leaves on PH_FREQ, PH_PRDCD, PH_STATE, PH_STATE@RK_ENDDT, RK_TARKEY[3], RK_TARKEY[5]
Best candidate C2.2: 4 constants on PH_FREQ, PH_STATE, RK_TARKEY[5], ROUND_HALF_UP; total 24161/34145, holdout 4701/6737
Same train rows (the data cannot tell them apart): C2.2/HALF_EVEN, C2.2/HALF_DOWN, C2.2/UP, C2.2/CEILING, C2.1, C2.1/HALF_EVEN
  C2.2/DOWN: 4 constants on PH_FREQ, PH_STATE, RK_TARKEY[5], ROUND_DOWN: total 24159
  C2.2/FLOOR: 4 constants on PH_FREQ, PH_STATE, RK_TARKEY[5], ROUND_FLOOR: total 24159
  C2.1/PH_STATE@RK_BEGDT: 4 constants on PH_FREQ, PH_STATE@RK_BEGDT, RK_TARKEY[5], ROUND_HALF_UP: total 24159
  C2.1/DOWN: 4 constants on PH_FREQ, PH_STATE@RK_ENDDT, RK_TARKEY[5], ROUND_DOWN: total 24159
  card L1: PH_STATE@RK_ENDDT = 70 and RK_TARKEY[5] = 1 -> 1 (308 rows, e.g. [['BL10000003', 1999]])
  card L2: PH_STATE@RK_ENDDT = 70 and RK_TARKEY[5] != 1 and PH_FREQ = J -> 0.5833 (4 rows, e.g. [['BL10000573', 2009]])
  card L3: PH_STATE@RK_ENDDT = 70 and RK_TARKEY[5] != 1 and PH_FREQ != J -> 1 (212 rows, e.g. [['BL10000188', 2011]])
  card L4: PH_STATE@RK_ENDDT != 70 -> 1 (26882 rows, e.g. [['BL10000001', 2009]])
Residuals: 9984 rows. Fit another cluster (a condition is missing): 1 -> 1.1765 x 986, 1 -> 1.1333 x 551, 1 -> 1.3333 x 421, 1 -> 1.2 x 271, 1 -> 1.0909 x 210, 1 -> 1.0714 x 168. Noise 6731 (whole-unit deltas 2983, listed in NREXCP 67), ambiguous 0
  ['BL10000001', 2007] noise: target 60.00, computed None, delta None
  ['BL10000001', 2008] noise: target 90.00, computed 60.00, delta 30.00
  ['BL10000003', 1997] noise: target 50.00, computed None, delta None
  ['BL10000003', 2003] noise: target 66.00, computed 60.00, delta 6.00
  ['BL10000004', 2017] noise: target 76.50, computed None, delta None
  ['BL10000005', 2010] noise: target 37.50, computed None, delta None
  ['BL10000005', 2011] noise: target 90.00, computed 37.50, delta 52.50
  ['BL10000007', 2006] noise: target 15.00, computed None, delta None

## management_fees

No relation with dense clusters: a feature or a different relation is missing.

## risk_charges

No relation with dense clusters: a feature or a different relation is missing.

## total_charges

Exact identity: total_charges = entry_charges + admin_fees + management_fees + risk_charges on 34145 of 34145 rows
No relation with dense clusters: a feature or a different relation is missing.
