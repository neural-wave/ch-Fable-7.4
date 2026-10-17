# t3_booking_prm, r2-search-fx

After r2/T1-T4: the wrong premium bookings are those whose fund currency is not the policy currency (64958 of 64958 under T1-T4). Holes: the date of the exchange rate and how the amount is converted.

| Finding | Holes | Right (80 %) | Right (held out) |
| --- | --- | --- | --- |
| t3_booking_prm/r2-search-fx/S1 | {'fx_day': 'PR_RCVDT', 'conversion': 'exact'} | 323577 / 326017 | 81020 / 81619 |
| t3_booking_prm/r2-search-fx/S2 | {'fx_day': 'PR_RCVDT', 'conversion': 'rate'} | 306147 / 326017 | 76715 / 81619 |
| t3_booking_prm/r2-search-fx/S3 | {'fx_day': 'PR_DUEDT', 'conversion': 'exact'} | 263961 / 326017 | 66035 / 81619 |
| t3_booking_prm/r2-search-fx/S4 | {'fx_day': 'PR_DUEDT', 'conversion': 'rate'} | 262330 / 326017 | 65635 / 81619 |
| t3_booking_prm/r2-search-fx/S5 | {'fx_day': 'PR_RCVDT', 'conversion': 'cents'} | 260296 / 326017 | 65145 / 81619 |
| t3_booking_prm/r2-search-fx/S6 | {'fx_day': 'PR_DUEDT', 'conversion': 'cents'} | 258384 / 326017 | 64667 / 81619 |
| t3_booking_prm/r2-search-fx/S7 | {'fx_day': 'BK_TRDDT', 'conversion': 'cents'} | 258202 / 326017 | 64609 / 81619 |
| t3_booking_prm/r2-search-fx/S8 | {'fx_day': 'BK_TRDDT', 'conversion': 'rate'} | 258194 / 326017 | 64609 / 81619 |
| t3_booking_prm/r2-search-fx/S9 | {'fx_day': 'BK_TRDDT', 'conversion': 'exact'} | 258194 / 326017 | 64609 / 81619 |
