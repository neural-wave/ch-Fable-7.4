# t3_booking_adm_amc, r2-search-units

After r2 (t3_booking_amc): 8885 management charges have the right amount and units off by one millionth. Hole: how an amount becomes units, with the exchange rate rounded to millionths or exact.

| Finding | Holes | Right (80 %) | Right (held out) |
| --- | --- | --- | --- |
| t3_booking_adm_amc/r2-search-units/S1 | {'conversion': 'exact'} | 2882990 / 2928356 | 721764 / 733109 |
| t3_booking_adm_amc/r2-search-units/S2 | {'conversion': 'rate'} | 2874657 / 2928356 | 719650 / 733109 |
