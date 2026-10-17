# t2_projection_year, r3-search-era

All policies, one pot, nearest age, decimal growth (r2-search-regular/S1, r2-search-age/S1). Rounding by era: cut off up to the system conversion (event 800), half up after, judged on the application or the start date (r2-search-old/S1 against r1-search-single/S1).

| Finding | Holes | Right (80 %) | Right (held out) |
| --- | --- | --- | --- |
| t2_projection_year/r3-search-era/S1 | {'rounding': 'PH_APPDT', 'parameter_day': 'PH_APPDT'} | 62657 / 64021 | 14575 / 15019 |
| t2_projection_year/r3-search-era/S2 | {'rounding': 'PH_BEGDT', 'parameter_day': 'PH_APPDT'} | 62468 / 64021 | 14575 / 15019 |
| t2_projection_year/r3-search-era/S3 | {'rounding': 'PH_APPDT', 'parameter_day': 'PH_BEGDT'} | 60943 / 64021 | 14184 / 15019 |
| t2_projection_year/r3-search-era/S4 | {'rounding': 'PH_BEGDT', 'parameter_day': 'PH_BEGDT'} | 60754 / 64021 | 14184 / 15019 |
| t2_projection_year/r3-search-era/S5 | {'rounding': 'half_up', 'parameter_day': 'PH_APPDT'} | 43861 / 64021 | 10549 / 15019 |
| t2_projection_year/r3-search-era/S6 | {'rounding': 'half_up', 'parameter_day': 'PH_BEGDT'} | 42508 / 64021 | 10158 / 15019 |
| t2_projection_year/r3-search-era/S7 | {'rounding': 'down', 'parameter_day': 'PH_APPDT'} | 19105 / 64021 | 4097 / 15019 |
| t2_projection_year/r3-search-era/S8 | {'rounding': 'down', 'parameter_day': 'PH_BEGDT'} | 18734 / 64021 | 4095 / 15019 |
