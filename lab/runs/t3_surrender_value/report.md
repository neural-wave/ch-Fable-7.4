# t3_surrender_value

Grain: NRRISK {'policy_id': 'RK_POLNR'} (reverse coverage 100.0%; others: NRPREM 2.6%, NRBOOK 2.6%)

## surrender_value

Relation: value / policy_value: 3 clusters, noise 281, ambiguous 1518
| center | rows | roundings that reproduce all rows |
|---|---|---|
| 0.98 | 183 |  |
| 0.99 | 164 |  |
| 1 | 4007 | HALF_UP HALF_EVEN HALF_DOWN DOWN UP FLOOR CEILING |
Other relation: value - policy_value: 1 clusters, 5525 rows exact, noise 628
Optimal trees: errors 324, leaves 6; smallest feature sets: {RK_TARKEY[5], weekday(valuation_date), PH_STATE@RK_ENDDT}; {RK_TARKEY[5], weekday(valuation_date), PH_STATE}
  conflicting vectors (same features, different clusters): 9
  conflicting vector (RK_TARKEY[5] = 4, weekday(valuation_date) = 3, PH_STATE@RK_ENDDT = 10): clusters 1 x 318, 0.98 x 112, 0.99 x 103; example ['BL10000010', '2025-12-31']
  conflicting vector (RK_TARKEY[5] = 1, weekday(valuation_date) = 7, PH_STATE@RK_ENDDT = 10): clusters 1 x 214, 0.98 x 23, 0.99 x 19; example ['BL10000177', '2006-12-31']
  conflicting vector (RK_TARKEY[5] = 1, weekday(valuation_date) = 7, PH_STATE@RK_ENDDT = 60): clusters 1 x 138, 0.99 x 11, 0.98 x 9; example ['BL10000327', '2006-12-31']
  conflicting vector (RK_TARKEY[5] = 2, weekday(valuation_date) = 7, PH_STATE@RK_ENDDT = 10): clusters 0.98 x 22, 0.99 x 12, 1 x 9; example ['BL10000100', '2006-12-31']
  conflicting vector (RK_TARKEY[5] = 2, weekday(valuation_date) = 7, PH_STATE@RK_ENDDT = 60): clusters 0.99 x 13, 0.98 x 11, 1 x 4; example ['BL10000007', '2006-12-31']
CART for comparison: 6 leaves on EC_RATE@RK_BEGDT, RK_TARKEY[5], weekday(valuation_date)
Best candidate C2.2/DOWN: 6 constants on PH_STATE, RK_TARKEY[5], weekday(valuation_date), ROUND_DOWN; total 5548/6153, holdout 1118/1241
Same train rows (the data cannot tell them apart): C2.2/FLOOR, C2.1/DOWN, C2.1/FLOOR
  C1/DOWN: 6 constants on EC_RATE@RK_BEGDT, RK_TARKEY[5], weekday(valuation_date), ROUND_DOWN: total 5545
  C1/FLOOR: 6 constants on EC_RATE@RK_BEGDT, RK_TARKEY[5], weekday(valuation_date), ROUND_FLOOR: total 5545
  C2.2/HALF_EVEN: 6 constants on PH_STATE, RK_TARKEY[5], weekday(valuation_date), ROUND_HALF_EVEN: total 5528
  C2.2/HALF_DOWN: 6 constants on PH_STATE, RK_TARKEY[5], weekday(valuation_date), ROUND_HALF_DOWN: total 5528
  card L1: RK_TARKEY[5] = 2 and weekday(valuation_date) = 7 and PH_STATE@RK_ENDDT = 10 -> 0.98 (43 rows, e.g. [['BL10000012', '2006-12-31']])
  card L2: RK_TARKEY[5] = 2 and weekday(valuation_date) = 7 and PH_STATE@RK_ENDDT != 10 -> 0.99 (28 rows, e.g. [['BL10000168', '2006-12-31']])
  card L3: RK_TARKEY[5] = 2 and weekday(valuation_date) != 7 -> 1 (1290 rows, e.g. [['BL10000001', '2020-04-30']])
  card L4: RK_TARKEY[5] != 2 and RK_TARKEY[5] = 3 -> 1 (1273 rows, e.g. [['BL10000013', '2020-04-30']])
  card L5: RK_TARKEY[5] != 2 and RK_TARKEY[5] != 3 and PH_STATE@RK_ENDDT = 30 -> 0.99 (1 rows, e.g. [['BL10001863', '2025-12-31']])
  card L6: RK_TARKEY[5] != 2 and RK_TARKEY[5] != 3 and PH_STATE@RK_ENDDT != 30 -> 1 (1719 rows, e.g. [['BL10000022', '2006-12-31']])
Residuals: 605 rows. Fit another cluster (a condition is missing): 1 -> 0.98 x 150, 1 -> 0.99 x 138, 0.98 -> 0.99 x 12, 0.99 -> 0.98 x 11, 0.98 -> 1 x 9, 0.99 -> 1 x 4. Noise 281 (whole-unit deltas 18, listed in NREXCP 12), ambiguous 0
  ['BL10000055', '2006-12-31'] noise: target 13475.65, computed 13896.76, delta -421.11
  ['BL10000095', '2006-12-31'] noise: target 14223.70, computed 14370.33, delta -146.63
  ['BL10000141', '2006-12-31'] noise: target 7076.03, computed 7297.16, delta -221.13
  ['BL10000155', '2025-12-31'] noise: target 19663.84, computed 20272.00, delta -608.16
  ['BL10000161', '2025-12-31'] noise: target 3272.42, computed 3373.63, delta -101.21
  ['BL10000191', '2006-12-31'] noise: target 6595.29, computed 6663.28, delta -67.99
  ['BL10000202', '2025-12-31'] noise: target 4167.57, computed 4296.46, delta -128.89
  ['BL10000207', '2006-12-31'] noise: target 5421.51, computed 5534.46, delta -112.95
