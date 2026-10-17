# t3_surrender_value, r3-search-net

After r3: 5 surrender values of Neuron NG one cent too low, all with a penalty of an exact half cent (132330 x 5 % = 6616.5, Neuron 6616); the surrender value 132330 x 95 % = 125713.5 rounded half up is right. The old system rounded the penalty up, the same as rounding the rest down. BL10001005 has a value of -3 cents and a surrender value of 0. Holes: the surrender value as the rounded rest, and its floor. The rows off by whole francs are left (11 of 21 under r3/T1 are listed in NREXCP: hand edits).

| Finding | Holes | Right (80 %) | Right (held out) |
| --- | --- | --- | --- |
| t3_surrender_value/r3-search-net/S1 | {'penalty': 'net', 'floor': 'zero'} | 4996 / 5009 | 1141 / 1144 |
| t3_surrender_value/r3-search-net/S2 | {'penalty': ('up', 'net'), 'floor': 'zero'} | 4996 / 5009 | 1141 / 1144 |
| t3_surrender_value/r3-search-net/S3 | {'penalty': 'net', 'floor': 'none'} | 4995 / 5009 | 1141 / 1144 |
| t3_surrender_value/r3-search-net/S4 | {'penalty': ('up', 'net'), 'floor': 'none'} | 4995 / 5009 | 1141 / 1144 |
| t3_surrender_value/r3-search-net/S5 | {'penalty': ('up', 'value'), 'floor': 'zero'} | 4991 / 5009 | 1141 / 1144 |
| t3_surrender_value/r3-search-net/S6 | {'penalty': ('net', 'value'), 'floor': 'zero'} | 4991 / 5009 | 1141 / 1144 |
| t3_surrender_value/r3-search-net/S7 | {'penalty': ('up', 'value'), 'floor': 'none'} | 4990 / 5009 | 1141 / 1144 |
| t3_surrender_value/r3-search-net/S8 | {'penalty': ('net', 'value'), 'floor': 'none'} | 4990 / 5009 | 1141 / 1144 |
