# t3_booking_prm, r4-search-entry

After r4: 827 of the 861 premiums with a wrong split invest one cent less than Neuron; all looked at have an individual entry rate (NRAGRE ENT, 0.5 % or 1.5 %) whose charge is an exact half cent (192.5, 787.5). Hole: how the entry charge is rounded.

| Finding | Holes | Right (80 %) | Right (held out) |
| --- | --- | --- | --- |
| t3_booking_prm/r4-search-entry/S1 | {'entry': 'down'} | 325425 / 326017 | 81482 / 81619 |
| t3_booking_prm/r4-search-entry/S2 | {'entry': 'half_down'} | 325425 / 326017 | 81482 / 81619 |
| t3_booking_prm/r4-search-entry/S3 | {'entry': 'split'} | 324867 / 326017 | 81332 / 81619 |
