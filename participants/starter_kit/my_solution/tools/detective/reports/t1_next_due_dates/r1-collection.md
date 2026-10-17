# t1_next_due_dates, r1-collection

Round 1 (llm/003-t1-story.md), collection dates only; the target due date is context.

## Rows

right: 10758, wrong: 4270

## Most common differences

- due_date: 0 (4022), 2 (133), 3 (88), 1 (27)
- collection_date: -2 (2080), -1 (1274), -3 (673), 2 (108), 3 (78), 1 (32), 0 (25)

## Conditions (decision tree on the wrong rows)

- **t1_next_due_dates/r1-collection/T1** due_date:weekday > 4.5 and PH_PAYMT@RK_BEGDT != UB and due_date:weekday > 5.5: 3346 of 3371 wrong (99.3%)
- **t1_next_due_dates/r1-collection/T2** due_date:weekday > 4.5 and PH_PAYMT@RK_BEGDT != UB and due_date:weekday <= 5.5: 707 of 1403 wrong (50.4%)
- **t1_next_due_dates/r1-collection/T3** due_date:weekday <= 4.5 and PR_DUEDT:last:weekday > 6.5 and PR_DUEDT:days_of_month > 1.5: 147 of 155 wrong (94.8%)
- **t1_next_due_dates/r1-collection/T4** due_date:weekday <= 4.5 and PR_DUEDT:last:weekday <= 6.5 and due_date:TI_holiday: 27 of 35 wrong (77.1%)

## Change points

- **t1_next_due_dates/r1-collection/C1** due_date between 2026-12-24 and 2026-12-25: wrong 27.9% before, 28.5% after (explains 5.1%)
- **t1_next_due_dates/r1-collection/C2** PR_RCVDT:last between 2026-06-04 and 2026-06-05: wrong 30.6% before, 12.2% after (explains 1.9%)
- **t1_next_due_dates/r1-collection/C3** EV_EFFDT:last between 2026-06-04 and 2026-06-05: wrong 29.9% before, 26.1% after (explains 1.4%)
- **t1_next_due_dates/r1-collection/C4** PR_DUEDT:last between 2026-06-29 and 2026-06-30: wrong 28.6% before, 23.3% after (explains 0.6%)
- **t1_next_due_dates/r1-collection/C5** HD_VLDFR@RK_ENDDT between 2006-08-31 and 2006-09-01: wrong 33.6% before, 27.2% after (explains 0.3%)
- **t1_next_due_dates/r1-collection/C6** HD_CHGTS@RK_ENDDT between 2006-10-11T08:45:01.000000 and 2006-10-21T10:29:01.000000: wrong 33.5% before, 27.2% after (explains 0.3%)
- **t1_next_due_dates/r1-collection/C7** RK_BEGDT between 2006-08-31 and 2006-09-01: wrong 33.4% before, 27.2% after (explains 0.3%)
- **t1_next_due_dates/r1-collection/C8** PR_RCVDT:first between 2006-09-03 and 2006-09-12: wrong 33.4% before, 27.2% after (explains 0.3%)
- **t1_next_due_dates/r1-collection/C9** EV_EFFDT:first between 2006-08-31 and 2006-09-01: wrong 33.4% before, 27.2% after (explains 0.3%)
- **t1_next_due_dates/r1-collection/C10** PH_CHGTS@RK_BEGDT between 2006-10-11T08:45:01.000000 and 2006-10-21T10:29:01.000000: wrong 33.3% before, 27.2% after (explains 0.3%)
