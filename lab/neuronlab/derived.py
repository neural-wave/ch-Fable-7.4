"""Pseudo-targets: target files derived from legacy tables, for tasks that have no target values (t7).

NRTAXB has the tax bookings of Neuron without their amounts: which payout was taxed, with which tax types. That is
a label the pipeline can learn from: clustering and trees find when Neuron withheld which taxes, the agent then
writes the amounts from NRTAXR. Each pseudo-target is a CSV in `lab/.cache/derived/`, in the format of the target
files, and runs through every step of the lab like a diagnostic file. It is never scored and the submission never
reads it.
"""
import polars as pl

from . import paths, store

PAYOUTS = (400, 410, 500)  # NRCODE EVTTP: partial withdrawal, full surrender, death claim
# NRCODE TAXTP booked on payouts, in the order a tax depends on another (the surcharge SOL is a share of KST)
PAYOUT_TAXES = ["KST", "SOL", "KIS", "VST", "SOS", "BOL", "BOC"]


def payout_taxes():
    """(policy_id, event_nr) -> one column per tax type: `yes` when NRTAXB books it on the payout event, else `no`.

    One yes/no value per tax keeps each tree small: a single label with every combination of taxes needs more
    leaves than a tree of depth 3 has.
    """
    events = store.load("NREVNT").filter(pl.col("EV_EVTTP").is_in(PAYOUTS))
    booked = store.load("NRTAXB").select("TB_POLNR", "TB_EVTNR", "TB_TAXTP").unique()
    keys = events.select(pl.col("EV_POLNR").alias("policy_id"), pl.col("EV_EVTNR").alias("event_nr"))
    for tax in PAYOUT_TAXES:
        mine = booked.filter(pl.col("TB_TAXTP") == tax).select(
            pl.col("TB_POLNR").alias("policy_id"), pl.col("TB_EVTNR").alias("event_nr"), pl.lit("yes").alias(tax))
        keys = keys.join(mine, on=["policy_id", "event_nr"], how="left").with_columns(pl.col(tax).fill_null("no"))
    return keys.sort("policy_id", "event_nr")


DERIVED = {  # name: (builder, key columns, value columns, grain table, key column -> grain column)
    "t7_payout_taxes": (payout_taxes, ["policy_id", "event_nr"], PAYOUT_TAXES,
                        "NREVNT", {"policy_id": "EV_POLNR", "event_nr": "EV_EVTNR"}),
}


def names():
    return sorted(DERIVED)


def columns(name):
    return DERIVED[name][1], DERIVED[name][2]


def grain(name):
    """The grain of a pseudo-target is known by construction: the table its rows come from."""
    _, _, _, table, mapping = DERIVED[name]
    return {"table": table, "columns": mapping, "missing": 0, "unique": True, "coverage": 1.0,
            "kind": "derived"}


def write(name):
    """Writes the CSV of a pseudo-target when it is missing or older than the legacy tables it reads."""
    path = paths.DERIVED / f"{name}.csv"
    newest = max(p.stat().st_mtime for p in paths.LEGACY.glob("NR*.csv"))
    if not path.exists() or path.stat().st_mtime < newest:
        path.parent.mkdir(parents=True, exist_ok=True)
        DERIVED[name][0]().write_csv(path)
    return path
