# t3_booking_prm, r7-search-split

After r7-search-entry-era: on the single-fund premiums with a fractional entry charge (all exact halves, all with an agreement), Neuron NG cut the charge off (581 premiums, 16 policies) and the old system rounded it up (24, 1 policy), so no rounding of the charge alone fits both. Hole: the amount of a fund as one rounding of premium x (1 - entry rate) x share.

| Finding | Holes | Right (80 %) | Right (held out) |
| --- | --- | --- | --- |
| t3_booking_prm/r7-search-split/S1 | {'split': 'premium', 'entry': 'down'} | 326011 / 326017 | 81618 / 81619 |
| t3_booking_prm/r7-search-split/S2 | {'split': 'premium', 'entry': 'net'} | 326011 / 326017 | 81618 / 81619 |
| t3_booking_prm/r7-search-split/S3 | {'split': 'net', 'entry': 'down'} | 325878 / 326017 | 81591 / 81619 |
| t3_booking_prm/r7-search-split/S4 | {'split': 'net', 'entry': 'net'} | 325864 / 326017 | 81588 / 81619 |
