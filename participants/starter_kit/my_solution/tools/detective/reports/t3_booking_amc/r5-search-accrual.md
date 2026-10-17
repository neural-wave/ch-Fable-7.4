# t3_booking_amc, r5-search-accrual

After r5/T1: the last 78 wrong management charges are of the first run of old policies that start on the 31st: Neuron counted the days from the start date (30 from 2002-10-31 to 2002-11-30), not from the same day a month before the run. Hole: the days since the previous monthly anniversary of the start date.

| Finding | Holes | Right (80 %) | Right (held out) |
| --- | --- | --- | --- |
| t3_booking_amc/r5-search-accrual/S1 | {'accrual': ('anniversary360', 'month')} | 1467108 / 1467108 | 366852 / 366852 |
| t3_booking_amc/r5-search-accrual/S2 | {'accrual': ('days360', 'month')} | 1461867 / 1467108 | 365455 / 366852 |
| t3_booking_amc/r5-search-accrual/S3 | {'accrual': ('anniversary365', 'month')} | 1326213 / 1467108 | 331828 / 366852 |
