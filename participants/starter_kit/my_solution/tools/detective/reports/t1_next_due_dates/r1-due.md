# t1_next_due_dates, r1-due

Round 1 (llm/003-t1-story.md), due dates only.

## Rows

right: 10758, wrong: 4270

## Most common differences

- due_date: 0 (4022), 2 (133), 3 (88), 1 (27)
- collection_date: -2 (2080), -1 (1274), -3 (673), 2 (108), 3 (78), 1 (32), 0 (25)

## Conditions (decision tree on the wrong rows)

- **t1_next_due_dates/r1-due/T1** PR_DUEDT:days_of_month > 1.5 and PH_APPDT@RK_BEGDT:year <= 2006.5 and collection_date:holiday != Jahrestag der Ausrufung der Republik: 248 of 255 wrong (97.3%)

## Change points

- **t1_next_due_dates/r1-due/C1** PR_DUEDT:last between 2026-06-28 and 2026-06-29: wrong 1.8% before, 0.2% after (explains 35.8%)
- **t1_next_due_dates/r1-due/C2** EV_EFFDT:last between 2026-06-28 and 2026-06-29: wrong 0.0% before, 16.1% after (explains 14.7%)
- **t1_next_due_dates/r1-due/C3** PR_RCVDT:last between 2026-05-29 and 2026-05-30: wrong 2.1% before, 1.5% after (explains 11.9%)
- **t1_next_due_dates/r1-due/C4** HD_VLDFR@RK_ENDDT between 2006-08-31 and 2006-09-01: wrong 10.1% before, 0.0% after (explains 8.6%)
- **t1_next_due_dates/r1-due/C5** HD_CHGTS@RK_ENDDT between 2006-08-27T09:16:47.000000 and 2006-08-31T11:41:09.000000: wrong 10.0% before, 0.0% after (explains 8.5%)
- **t1_next_due_dates/r1-due/C6** RK_BEGDT between 2006-08-31 and 2006-09-01: wrong 9.8% before, 0.0% after (explains 8.3%)
- **t1_next_due_dates/r1-due/C7** PR_RCVDT:first between 2006-09-03 and 2006-09-12: wrong 9.8% before, 0.0% after (explains 8.3%)
- **t1_next_due_dates/r1-due/C8** EV_EFFDT:first between 2006-08-31 and 2006-09-01: wrong 9.8% before, 0.0% after (explains 8.3%)
- **t1_next_due_dates/r1-due/C9** PH_CHGTS@RK_BEGDT between 2006-08-27T09:16:47.000000 and 2006-08-31T11:41:09.000000: wrong 9.7% before, 0.0% after (explains 8.2%)
- **t1_next_due_dates/r1-due/C10** PH_APPDT@RK_BEGDT between 2006-08-24 and 2006-08-28: wrong 9.7% before, 0.0% after (explains 8.2%)
