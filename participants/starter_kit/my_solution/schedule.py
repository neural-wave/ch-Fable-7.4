"""t1: the premium due dates of the year after the extract date, and the day each one is collected.

From the story (tools/detective/llm/003-t1-story.md): the policies that pay regular premiums on the extract date
(state 10, a frequency other than E, in the policy version valid on that day); due dates in whole periods of
the frequency, before maturity.

Found in the data (tools/detective/llm/004-t1-findings.md):
- the schedule starts at the first past due date on or after the system conversion (event 800), not at the
  start date, and goes on in whole periods from there (search t1_next_due_dates/r2-due-search/S1, after the
  decision tree r1-due/T1: the rule was wrong where the past due dates had moved to other days of the month)
- direct debits (LS) are collected on the next business day of canton Ticino, bank transfers (UB) on the due
  date (r2-collection-search/S1, after r1-collection/T1, T2, T4: weekends, Fridays and Ticino holidays)

The choices stay parameters, so the search can test them again on new data:
- `anchor`: where the schedule starts: the start date PH_BEGDT, the first or last past due date of NRPREM, or
  the first past due date on or after the first event of a type (an event type code)
- `chained`: each due date from the previous one, so a day 31 sinks in a short month and stays there, instead
  of whole periods from the anchor
- `shifted`: the payment methods whose money is collected on the next business day instead of the due date
- `calendar`: the holidays that are no business day: none (weekends only) or those of canton Ticino
"""
import datetime as dt

import polars as pl

from calendars import business_days
from legacy import table, versions_on

IN_FORCE = 10  # STATE: in force, premium paying
SYSTEM_CONVERSION = 800  # EVTTP: the night Neuron moved from COBOL to Neuron NG
DIRECT_DEBIT = ("LS",)  # PAYMT
SINGLE_PREMIUM = "E"  # FREQ
MONTHS = {"J": 12, "H": 6, "Q": 3, "M": 1}  # FREQ: yearly, half-yearly, quarterly, monthly
YEARS = range(2025, 2029)


def paying_policies(legacy_dir, day: dt.date) -> pl.DataFrame:
    """The policy versions valid on `day` that pay regular premiums."""
    policies = versions_on(table(legacy_dir, "NRPOLH"), day, "PH_POLNR", "PH_VRSNR")
    return policies.filter(pl.col("PH_STATE").eq(IN_FORCE), pl.col("PH_FREQ").ne(SINGLE_PREMIUM))


def first_due_after(legacy_dir, event_type: int) -> pl.DataFrame:
    """PR_POLNR and ANCHOR: the first past due date on or after the first event of `event_type`."""
    events = table(legacy_dir, "NREVNT").filter(pl.col("EV_EVTTP").eq(event_type)).group_by("EV_POLNR").agg(
        pl.col("EV_EFFDT").min())
    dues = table(legacy_dir, "NRPREM").join(events, left_on="PR_POLNR", right_on="EV_POLNR")
    later = dues.filter(pl.col("PR_DUEDT").ge(pl.col("EV_EFFDT")))
    return later.group_by("PR_POLNR").agg(ANCHOR=pl.col("PR_DUEDT").min())


def anchors(legacy_dir, anchor) -> pl.DataFrame:
    """PR_POLNR and ANCHOR of the policies that have one; the others start at PH_BEGDT."""
    dues = table(legacy_dir, "NRPREM").group_by("PR_POLNR")
    match anchor:
        case "first_due":
            return dues.agg(ANCHOR=pl.col("PR_DUEDT").min())
        case "last_due":
            return dues.agg(ANCHOR=pl.col("PR_DUEDT").max())
        case int():
            return first_due_after(legacy_dir, anchor)
    return dues.agg(ANCHOR=pl.lit(None, pl.Date))


def due_dates(policies: pl.DataFrame, chained: bool) -> pl.DataFrame:
    """One row per policy and due date DUE from its ANCHOR, before maturity.

    Whole periods from the anchor clamp a day 31 to the end of a shorter month only there; chained, the day of
    every due date is the smallest month length met so far.
    """
    period = pl.col("PH_FREQ").replace_strict(MONTHS, return_dtype=pl.Int64)
    years = pl.col("PH_ENDDT").dt.year().sub(pl.col("ANCHOR").dt.year()).add(1)
    steps = policies.with_columns(STEP=pl.int_ranges(0, years.mul(12).floordiv(period))).explode("STEP")
    months = pl.format("{}mo", pl.col("STEP").mul(period))
    month_start = pl.col("ANCHOR").dt.month_start().dt.offset_by(months)
    sunk = pl.min_horizontal(pl.col("ANCHOR").dt.day(), month_start.dt.month_end().dt.day().cum_min().over(
        "PH_POLNR", order_by="STEP"))
    chain = month_start.dt.offset_by(pl.format("{}d", sunk.sub(1)))
    whole = pl.col("ANCHOR").dt.offset_by(months)
    dues = steps.with_columns(DUE=pl.when(pl.lit(chained)).then(chain).otherwise(whole))
    return dues.filter(pl.col("DUE").lt(pl.col("PH_ENDDT")))


def next_due_dates(legacy_dir, extract_date: dt.date, anchor=SYSTEM_CONVERSION, chained: bool = False,
                   shifted: tuple[str, ...] = DIRECT_DEBIT, calendar: str = "TI") -> pl.DataFrame:
    """policy_id, n, due_date and collection_date of the due dates in the year after `extract_date`."""
    policies = paying_policies(legacy_dir, extract_date).join(
        anchors(legacy_dir, anchor), left_on="PH_POLNR", right_on="PR_POLNR", how="left").with_columns(
        ANCHOR=pl.coalesce("ANCHOR", "PH_BEGDT"))
    dues = due_dates(policies, chained)
    year = dues.filter(pl.col("DUE").gt(extract_date), pl.col("DUE").le(pl.lit(extract_date).dt.offset_by("1y")))
    collected = year.join(business_days(calendar, YEARS), left_on="DUE", right_on="DAY", how="left")
    collection = pl.when(pl.col("PH_PAYMT").is_in(shifted)).then(pl.col("NEXT")).otherwise(pl.col("DUE"))
    return collected.select(policy_id="PH_POLNR", n=pl.col("DUE").rank("ordinal").over("PH_POLNR"), due_date="DUE",
                            collection_date=collection)
