"""Bookings made by the rules, next to the bookings of the export.

The rules make the premium and charge bookings themselves; NRBOOK has the same bookings with their dates but
without amounts. A booking is the same when policy, type, fund, pot and trade date agree (a key of NRBOOK), so
`with_ids` gives a made booking the BK_BOOKID of its twin, and the target t3_booking can judge its amounts.
"""
import pathlib

import polars as pl

from detective.diagnostics import marked
from detective.load import LEGACY, load

SAME = ["BK_POLNR", "BK_BKTYP", "BK_FNDID", "BK_POTCD", "BK_TRDDT"]


def with_ids(made: pl.DataFrame, legacy: pathlib.Path = LEGACY) -> pl.DataFrame:
    """`made` with BK_BOOKID of the NRBOOK booking with the same key (null for a booking NRBOOK does not have)."""
    ids = load("NRBOOK", legacy).select(*SAME, "BK_BOOKID")
    return made.join(ids, on=SAME, how="left")


def as_target(made: pl.DataFrame, legacy: pathlib.Path = LEGACY) -> pl.DataFrame:
    """The made bookings in the columns of the target t3_booking."""
    return with_ids(made, legacy).drop_nulls("BK_BOOKID").select(
        booking_id="BK_BOOKID", policy_id="BK_POLNR", booking_type="BK_BKTYP", amount_pc="BK_AMTPC",
        price="BK_PRICE", units="BK_UNITS")


def presence(candidates: pl.DataFrame, made: pl.DataFrame, legacy: pathlib.Path = LEGACY) -> tuple[pl.DataFrame, pl.DataFrame]:
    """(export, rules) of `diagnostics.marked` for bookings: booked when NRBOOK or `made` has the candidate."""
    names = dict(zip(SAME, ["policy_id", "booking_type", "fund_id", "pot_code", "trade_date"], strict=True))
    return marked(candidates, load("NRBOOK", legacy), made, names, "booked")
