# t1_next_due_dates

Grain: NRRISK {'policy_id': 'RK_POLNR'} (reverse coverage 100.0%; others: NREVNT 3.5%, NRBOOK 0.4%)

## due_date

Relation: value - (months) previous(due_date): 3 clusters, noise 1914, ambiguous 0
| center | rows | roundings that reproduce all rows |
|---|---|---|
| 1 | 12042 | HALF_UP |
| 3 | 1032 | HALF_UP |
| 6 | 40 | HALF_UP |
Other relation: value - (days) previous(due_date): 11 clusters, 13380 rows exact, noise 1648
Other relation: value - (days) previous(collection_date): 15 clusters, 13377 rows exact, noise 1651
Optimal trees: errors 0, leaves 3; smallest feature sets: {PH_FREQ}
  PH_FREQ is interchangeable with: PH_FREQ@RK_BEGDT, PH_FREQ@RK_ENDDT
CART for comparison: 3 leaves on PH_FREQ
Best candidate C1: 3 constants on PH_FREQ, ROUND_HALF_UP; total 13114/15028, holdout 2618/3011
Same train rows (the data cannot tell them apart): C2.1, C1/HALF_EVEN, C2.1/HALF_EVEN, C1/DOWN, C2.1/DOWN, C1/HALF_DOWN
  card L1: PH_FREQ = H -> 6 (40 rows, e.g. [['BL10000081', 2]])
  card L2: PH_FREQ != H and PH_FREQ = M -> 1 (12042 rows, e.g. [['BL10000001', 2]])
  card L3: PH_FREQ != H and PH_FREQ != M -> 3 (1032 rows, e.g. [['BL10000039', 2]])
Residuals: 1914 rows. Fit another cluster (a condition is missing): none. Noise 1914 (whole-unit deltas 0, listed in NREXCP 0), ambiguous 0
  ['BL10000001', 1] noise: target 2026-07-26, computed None, delta None
  ['BL10000010', 1] noise: target 2026-07-26, computed None, delta None
  ['BL10000013', 1] noise: target 2026-07-01, computed None, delta None
  ['BL10000018', 1] noise: target 2026-07-31, computed None, delta None
  ['BL10000018', 4] noise: target 2026-10-31, computed 2026-10-30, delta None
  ['BL10000018', 6] noise: target 2026-12-31, computed 2026-12-30, delta None
  ['BL10000018', 9] noise: target 2027-03-31, computed 2027-03-28, delta None
  ['BL10000018', 11] noise: target 2027-05-31, computed 2027-05-30, delta None

## collection_date

Relation: value - (days) due_date: 4 clusters, noise 0, ambiguous 0
| center | rows | roundings that reproduce all rows |
|---|---|---|
| 0 | 10966 | HALF_UP |
| 1 | 1269 | HALF_UP |
| 2 | 2120 | HALF_UP |
| 3 | 673 | HALF_UP |
Other relation: value - (months) due_date: 2 clusters, 10966 rows exact, noise 4062
Optimal trees: errors 357, leaves 7; smallest feature sets: {weekday(due_date), PH_PAYMT, day(due_date)}
  PH_PAYMT is interchangeable with: PH_PAYMT@RK_BEGDT, PH_PAYMT@RK_ENDDT
  conflicting vectors (same features, different clusters): 11
  conflicting vector (weekday(due_date) = 7, PH_PAYMT = LS, day(due_date) = 28): clusters 1 x 125, 2 x 31; example ['BL10000339', 9]
  conflicting vector (weekday(due_date) = 2, PH_PAYMT = LS, day(due_date) = 29): clusters 0 x 15, 1 x 7; example ['BL10000198', 12]
  conflicting vector (weekday(due_date) = 5, PH_PAYMT = LS, day(due_date) = 19): clusters 3 x 8, 0 x 7; example ['BL10000206', 8]
  conflicting vector (weekday(due_date) = 5, PH_PAYMT = LS, day(due_date) = 25): clusters 0 x 8, 3 x 4; example ['BL10001207', 6]
  conflicting vector (weekday(due_date) = 6, PH_PAYMT = LS, day(due_date) = 15): clusters 2 x 5, 3 x 5; example ['BL10001874', 4]
CART for comparison: 7 leaves on PH_PAYMT, day(due_date), month(due_date), weekday(due_date)
Best candidate C2.1: 7 constants on PH_PAYMT, day(due_date), weekday(due_date), ROUND_HALF_UP; total 14671/15028, holdout 2939/3011
Same train rows (the data cannot tell them apart): C2.1/HALF_EVEN, C2.1/DOWN, C2.1/HALF_DOWN, C2.1/UP, C2.1/FLOOR, C2.1/CEILING
  C1: 7 constants on PH_PAYMT, day(due_date), month(due_date), weekday(due_date), ROUND_HALF_UP: total 14503
  C1/HALF_EVEN: 7 constants on PH_PAYMT, day(due_date), month(due_date), weekday(due_date), ROUND_HALF_EVEN: total 14503
  C1/DOWN: 7 constants on PH_PAYMT, day(due_date), month(due_date), weekday(due_date), ROUND_DOWN: total 14503
  C1/HALF_DOWN: 7 constants on PH_PAYMT, day(due_date), month(due_date), weekday(due_date), ROUND_HALF_DOWN: total 14503
  card L1: weekday(due_date) = 5 and PH_PAYMT = LS and day(due_date) = 1 -> 3 (652 rows, e.g. [['BL10000013', 7]])
  card L2: weekday(due_date) = 5 and PH_PAYMT = LS and day(due_date) != 1 -> 0 (751 rows, e.g. [['BL10000001', 8]])
  card L3: weekday(due_date) = 5 and PH_PAYMT != LS -> 0 (274 rows, e.g. [['BL10000022', 7]])
  card L4: weekday(due_date) != 5 and weekday(due_date) = 6 and PH_PAYMT = LS -> 2 (2096 rows, e.g. [['BL10000001', 3]])
  card L5: weekday(due_date) != 5 and weekday(due_date) = 6 and PH_PAYMT != LS -> 0 (399 rows, e.g. [['BL10000022', 2]])
  card L6: weekday(due_date) != 5 and weekday(due_date) != 6 and weekday(due_date) = 7 -> 1 (1551 rows, e.g. [['BL10000001', 1]])
  card L7: weekday(due_date) != 5 and weekday(due_date) != 6 and weekday(due_date) != 7 -> 0 (9305 rows, e.g. [['BL10000001', 2]])
Residuals: 357 rows. Fit another cluster (a condition is missing): 1 -> 0 x 276, 1 -> 2 x 33, 0 -> 1 x 27, 0 -> 3 x 12, 2 -> 3 x 9. Noise 0 (whole-unit deltas 0, listed in NREXCP 0), ambiguous 0
  ['BL10000022', 5] other regime: target 2026-11-01, computed 2026-11-02, delta None
  ['BL10000054', 2] other regime: target 2026-11-01, computed 2026-11-02, delta None
  ['BL10000062', 3] other regime: target 2027-02-28, computed 2027-03-01, delta None
  ['BL10000068', 5] other regime: target 2026-11-29, computed 2026-11-30, delta None
  ['BL10000068', 8] other regime: target 2027-02-28, computed 2027-03-01, delta None
  ['BL10000070', 5] other regime: target 2026-11-01, computed 2026-11-02, delta None
  ['BL10000082', 2] other regime: target 2026-08-16, computed 2026-08-17, delta None
  ['BL10000082', 11] other regime: target 2027-05-16, computed 2027-05-17, delta None
