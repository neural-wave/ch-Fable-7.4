# t3_booking_charges, r1-search-limit

After r1: the 6 wrong bookings are two runs of paid-up policies whose value runs out. In one the admin fee (850) took exactly the value of every fund (754 in all) while the management charge of 1 cent was still booked; in the other the risk charge (199) took exactly what the admin fee and the management charge left. Hole: what a run takes when the value runs out.

| Finding | Holes | Right (80 %) | Right (held out) |
| --- | --- | --- | --- |
| t3_booking_charges/r1-search-limit/S1 | {'limit': 'value'} | 3693246 / 3693246 | 923965 / 923965 |
| t3_booking_charges/r1-search-limit/S2 | {'limit': 'all'} | 3693245 / 3693246 | 923964 / 923965 |
| t3_booking_charges/r1-search-limit/S3 | {'limit': 'none'} | 3693243 / 3693246 | 923962 / 923965 |
