# t3_booking_prm, r3-search-trade

After r3/T1, T2: the missing premium bookings follow a money date with a gap of more than one day to the trade date; 2655 NRBOOK trade dates are one business day later than the first business day after the money date, on no holiday of the calendar. Holes: the trade date as the first price day of the fund after the money date, or the first business day of a calendar.

| Finding | Holes | Right (80 %) | Right (held out) |
| --- | --- | --- | --- |
| t3_booking_prm/r3-search-trade/S1 | {'trade': 'price_day'} | 324867 / 326017 | 81332 / 81619 |
| t3_booking_prm/r3-search-trade/S2 | {'trade': 'TI'} | 323577 / 326017 | 81020 / 81619 |
| t3_booking_prm/r3-search-trade/S3 | {'trade': 'CH'} | 306111 / 326017 | 76710 / 81619 |
| t3_booking_prm/r3-search-trade/S4 | {'trade': 'weekend'} | 302873 / 326017 | 75902 / 81619 |
