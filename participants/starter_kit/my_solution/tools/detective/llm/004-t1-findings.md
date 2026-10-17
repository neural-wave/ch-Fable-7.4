# 004 · t1_next_due_dates · from the findings of round r1 to round 2

**Step:** findings → sketch with holes → search → code. **LLM:** Claude Code.

## Input

`reports/t1_next_due_dates/r1-due.md` (round 1: 14780 of 15028 due dates right):

- the wrong due dates are 1 to 3 days later than Neuron's
- **r1-due/T1** past due dates on more than one day of the month (`PR_DUEDT:days_of_month > 1.5`) and an
  application up to 2006: 248 of 255 wrong. The schedule did not keep the start day: Neuron moved it.

`reports/t1_next_due_dates/r1-collection.md` (the target due date as context):

- the wrong collection dates are 1 to 3 days later than the due date
- **r1-collection/T1** due date on Saturday or Sunday and payment method not UB: 3346 of 3371 wrong
- **r1-collection/T2** due date on a Friday and not UB: 707 of 1403 wrong (Fridays before a holiday weekend)
- **r1-collection/T4** a Ticino holiday on a weekday: 27 of 35 wrong

## Prompt

The story says Neuron "maintains the schedule itself" and that the past due dates show how. Write the due dates
as a sketch whose holes are the places a schedule can start from and the two ways to add periods, and the
collection date as a sketch whose holes are the payment methods that move and the calendar. Every candidate
must come from the data: dates of NRPREM, and every event type of the code list EVTTP, not a chosen one.

## Output

`schedule.py`, round 2 with holes `anchor` (PH_BEGDT, first or last past due, the first past due on or after
the first event of each of the 15 event types), `chained`, `shifted`, `calendar`.

## Search

`reports/t1_next_due_dates/r2-due-search.md`, due dates only, 36 candidates:

- **S1** anchor = first due on or after event 800 (system conversion), whole periods: 12131 / 12131,
  held out 2897 / 2897
- the next best (event 400) 112 rows fewer; the start date (the story's reading) 198 fewer; chained steps
  are worse everywhere

`reports/t1_next_due_dates/r2-collection-search.md`, with the due dates of S1, 8 candidates:

- **S1** LS on the next business day of the Ticino calendar, UB on the due date: 12131 / 12131, held out
  2897 / 2897; weekends only: 613 fewer

## Result

`schedule.py` defaults: anchor = 800, whole periods, LS shifted, Ticino calendar. 15028 of 15028.
