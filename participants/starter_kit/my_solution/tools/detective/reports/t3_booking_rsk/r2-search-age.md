# t3_booking_rsk, r2-search-age

After r2/T1: the wrong risk charges are of insured persons born on day 1 to 12 of a month, in policies of the old system that run on after the conversion. In t2 the entry age convention belonged to the system that made the offer (r5-search-era-age/S1). Hole: the date that tells which system the age convention belongs to.

| Finding | Holes | Right (80 %) | Right (held out) |
| --- | --- | --- | --- |
| t3_booking_rsk/r2-search-age/S1 | {'age_era_day': 'PH_APPDT', 'risk_age': ('nearest_days365', 'nearest')} | 764888 / 764890 | 190855 / 190856 |
| t3_booking_rsk/r2-search-age/S2 | {'age_era_day': 'PH_BEGDT', 'risk_age': ('nearest_days365', 'nearest')} | 764888 / 764890 | 190855 / 190856 |
| t3_booking_rsk/r2-search-age/S3 | {'age_era_day': 'RUN', 'risk_age': ('nearest_days365', 'nearest')} | 760776 / 764890 | 189826 / 190856 |
| t3_booking_rsk/r2-search-age/S4 | {'age_era_day': 'RUN', 'risk_age': 'nearest'} | 759772 / 764890 | 189605 / 190856 |
| t3_booking_rsk/r2-search-age/S5 | {'age_era_day': 'PH_APPDT', 'risk_age': 'nearest'} | 759772 / 764890 | 189605 / 190856 |
| t3_booking_rsk/r2-search-age/S6 | {'age_era_day': 'PH_BEGDT', 'risk_age': 'nearest'} | 759772 / 764890 | 189605 / 190856 |
