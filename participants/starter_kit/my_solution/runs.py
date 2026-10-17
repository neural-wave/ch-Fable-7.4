"""t3: the dates of the monthly charge runs, made from the policy (tools/detective/llm/011-t3-runs-story.md).

Neuron takes its charges on every monthly anniversary of the start date (the glossary: the same day in every
month; a month without that day has it on its last day) until the policy ends by maturity, surrender or death.
NREVNT keeps the runs as events 300, but a new system has to know them before they happen, so here they are made
from the start date, the premiums and the customer orders; the events are only the diagnostic that checks them.

The choices stay parameters of `charge_dates`:
- `first`: the first run: the first monthly anniversary after the start date ("start"), or the first one on or
  after the trade date of the first premium ("invested") or after it ("after_invested")
- `ending`: the run on the day the policy ends by surrender or death: taken ("on") or not ("before")
- `maturity`: the run on the maturity date: taken ("on") or not ("before")
"""
import polars as pl

from events import DEATH, SURRENDER, counted
from legacy import table

ENDINGS = {"on": "le", "before": "lt"}


def ends(legacy_dir) -> pl.DataFrame:
    """PH_POLNR and ENDED, the date of the surrender or death claim that ended the policy."""
    ending = counted(legacy_dir).filter(pl.col("EV_EVTTP").is_in([SURRENDER, DEATH]))
    return ending.group_by(PH_POLNR="EV_POLNR").agg(ENDED=pl.col("EV_EFFDT").min())


def anniversaries(policies: pl.DataFrame, until) -> pl.DataFrame:
    """PH_POLNR and RUN for every monthly anniversary of PH_BEGDT after it, up to the date `until`."""
    months = pl.int_ranges(1, pl.lit(until).dt.year().sub(pl.col("PH_BEGDT").dt.year()).add(1).mul(12))
    spread = policies.select("PH_POLNR", "PH_BEGDT", MONTHS=months).explode("MONTHS")
    days = spread.with_columns(RUN=pl.col("PH_BEGDT").dt.offset_by(pl.format("{}mo", pl.col("MONTHS"))))
    return days.filter(pl.col("RUN").le(until)).select("PH_POLNR", "RUN")


def charge_dates(legacy_dir, premiums: pl.DataFrame, until, first: str = "after_invested", ending: str = "before",
                 maturity: str = "before") -> pl.DataFrame:
    """BK_POLNR and RUN of every charge run up to the date `until`; `premiums` are the premium bookings (BK_POLNR,
    BK_TRDDT)."""
    policies = table(legacy_dir, "NRPOLH").group_by("PH_POLNR").agg(pl.col("PH_BEGDT", "PH_ENDDT").last())
    invested = premiums.group_by(PH_POLNR="BK_POLNR").agg(INVESTED=pl.col("BK_TRDDT").min())
    known = policies.join(invested, on="PH_POLNR", how="left").join(ends(legacy_dir), on="PH_POLNR", how="left")
    dated = anniversaries(policies, until).join(known, on="PH_POLNR")
    starts = {"start": pl.lit(True), "invested": pl.col("RUN").ge(pl.col("INVESTED")),
              "after_invested": pl.col("RUN").gt(pl.col("INVESTED"))}
    open_end = getattr(pl.col("RUN"), ENDINGS[ending])(pl.col("ENDED")).fill_null(True)
    in_force = getattr(pl.col("RUN"), ENDINGS[maturity])(pl.col("PH_ENDDT"))
    return dated.filter(starts[first], open_end, in_force).select(BK_POLNR="PH_POLNR", RUN="RUN")
