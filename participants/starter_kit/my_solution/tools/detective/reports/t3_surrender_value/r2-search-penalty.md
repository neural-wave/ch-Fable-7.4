# t3_surrender_value, r2-search-penalty

After r1 (r1-search/S1): the policy value is right in every row; 230 surrender values are one cent too high, 225 of them on 2006-12-31 (r1/C1: 31.4 % wrong before 2020, 0.5 % after), when the old system made them. Hole: how the penalty is rounded, per system. The 7 missing rows are policies without units on the date: worth 0.

| Finding | Holes | Right (80 %) | Right (held out) |
| --- | --- | --- | --- |
| t3_surrender_value/r2-search-penalty/S1 | {'penalty': ('up', 'value')} | 4990 / 5009 | 1141 / 1144 |
| t3_surrender_value/r2-search-penalty/S2 | {'penalty': ('up', 'half_up')} | 4990 / 5009 | 1141 / 1144 |
| t3_surrender_value/r2-search-penalty/S3 | {'penalty': 'half_up'} | 4896 / 5009 | 1119 / 1144 |
| t3_surrender_value/r2-search-penalty/S4 | {'penalty': ('half_up', 'value')} | 4896 / 5009 | 1119 / 1144 |
| t3_surrender_value/r2-search-penalty/S5 | {'penalty': ('up', 'down')} | 4853 / 5009 | 1105 / 1144 |
| t3_surrender_value/r2-search-penalty/S6 | {'penalty': 'up'} | 4846 / 5009 | 1101 / 1144 |
| t3_surrender_value/r2-search-penalty/S7 | {'penalty': 'value'} | 4803 / 5009 | 1098 / 1144 |
| t3_surrender_value/r2-search-penalty/S8 | {'penalty': ('value', 'half_up')} | 4803 / 5009 | 1098 / 1144 |
| t3_surrender_value/r2-search-penalty/S9 | {'penalty': ('down', 'value')} | 4803 / 5009 | 1098 / 1144 |
| t3_surrender_value/r2-search-penalty/S10 | {'penalty': ('down', 'half_up')} | 4803 / 5009 | 1098 / 1144 |
| t3_surrender_value/r2-search-penalty/S11 | {'penalty': ('half_up', 'down')} | 4759 / 5009 | 1083 / 1144 |
| t3_surrender_value/r2-search-penalty/S12 | {'penalty': ('half_up', 'up')} | 4752 / 5009 | 1079 / 1144 |
| t3_surrender_value/r2-search-penalty/S13 | {'penalty': 'down'} | 4666 / 5009 | 1062 / 1144 |
| t3_surrender_value/r2-search-penalty/S14 | {'penalty': ('value', 'down')} | 4666 / 5009 | 1062 / 1144 |
| t3_surrender_value/r2-search-penalty/S15 | {'penalty': ('value', 'up')} | 4659 / 5009 | 1058 / 1144 |
| t3_surrender_value/r2-search-penalty/S16 | {'penalty': ('down', 'up')} | 4659 / 5009 | 1058 / 1144 |
