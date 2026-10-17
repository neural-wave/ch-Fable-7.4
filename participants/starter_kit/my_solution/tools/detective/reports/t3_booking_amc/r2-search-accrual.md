# t3_booking_amc, r2-search-accrual

After r2/T1: the wrong management charges of the old system are of policies whose monthly anniversary is the 30th or 31st, where the same day a month earlier is not the day of the previous run. Hole: the days since the previous run.

| Finding | Holes | Right (80 %) | Right (held out) |
| --- | --- | --- | --- |
| t3_booking_amc/r2-search-accrual/S1 | {'accrual': ('runs360', 'month')} | 1446747 / 1467108 | 361730 / 366852 |
| t3_booking_amc/r2-search-accrual/S2 | {'accrual': ('days360', 'month')} | 1441857 / 1467108 | 360433 / 366852 |
