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

## 2026-10-17, written function (step 4b): 15028 / 15028, holdout 3011 / 3011

No lab candidate is complete: `due_date` is a schedule, not a relation, and the best `collection_date` candidate
C2.1 (weekday, PH_PAYMT, day) reaches only 14671 / 15028 (holdout 2939 / 3011). No feature was added (no `~llm` run).
I wrote `t1_next_due_dates` in submission.py from the evidence. First `lab score`: 15028 / 15028 (holdout 3011 / 3011).
check.py with the system Python gives the same score in 0.1 s. NRBOOK and NRPREM are not read.

Rules:
- **Policies:** the NRPOLH version valid on the extract date (`valid`, not `latest`) has PH_STATE 10, and PH_FREQ is
  not E. This answers the open question about BL10001854: its last version, v3 (state 10), is a backdated correction
  valid 2018-05-28..2021-01-06. The version valid in 2026 is v2, state 20 (paid-up).
- **Due dates:** step 1/3/6/12 months for M/Q/H/J. Every due date that falls before the system change of
  2007-08-11 is computed from the one before it with `add_months`, so a missing day sticks (31 -> 28 after a
  February). After the change, due date k = `add_months(anchor, k * step)`, where the anchor is the last due date
  before the change (PH_BEGDT for newer policies). This covers BL10000267 (28th from 2007 on) and BL10002725 /
  BL10004468 (began in 2007 before the change, so they keep the 31st / 30th). Window: (extract, extract + 12 months].
- **Collection date:** UB on the due date, including weekends. LS on the next bank working day, which skips weekends
  and the Ticino holidays.
  - Observed in the train data, where every LS row on these days shifts and none stays: 8 Dec, 25 Dec, 1 Jan, 6 Jan,
    19 Mar, Easter Monday, Ascension, Whit Monday, Corpus Christi and 29 Jun.
  - Working days: Good Friday (2027-03-26, 158 LS rows with lag 0), 24 Dec and 31 Dec.
  - Not observable in this window, because they fall on a weekend: 1 May, 1 Aug, 15 Aug, 1 Nov and 26 Dec. They
    are in the calendar because they are Ticino holidays, not because the data shows them.
  - Easter: `neuron.easter` (Meeus algorithm), new helper. The other tasks do not use it.
- **t5:** t1 is now in `CHECKED`. Each entry has a fourth element: the arguments after `legacy_dir`, computed from
  `targets_dir` (t1: the extract date 2026-06-30; t3 can read its valuation dates there). t5 still finds 10
  outliers, all from t0, because t1 has none in train.
- Kept the import line `from neuron import cents, ...` as it was. `lab/tests/test_score.py` patches it by its text,
  so the new helpers are imported on a second line.

Residuals: none. Open questions:
- The holdout/hidden policies use the same window. A hidden policy that matures in the window would show whether
  due dates stop at PH_ENDDT. No such policy is in NRPOLH (state 10 and PH_ENDDT <= 2027-07-01), so the code has no
  end check.
- The weekend holidays above are not verified.
