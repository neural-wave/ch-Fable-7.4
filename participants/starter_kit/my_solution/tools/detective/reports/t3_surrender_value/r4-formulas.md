# t3_surrender_value, r4-formulas

The surrender values with a penalty (outside the waivers), by the product scale (PD_SRPSCL) and the completed policy years. Regression: the surrender value on the policy value, robust; Z3: the factor in millionths that gives every surrender value within a franc of the fit to the cent, rounded half up by Neuron NG and cut off by the old system (t3_surrender_value/r3-search-net/S1). Compare with NRSURR.

| Finding | Group | Rows | Regression | Exact (Z3) |
| --- | --- | --- | --- | --- |
| t3_surrender_value/r4-formulas/F1 | scale 1, 0 completed years, old system | 33 | penalty 5.0001% | penalty 50000 millionths (33 rows within a franc) |
| t3_surrender_value/r4-formulas/F2 | scale 1, 0 completed years, Neuron NG | 21 | penalty 5.0000% | penalty 50000 millionths (21 rows within a franc) |
| t3_surrender_value/r4-formulas/F3 | scale 1, 1 completed years, old system | 29 | penalty 4.0000% | penalty 40000 millionths (29 rows within a franc) |
| t3_surrender_value/r4-formulas/F4 | scale 1, 1 completed years, Neuron NG | 69 | penalty 4.0000% | penalty 40000 millionths (69 rows within a franc) |
| t3_surrender_value/r4-formulas/F5 | scale 1, 2 completed years, old system | 29 | penalty 3.0000% | penalty 30000 millionths (29 rows within a franc) |
| t3_surrender_value/r4-formulas/F6 | scale 1, 2 completed years, Neuron NG | 53 | penalty 3.0000% | penalty 30000 millionths (52 rows within a franc) |
| t3_surrender_value/r4-formulas/F7 | scale 1, 3 completed years, old system | 33 | penalty 2.0000% | penalty 20000 millionths (33 rows within a franc) |
| t3_surrender_value/r4-formulas/F8 | scale 1, 3 completed years, Neuron NG | 65 | penalty 2.0000% | penalty 20000 millionths (65 rows within a franc) |
| t3_surrender_value/r4-formulas/F9 | scale 1, 4 completed years, old system | 32 | penalty 1.0000% | penalty 10000 millionths (32 rows within a franc) |
| t3_surrender_value/r4-formulas/F10 | scale 1, 4 completed years, Neuron NG | 58 | penalty 1.0000% | penalty 10000 millionths (58 rows within a franc) |
| t3_surrender_value/r4-formulas/F11 | scale 1, 5 completed years, Neuron NG | 1 | penalty -1.2241% | none |
| t3_surrender_value/r4-formulas/F12 | scale 1, 12 completed years, Neuron NG | 1 | penalty -0.5784% | none |
| t3_surrender_value/r4-formulas/F13 | scale 1, 13 completed years, Neuron NG | 1 | penalty -0.0745% | none |
| t3_surrender_value/r4-formulas/F14 | scale 1, 20 completed years, Neuron NG | 1 | penalty -0.4836% | none |
| t3_surrender_value/r4-formulas/F15 | scale 2, 0 completed years, old system | 22 | penalty 3.0002% | penalty 30000 millionths (22 rows within a franc) |
| t3_surrender_value/r4-formulas/F16 | scale 2, 0 completed years, Neuron NG | 9 | penalty 2.9999% | penalty 30000 millionths (9 rows within a franc) |
| t3_surrender_value/r4-formulas/F17 | scale 2, 1 completed years, old system | 20 | penalty 2.0000% | penalty 20000 millionths (20 rows within a franc) |
| t3_surrender_value/r4-formulas/F18 | scale 2, 1 completed years, Neuron NG | 35 | penalty 2.0000% | penalty 20000 millionths (35 rows within a franc) |
| t3_surrender_value/r4-formulas/F19 | scale 2, 2 completed years, old system | 15 | penalty 1.0000% | penalty 10000 millionths (15 rows within a franc) |
| t3_surrender_value/r4-formulas/F20 | scale 2, 2 completed years, Neuron NG | 29 | penalty 1.0000% | penalty 10000 millionths (29 rows within a franc) |
| t3_surrender_value/r4-formulas/F21 | scale 2, 9 completed years, Neuron NG | 1 | penalty -1.0825% | none |
| t3_surrender_value/r4-formulas/F22 | scale 2, 14 completed years, Neuron NG | 1 | penalty -0.2133% | none |
| t3_surrender_value/r4-formulas/F23 | scale 2, 16 completed years, Neuron NG | 1 | penalty -0.5994% | none |
| t3_surrender_value/r4-formulas/F24 | scale 3, 0 completed years, old system | 13 | penalty 2.0000% | penalty 20000 millionths (13 rows within a franc) |
| t3_surrender_value/r4-formulas/F25 | scale 3, 0 completed years, Neuron NG | 17 | penalty 2.0000% | penalty 20000 millionths (17 rows within a franc) |
| t3_surrender_value/r4-formulas/F26 | scale 3, 1 completed years, old system | 10 | penalty 1.0000% | penalty 10000 millionths (10 rows within a franc) |
| t3_surrender_value/r4-formulas/F27 | scale 3, 1 completed years, Neuron NG | 20 | penalty 1.0000% | penalty 10000 millionths (20 rows within a franc) |
| t3_surrender_value/r4-formulas/F28 | scale 3, 2 completed years, Neuron NG | 1 | penalty -0.3460% | none |
