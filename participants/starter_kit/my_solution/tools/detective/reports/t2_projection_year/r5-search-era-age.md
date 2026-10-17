# t2_projection_year, r5-search-era-age

After r5-search-age: 21 of the 22 wrong policies were offered by the old system (PH_APPDT up to the conversion) and are right with the entry age one higher (a diagnostic run with the age shifted by -1 and +1). Hole: the age convention as a pair (old system, Neuron NG), and the date that decides the system.

| Finding | Holes | Right (80 %) | Right (held out) |
| --- | --- | --- | --- |
| t2_projection_year/r5-search-era-age/S1 | {'age': ('nearest_days365', 'nearest'), 'era_day': 'PH_APPDT'} | 64021 / 64021 | 14998 / 15019 |
| t2_projection_year/r5-search-era-age/S2 | {'age': ('nearest_days365', 'months'), 'era_day': 'PH_APPDT'} | 64021 / 64021 | 14998 / 15019 |
| t2_projection_year/r5-search-era-age/S3 | {'age': ('nearest_days365', 'nearest'), 'era_day': 'PH_BEGDT'} | 63832 / 64021 | 14998 / 15019 |
| t2_projection_year/r5-search-era-age/S4 | {'age': ('nearest_days365', 'months'), 'era_day': 'PH_BEGDT'} | 63832 / 64021 | 14998 / 15019 |
| t2_projection_year/r5-search-era-age/S5 | {'age': ('nearest_days365.25', 'nearest'), 'era_day': 'PH_APPDT'} | 63637 / 64021 | 14864 / 15019 |
| t2_projection_year/r5-search-era-age/S6 | {'age': ('nearest_days365.25', 'months'), 'era_day': 'PH_APPDT'} | 63637 / 64021 | 14864 / 15019 |
| t2_projection_year/r5-search-era-age/S7 | {'age': ('nearest', 'nearest'), 'era_day': 'PH_APPDT'} | 63604 / 64021 | 14835 / 15019 |
| t2_projection_year/r5-search-era-age/S8 | {'age': ('nearest', 'months'), 'era_day': 'PH_APPDT'} | 63604 / 64021 | 14835 / 15019 |
| t2_projection_year/r5-search-era-age/S9 | {'age': ('months', 'nearest'), 'era_day': 'PH_APPDT'} | 63604 / 64021 | 14835 / 15019 |
| t2_projection_year/r5-search-era-age/S10 | {'age': ('months', 'months'), 'era_day': 'PH_APPDT'} | 63604 / 64021 | 14835 / 15019 |
| t2_projection_year/r5-search-era-age/S11 | {'age': ('nearest_days365.25', 'nearest'), 'era_day': 'PH_BEGDT'} | 63448 / 64021 | 14864 / 15019 |
| t2_projection_year/r5-search-era-age/S12 | {'age': ('nearest_days365.25', 'months'), 'era_day': 'PH_BEGDT'} | 63448 / 64021 | 14864 / 15019 |
| t2_projection_year/r5-search-era-age/S13 | {'age': ('nearest', 'nearest'), 'era_day': 'PH_BEGDT'} | 63415 / 64021 | 14835 / 15019 |
| t2_projection_year/r5-search-era-age/S14 | {'age': ('nearest', 'months'), 'era_day': 'PH_BEGDT'} | 63415 / 64021 | 14835 / 15019 |
| t2_projection_year/r5-search-era-age/S15 | {'age': ('months', 'nearest'), 'era_day': 'PH_BEGDT'} | 63415 / 64021 | 14835 / 15019 |
| t2_projection_year/r5-search-era-age/S16 | {'age': ('months', 'months'), 'era_day': 'PH_BEGDT'} | 63415 / 64021 | 14835 / 15019 |
| t2_projection_year/r5-search-era-age/S17 | {'age': ('days365', 'nearest'), 'era_day': 'PH_APPDT'} | 54926 / 64021 | 13097 / 15019 |
| t2_projection_year/r5-search-era-age/S18 | {'age': ('days365', 'months'), 'era_day': 'PH_APPDT'} | 54926 / 64021 | 13097 / 15019 |
| t2_projection_year/r5-search-era-age/S19 | {'age': ('days365', 'nearest'), 'era_day': 'PH_BEGDT'} | 54830 / 64021 | 13118 / 15019 |
| t2_projection_year/r5-search-era-age/S20 | {'age': ('days365', 'months'), 'era_day': 'PH_BEGDT'} | 54830 / 64021 | 13118 / 15019 |
| t2_projection_year/r5-search-era-age/S21 | {'age': ('completed', 'nearest'), 'era_day': 'PH_APPDT'} | 54435 / 64021 | 13045 / 15019 |
| t2_projection_year/r5-search-era-age/S22 | {'age': ('completed', 'months'), 'era_day': 'PH_APPDT'} | 54435 / 64021 | 13045 / 15019 |
| t2_projection_year/r5-search-era-age/S23 | {'age': ('completed', 'nearest'), 'era_day': 'PH_BEGDT'} | 54360 / 64021 | 13066 / 15019 |
| t2_projection_year/r5-search-era-age/S24 | {'age': ('completed', 'months'), 'era_day': 'PH_BEGDT'} | 54360 / 64021 | 13066 / 15019 |
