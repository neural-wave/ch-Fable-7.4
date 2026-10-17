# t1_next_due_dates: notes

## 2026-10-17, observations made while testing the harness (not rules yet: check each with `lab score`)

Measured on the train targets, with `lab show` and Polars:
- **Rows per policy.** Exactly 12, 4, 2 or 1 rows for the frequencies M, Q, H and J (1118, 347, 41 and 142
  policies). Every due date is in (2026-06-30, 2027-06-30]: one year after the extract date.
- **Which policies.** All 1648 policies of t1 have PH_STATE = 10 in their latest NRPOLH version and a frequency other
  than E (single premium). One train policy in state 10 with frequency Q has no rows: BL10001854. Why is open.
- **Day of the due date.** It is the day of PH_BEGDT in 14420 of 15028 rows. The 608 other rows all have
  begin day > due day:
  - 360 of them are month ends (e.g. BL10000018, begin 2024-08-31: 2026-09-30, 2027-02-28);
  - 248 are not: the day stays 28, 29 or 30 for the whole year. Example: BL10000267, begin 2006-03-31, all due dates
    on the 28th. This policy began before the system change of 2007-08-11; compare with its NRPREM due dates.
- **No holiday table** in legacy/ (searched SCHEMA.md and NRDICT for holiday/calendar).

From `lab run t1_next_due_dates`, with the earlier target column as input:
- `due_date` has no relation with dense clusters: it is a schedule. Write it in submission.py and score it with
  `lab score`.
- `collection_date - due_date` takes 0, 1, 2 or 3 days:
  - UB always 0;
  - LS by weekday: Saturday +2, Sunday +1, holidays more.
  - The optimal tree on {weekday(due_date), PH_PAYMT, day(due_date)} gets 14671 of 15028 rows right, given the
    right due date. The rest is in two groups:
    - UB rows on a Sunday: depth 3 leaves no split for them;
    - probably holidays: lag 1 on a Monday or Tuesday, 3 on a Friday, 2 on a Sunday before a holiday Monday, e.g.
      Sunday 2027-03-28 and Easter Monday 2027-03-29. Check each date with `lab score`.
