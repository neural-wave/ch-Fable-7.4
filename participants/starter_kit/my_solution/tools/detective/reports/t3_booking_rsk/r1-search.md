# t3_booking_rsk, r1-search

Round 1 of the risk charge in the charge run (the t2 formula on the whole value of the run, shared like the admin fee): 892637 of 955746 right. Holes: the part of the year (the old system accrued management charges by days), the age (convention per system, attained on the run date or entry age plus policy years).

| Finding | Holes | Right (80 %) | Right (held out) |
| --- | --- | --- | --- |
| t3_booking_rsk/r1-search/S1 | {'risk_accrual': 'month', 'age_basis': 'policy', 'risk_age': ('nearest_days365', 'nearest')} | 714346 / 764890 | 178291 / 190856 |
| t3_booking_rsk/r1-search/S2 | {'risk_accrual': 'month', 'age_basis': 'policy', 'risk_age': 'nearest'} | 713475 / 764890 | 178104 / 190856 |
| t3_booking_rsk/r1-search/S3 | {'risk_accrual': ('anniversary360', 'month'), 'age_basis': 'policy', 'risk_age': ('nearest_days365', 'nearest')} | 690435 / 764890 | 172329 / 190856 |
| t3_booking_rsk/r1-search/S4 | {'risk_accrual': ('anniversary360', 'month'), 'age_basis': 'policy', 'risk_age': 'nearest'} | 690036 / 764890 | 172247 / 190856 |
| t3_booking_rsk/r1-search/S5 | {'risk_accrual': 'month', 'age_basis': 'attained', 'risk_age': 'completed'} | 613822 / 764890 | 153234 / 190856 |
| t3_booking_rsk/r1-search/S6 | {'risk_accrual': ('anniversary360', 'month'), 'age_basis': 'attained', 'risk_age': 'completed'} | 596505 / 764890 | 148949 / 190856 |
| t3_booking_rsk/r1-search/S7 | {'risk_accrual': 'month', 'age_basis': 'attained', 'risk_age': 'nearest'} | 534322 / 764890 | 132996 / 190856 |
| t3_booking_rsk/r1-search/S8 | {'risk_accrual': 'month', 'age_basis': 'attained', 'risk_age': ('nearest_days365', 'nearest')} | 532834 / 764890 | 132656 / 190856 |
| t3_booking_rsk/r1-search/S9 | {'risk_accrual': ('anniversary360', 'month'), 'age_basis': 'attained', 'risk_age': 'nearest'} | 519801 / 764890 | 129358 / 190856 |
| t3_booking_rsk/r1-search/S10 | {'risk_accrual': ('anniversary360', 'month'), 'age_basis': 'attained', 'risk_age': ('nearest_days365', 'nearest')} | 518831 / 764890 | 129140 / 190856 |
| t3_booking_rsk/r1-search/S11 | {'risk_accrual': 'month', 'age_basis': 'policy', 'risk_age': 'completed'} | 506583 / 764890 | 126410 / 190856 |
| t3_booking_rsk/r1-search/S12 | {'risk_accrual': ('anniversary360', 'month'), 'age_basis': 'policy', 'risk_age': 'completed'} | 497469 / 764890 | 124097 / 190856 |
