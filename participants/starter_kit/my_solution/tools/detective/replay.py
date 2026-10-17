"""Replay the fund accounting with the units Neuron booked, to check one step of a calculation at a time.

A charge run takes a share of the value of every fund and pot. Its formula can only be checked on the units that
were there before it, and a rule that is wrong in one run would make every later run wrong too. The diagnostic
target t3_booking has the units of the premium and charge bookings, NRBOOK has those of the customer orders: with
both, the holdings before any event are known exactly (teacher forcing), and every run can be checked on its own.
Bookings of reversed events and of technical corrections do not count (the task text: they "can be ignored"),
so they are left out here as well.
"""
import functools
import pathlib

import polars as pl

from detective.load import LEGACY, load
from detective.targets import TARGETS, target

REVERSAL = 900  # EVTTP
TECHNICAL_CORRECTION = 990  # EVTTP


def ignored_events(legacy: pathlib.Path = LEGACY) -> pl.DataFrame:
    """BK_POLNR and BK_EVTNR of the events that a reversal cancelled, and of the technical corrections."""
    events = load("NREVNT", legacy)
    cancelled = events.filter(pl.col("EV_EVTTP").eq(REVERSAL)).select(BK_POLNR="EV_POLNR", BK_EVTNR="EV_REVNR")
    corrections = events.filter(pl.col("EV_EVTTP").eq(TECHNICAL_CORRECTION)).select(BK_POLNR="EV_POLNR",
                                                                                     BK_EVTNR="EV_EVTNR")
    return pl.concat([cancelled, corrections])


@functools.cache
def known_units(legacy: pathlib.Path = LEGACY, folder: pathlib.Path = TARGETS) -> pl.DataFrame:
    """Every counted booking of the policies with targets, with BK_UNITS: from t3_booking where NRBOOK has none."""
    booked = target("t3_booking", folder).select(BK_BOOKID="booking_id", UNITS="units")
    policies = target("t3_booking", folder).select(BK_POLNR="policy_id").unique()
    counted = load("NRBOOK", legacy).join(policies, on="BK_POLNR", how="semi").join(ignored_events(legacy),
                                                                       on=["BK_POLNR", "BK_EVTNR"], how="anti")
    filled = counted.join(booked, on="BK_BOOKID", how="left").with_columns(
        BK_UNITS=pl.coalesce("BK_UNITS", "UNITS")).drop("UNITS")
    return filled.filter(pl.col("BK_UNITS").is_not_null())


STEP = 10_000_000  # more than any event number: a day before all events of the next day


def ordering(order: str, day: str, event: str) -> pl.Expr:
    """The position of a booking or an event in the order `order`: by event number ("event"), by the day and then
    the event number ("day"), or by the day alone, every event of a day before its bookings ("day_strict")."""
    days = pl.col(day).cast(pl.Int64).mul(STEP)
    positions = {"event": pl.col(event), "day": days.add(pl.col(event)), "day_strict": days}
    return positions[order]


def holdings_before(events: pl.DataFrame, legacy: pathlib.Path = LEGACY, order: str = "event") -> pl.DataFrame:
    """For every event (BK_POLNR, BK_EVTNR, RUN its date) of `events`: BK_FNDID, BK_POTCD and UNITS, the units of
    every fund and pot held before it in the order `order` (`ordering`, bookings by their trade date), positive
    holdings only."""
    pot = ["BK_POLNR", "BK_FNDID", "BK_POTCD"]
    keyed = known_units(legacy).with_columns(AT=ordering(order, "BK_TRDDT", "BK_EVTNR"))
    units = keyed.group_by(*pot, "AT").agg(pl.col("BK_UNITS").sum()).sort("AT")
    running = units.with_columns(UNITS=pl.col("BK_UNITS").cum_sum().over(pot, order_by="AT")).select(
        *pot, BOOKED="AT", UNITS="UNITS")
    marked = events.select("BK_POLNR", "BK_EVTNR", AT=ordering(order, "RUN", "BK_EVTNR")).unique()
    pairs = marked.join(running.select(pot).unique(), on="BK_POLNR")
    held = pairs.sort("AT").join_asof(running, left_on="AT", right_on="BOOKED", by=pot, strategy="backward",
                                      allow_exact_matches=False)
    return held.filter(pl.col("UNITS").gt(0)).select(*pot, "BK_EVTNR", "UNITS")
