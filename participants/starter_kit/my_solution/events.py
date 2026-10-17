"""The events of a policy (NREVNT). Reversed events and technical corrections can be ignored (the task text), so
the rules leave out the events a reversal cancelled and the corrections themselves.
"""
import polars as pl

from legacy import table

SURRENDER = 410  # EVTTP: full surrender
DEATH = 500  # EVTTP: death claim
REVERSAL = 900  # EVTTP: cancels the event EV_REVNR
TECHNICAL_CORRECTION = 990  # EVTTP


def ignored(legacy_dir) -> pl.DataFrame:
    """EV_POLNR and EV_EVTNR of the events that a reversal cancelled, and of the technical corrections."""
    events = table(legacy_dir, "NREVNT")
    cancelled = events.filter(pl.col("EV_EVTTP").eq(REVERSAL)).select("EV_POLNR", EV_EVTNR="EV_REVNR")
    corrections = events.filter(pl.col("EV_EVTTP").eq(TECHNICAL_CORRECTION)).select("EV_POLNR", "EV_EVTNR")
    return pl.concat([cancelled, corrections])


def counted(legacy_dir) -> pl.DataFrame:
    """The events that count: NREVNT without the ignored ones."""
    return table(legacy_dir, "NREVNT").join(ignored(legacy_dir), on=["EV_POLNR", "EV_EVTNR"], how="anti")
