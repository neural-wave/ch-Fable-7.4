# t3_booking, r1-search-premium

Round 1 of the premium bookings (llm/007-t3-story.md): 297504 of 407636 right, the price always right (the issue price on the trade date), the cents of the split and the millionths of the units off by 1. Holes: the rounding, by system as in t2, and the date of the broker, entry charge and allocation.

| Finding | Holes | Right (80 %) | Right (held out) |
| --- | --- | --- | --- |
| t3_booking/r1-search-premium/S1 | {'rounding': ('down', 'half_up'), 'era_day': 'PR_RCVDT', 'day': 'PR_RCVDT'} | 258194 / 326017 | 64609 / 81619 |
| t3_booking/r1-search-premium/S2 | {'rounding': ('down', 'half_up'), 'era_day': 'PR_DUEDT', 'day': 'PR_RCVDT'} | 258186 / 326017 | 64605 / 81619 |
| t3_booking/r1-search-premium/S3 | {'rounding': ('down', 'half_up'), 'era_day': 'PR_RCVDT', 'day': 'PR_DUEDT'} | 257916 / 326017 | 64537 / 81619 |
| t3_booking/r1-search-premium/S4 | {'rounding': ('down', 'half_up'), 'era_day': 'PR_DUEDT', 'day': 'PR_DUEDT'} | 257908 / 326017 | 64533 / 81619 |
| t3_booking/r1-search-premium/S5 | {'rounding': 'half_up', 'era_day': 'PR_RCVDT', 'day': 'PR_RCVDT'} | 238125 / 326017 | 59379 / 81619 |
| t3_booking/r1-search-premium/S6 | {'rounding': 'half_up', 'era_day': 'PR_DUEDT', 'day': 'PR_RCVDT'} | 238125 / 326017 | 59379 / 81619 |
| t3_booking/r1-search-premium/S7 | {'rounding': 'half_up', 'era_day': 'PR_RCVDT', 'day': 'PR_DUEDT'} | 237857 / 326017 | 59312 / 81619 |
| t3_booking/r1-search-premium/S8 | {'rounding': 'half_up', 'era_day': 'PR_DUEDT', 'day': 'PR_DUEDT'} | 237857 / 326017 | 59312 / 81619 |
| t3_booking/r1-search-premium/S9 | {'rounding': 'down', 'era_day': 'PR_RCVDT', 'day': 'PR_RCVDT'} | 126326 / 326017 | 31533 / 81619 |
| t3_booking/r1-search-premium/S10 | {'rounding': 'down', 'era_day': 'PR_DUEDT', 'day': 'PR_RCVDT'} | 126326 / 326017 | 31533 / 81619 |
| t3_booking/r1-search-premium/S11 | {'rounding': 'down', 'era_day': 'PR_RCVDT', 'day': 'PR_DUEDT'} | 126214 / 326017 | 31493 / 81619 |
| t3_booking/r1-search-premium/S12 | {'rounding': 'down', 'era_day': 'PR_DUEDT', 'day': 'PR_DUEDT'} | 126214 / 326017 | 31493 / 81619 |
