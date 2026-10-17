# t3_booking_prm, r5-search-fx

After r5/T1, T3: 363 premium bookings have the right amount but other units, mostly where the trade date is more than one day after the money date (a fund without a price on the next business day). The rate of the money date and the last rate before the trade date differ only there. Hole: the date of the exchange rate.

| Finding | Holes | Right (80 %) | Right (held out) |
| --- | --- | --- | --- |
| t3_booking_prm/r5-search-fx/S1 | {'fx_day': 'EVE'} | 325706 / 326017 | 81559 / 81619 |
| t3_booking_prm/r5-search-fx/S2 | {'fx_day': 'PR_RCVDT'} | 325425 / 326017 | 81482 / 81619 |
| t3_booking_prm/r5-search-fx/S3 | {'fx_day': 'BK_TRDDT'} | 260018 / 326017 | 65051 / 81619 |
