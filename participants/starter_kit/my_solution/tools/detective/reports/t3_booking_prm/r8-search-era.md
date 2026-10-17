# t3_booking_prm, r8-search-era

After r7-search-split/S1 7 premium bookings are wrong, all received on 2007-08-10 and traded on 2007-08-13, across the system conversion of 2007-08-11: Neuron NG rounded them half up. Hole: the date that tells the system of a booking.

| Finding | Holes | Right (80 %) | Right (held out) |
| --- | --- | --- | --- |
| t3_booking_prm/r8-search-era/S1 | {'era_day': 'BK_TRDDT'} | 326017 / 326017 | 81619 / 81619 |
| t3_booking_prm/r8-search-era/S2 | {'era_day': 'PR_RCVDT'} | 326011 / 326017 | 81618 / 81619 |
| t3_booking_prm/r8-search-era/S3 | {'era_day': 'PR_DUEDT'} | 325996 / 326017 | 81612 / 81619 |
