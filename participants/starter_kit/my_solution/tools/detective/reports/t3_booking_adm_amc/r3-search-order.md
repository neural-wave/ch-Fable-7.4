# t3_booking_adm_amc, r3-search-order

After r3/T1, T2 of t3_booking_adm and t3_booking_amc: the wrong charges are of runs on the 30th or 31st and of monthly bank transfers, where a premium is received shortly before the run and bought after it. Hole: which bookings a run sees, by event number or by trade date (detective.replay.ordering).

| Finding | Holes | Right (80 %) | Right (held out) |
| --- | --- | --- | --- |
| t3_booking_adm_amc/r3-search-order/S1 | {'order': 'day_strict'} | 2906371 / 2928356 | 727599 / 733109 |
| t3_booking_adm_amc/r3-search-order/S2 | {'order': 'day'} | 2895346 / 2928356 | 724823 / 733109 |
| t3_booking_adm_amc/r3-search-order/S3 | {'order': 'event'} | 2883152 / 2928356 | 721804 / 733109 |
