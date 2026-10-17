# order_bookings, r1-search

The customer orders (switch, withdrawal, surrender, death) are complete in NRBOOK: their price and exchange rate show the market conventions. Price: the last price of the fund on or before the trade date, latest publication.

| Finding | Holes | Right (80 %) | Right (held out) |
| --- | --- | --- | --- |
| order_bookings/r1-search/S1 | {'price': 'FP_BIDPR', 'fx_day': 'BK_TRDDT', 'fx_round': 'half_up'} | 19964 / 19964 | 4948 / 4948 |
| order_bookings/r1-search/S2 | {'price': 'FP_BIDPR', 'fx_day': 'BK_PRCDT', 'fx_round': 'half_up'} | 19927 / 19964 | 4936 / 4948 |
| order_bookings/r1-search/S3 | {'price': 'FP_BIDPR', 'fx_day': 'BK_TRDDT', 'fx_round': 'down'} | 16544 / 19964 | 4053 / 4948 |
| order_bookings/r1-search/S4 | {'price': 'FP_BIDPR', 'fx_day': 'BK_PRCDT', 'fx_round': 'down'} | 16529 / 19964 | 4047 / 4948 |
| order_bookings/r1-search/S5 | {'price': 'FP_ASKPR', 'fx_day': 'BK_TRDDT', 'fx_round': 'half_up'} | 5393 / 19964 | 1313 / 4948 |
| order_bookings/r1-search/S6 | {'price': 'FP_MIDPR', 'fx_day': 'BK_TRDDT', 'fx_round': 'half_up'} | 5393 / 19964 | 1313 / 4948 |
| order_bookings/r1-search/S7 | {'price': 'FP_ASKPR', 'fx_day': 'BK_PRCDT', 'fx_round': 'half_up'} | 5389 / 19964 | 1312 / 4948 |
| order_bookings/r1-search/S8 | {'price': 'FP_MIDPR', 'fx_day': 'BK_PRCDT', 'fx_round': 'half_up'} | 5389 / 19964 | 1312 / 4948 |
| order_bookings/r1-search/S9 | {'price': 'FP_ASKPR', 'fx_day': 'BK_TRDDT', 'fx_round': 'down'} | 4490 / 19964 | 1087 / 4948 |
| order_bookings/r1-search/S10 | {'price': 'FP_MIDPR', 'fx_day': 'BK_TRDDT', 'fx_round': 'down'} | 4490 / 19964 | 1087 / 4948 |
| order_bookings/r1-search/S11 | {'price': 'FP_ASKPR', 'fx_day': 'BK_PRCDT', 'fx_round': 'down'} | 4487 / 19964 | 1086 / 4948 |
| order_bookings/r1-search/S12 | {'price': 'FP_MIDPR', 'fx_day': 'BK_PRCDT', 'fx_round': 'down'} | 4487 / 19964 | 1086 / 4948 |
