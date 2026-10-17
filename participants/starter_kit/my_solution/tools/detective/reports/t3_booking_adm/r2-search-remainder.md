# t3_booking_adm, r2-search-remainder

After r2: the admin fee bookings of a run add up to the tariff fee in Neuron (all but 5 of 397842 runs) but not in round 2 in 149132 runs. Holes: where the cents go that the rounded shares miss, and the rounding of the shares.

| Finding | Holes | Right (80 %) | Right (held out) |
| --- | --- | --- | --- |
| t3_booking_adm/r2-search-remainder/S1 | {'remainder': 'largest', 'rounding': ('down', 'half_up')} | 1427910 / 1461248 | 357920 / 366257 |
| t3_booking_adm/r2-search-remainder/S2 | {'remainder': 'largest', 'rounding': 'half_up'} | 1315557 / 1461248 | 329273 / 366257 |
| t3_booking_adm/r2-search-remainder/S3 | {'remainder': 'none', 'rounding': ('down', 'half_up')} | 1313394 / 1461248 | 328869 / 366257 |
| t3_booking_adm/r2-search-remainder/S4 | {'remainder': 'last', 'rounding': ('down', 'half_up')} | 1261688 / 1461248 | 316409 / 366257 |
| t3_booking_adm/r2-search-remainder/S5 | {'remainder': 'first', 'rounding': ('down', 'half_up')} | 1235531 / 1461248 | 309322 / 366257 |
| t3_booking_adm/r2-search-remainder/S6 | {'remainder': 'none', 'rounding': 'half_up'} | 1234809 / 1461248 | 308832 / 366257 |
| t3_booking_adm/r2-search-remainder/S7 | {'remainder': 'hamilton', 'rounding': ('down', 'half_up')} | 1212099 / 1461248 | 303336 / 366257 |
| t3_booking_adm/r2-search-remainder/S8 | {'remainder': 'last', 'rounding': 'half_up'} | 1192012 / 1461248 | 298429 / 366257 |
| t3_booking_adm/r2-search-remainder/S9 | {'remainder': 'hamilton', 'rounding': 'half_up'} | 1178985 / 1461248 | 294932 / 366257 |
| t3_booking_adm/r2-search-remainder/S10 | {'remainder': 'first', 'rounding': 'half_up'} | 1173701 / 1461248 | 293553 / 366257 |
