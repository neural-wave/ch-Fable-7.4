# t3_booking_adm_amc, r1-search

Round 1 of the charge run (llm/009-t3-charges-story.md) on the holdings Neuron had before each run (detective.replay): 3330756 of 3661465 admin fee and management charge bookings right, the price always. Holes: the rounding, the precision of the value of a fund and pot, the date of the tariff.

| Finding | Holes | Right (80 %) | Right (held out) |
| --- | --- | --- | --- |
| t3_booking_adm_amc/r1-search/S1 | {'rounding': ('down', 'half_up'), 'valued': 'cents', 'parameter_day': 'RUN'} | 2663960 / 2928356 | 666796 / 733109 |
| t3_booking_adm_amc/r1-search/S2 | {'rounding': ('down', 'half_up'), 'valued': 'micro', 'parameter_day': 'RUN'} | 2662917 / 2928356 | 666549 / 733109 |
| t3_booking_adm_amc/r1-search/S3 | {'rounding': 'half_up', 'valued': 'cents', 'parameter_day': 'RUN'} | 2547558 / 2928356 | 637126 / 733109 |
| t3_booking_adm_amc/r1-search/S4 | {'rounding': 'half_up', 'valued': 'micro', 'parameter_day': 'RUN'} | 2546548 / 2928356 | 636884 / 733109 |
| t3_booking_adm_amc/r1-search/S5 | {'rounding': ('down', 'half_up'), 'valued': 'cents', 'parameter_day': 'PH_APPDT'} | 1720220 / 2928356 | 430611 / 733109 |
| t3_booking_adm_amc/r1-search/S6 | {'rounding': ('down', 'half_up'), 'valued': 'micro', 'parameter_day': 'PH_APPDT'} | 1719266 / 2928356 | 430374 / 733109 |
| t3_booking_adm_amc/r1-search/S7 | {'rounding': 'half_up', 'valued': 'cents', 'parameter_day': 'PH_APPDT'} | 1647499 / 2928356 | 411992 / 733109 |
| t3_booking_adm_amc/r1-search/S8 | {'rounding': 'half_up', 'valued': 'micro', 'parameter_day': 'PH_APPDT'} | 1646567 / 2928356 | 411760 / 733109 |
| t3_booking_adm_amc/r1-search/S9 | {'rounding': 'down', 'valued': 'micro', 'parameter_day': 'RUN'} | 810766 / 2928356 | 202414 / 733109 |
| t3_booking_adm_amc/r1-search/S10 | {'rounding': 'down', 'valued': 'cents', 'parameter_day': 'RUN'} | 810754 / 2928356 | 202417 / 733109 |
| t3_booking_adm_amc/r1-search/S11 | {'rounding': 'down', 'valued': 'micro', 'parameter_day': 'PH_APPDT'} | 512266 / 2928356 | 128215 / 733109 |
| t3_booking_adm_amc/r1-search/S12 | {'rounding': 'down', 'valued': 'cents', 'parameter_day': 'PH_APPDT'} | 512247 / 2928356 | 128214 / 733109 |
