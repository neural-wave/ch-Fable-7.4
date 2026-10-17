# t0_commission, r1-search

The holes of commission.py, after finding r1/T1 (the broker tier on the money date differs from the last one).

| Finding | Holes | Right (80 %) | Right (held out) |
| --- | --- | --- | --- |
| t0_commission/r1-search/S1 | {'broker_day': 'PR_RCVDT', 'rate_day': 'PR_DUEDT', 'half_up': True} | 183519 / 183527 | 42329 / 42331 |
| t0_commission/r1-search/S2 | {'broker_day': 'PR_RCVDT', 'rate_day': 'PR_RCVDT', 'half_up': True} | 183519 / 183527 | 42329 / 42331 |
| t0_commission/r1-search/S3 | {'broker_day': 'PR_RCVDT', 'rate_day': None, 'half_up': True} | 183519 / 183527 | 42329 / 42331 |
| t0_commission/r1-search/S4 | {'broker_day': 'PR_DUEDT', 'rate_day': 'PR_DUEDT', 'half_up': True} | 183517 / 183527 | 42329 / 42331 |
| t0_commission/r1-search/S5 | {'broker_day': 'PR_DUEDT', 'rate_day': 'PR_RCVDT', 'half_up': True} | 183517 / 183527 | 42329 / 42331 |
| t0_commission/r1-search/S6 | {'broker_day': 'PR_DUEDT', 'rate_day': None, 'half_up': True} | 183517 / 183527 | 42329 / 42331 |
| t0_commission/r1-search/S7 | {'broker_day': 'PR_RCVDT', 'rate_day': 'PR_DUEDT', 'half_up': False} | 183517 / 183527 | 42329 / 42331 |
| t0_commission/r1-search/S8 | {'broker_day': 'PR_RCVDT', 'rate_day': 'PR_RCVDT', 'half_up': False} | 183517 / 183527 | 42329 / 42331 |
| t0_commission/r1-search/S9 | {'broker_day': 'PR_RCVDT', 'rate_day': None, 'half_up': False} | 183517 / 183527 | 42329 / 42331 |
| t0_commission/r1-search/S10 | {'broker_day': 'PR_DUEDT', 'rate_day': 'PR_DUEDT', 'half_up': False} | 183515 / 183527 | 42329 / 42331 |
| t0_commission/r1-search/S11 | {'broker_day': 'PR_DUEDT', 'rate_day': 'PR_RCVDT', 'half_up': False} | 183515 / 183527 | 42329 / 42331 |
| t0_commission/r1-search/S12 | {'broker_day': 'PR_DUEDT', 'rate_day': None, 'half_up': False} | 183515 / 183527 | 42329 / 42331 |
| t0_commission/r1-search/S13 | {'broker_day': None, 'rate_day': 'PR_DUEDT', 'half_up': True} | 182304 / 183527 | 42114 / 42331 |
| t0_commission/r1-search/S14 | {'broker_day': None, 'rate_day': 'PR_RCVDT', 'half_up': True} | 182304 / 183527 | 42114 / 42331 |
| t0_commission/r1-search/S15 | {'broker_day': None, 'rate_day': None, 'half_up': True} | 182304 / 183527 | 42114 / 42331 |
| t0_commission/r1-search/S16 | {'broker_day': None, 'rate_day': 'PR_DUEDT', 'half_up': False} | 182302 / 183527 | 42114 / 42331 |
| t0_commission/r1-search/S17 | {'broker_day': None, 'rate_day': 'PR_RCVDT', 'half_up': False} | 182302 / 183527 | 42114 / 42331 |
| t0_commission/r1-search/S18 | {'broker_day': None, 'rate_day': None, 'half_up': False} | 182302 / 183527 | 42114 / 42331 |
