# charge_bookings, r1-search-booked

Which charges become bookings. Every run, fund and pot held and charge type is a candidate; booked is 1 when NRBOOK has the booking. Two RSK amounts of -1 cent (the largest-remainder correction of shares rounded up to 1 cent each) have no booking in NRBOOK. Hole: the amounts that are booked.

| Finding | Holes | Right (80 %) | Right (held out) |
| --- | --- | --- | --- |
| charge_bookings/r1-search-booked/S1 | {'booked': 'positive'} | 4470186 / 4470186 | 1034553 / 1034553 |
| charge_bookings/r1-search-booked/S2 | {'booked': 'nonzero'} | 4470186 / 4470186 | 1034551 / 1034553 |
