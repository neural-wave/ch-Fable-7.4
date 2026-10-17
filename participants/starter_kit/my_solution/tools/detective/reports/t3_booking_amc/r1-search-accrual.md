# t3_booking_amc, r1-search-accrual

After r1/C1: 65.1 % of the management charges before the conversion are wrong, 1.3 % after. Before it, the target over the twelfth of the yearly charge is 1.033 after a month of 31 days, 1.000 after 30, 0.967 after 29 and 0.933 after 28 (median per month length): days over 360. Hole: the part of the year a run charges, per system.

| Finding | Holes | Right (80 %) | Right (held out) |
| --- | --- | --- | --- |
| t3_booking_amc/r1-search-accrual/S1 | {'accrual': ('days360', 'month')} | 1441857 / 1467108 | 360433 / 366852 |
| t3_booking_amc/r1-search-accrual/S2 | {'accrual': 'month'} | 1350566 / 1467108 | 337927 / 366852 |
| t3_booking_amc/r1-search-accrual/S3 | {'accrual': ('days365', 'month')} | 1308389 / 1467108 | 327348 / 366852 |
| t3_booking_amc/r1-search-accrual/S4 | {'accrual': 'days360'} | 578543 / 1467108 | 144123 / 366852 |
