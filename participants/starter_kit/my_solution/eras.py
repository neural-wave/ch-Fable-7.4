"""The two systems behind the export: the old one (COBOL) up to the system conversion, Neuron NG (Java) after it.

They do not calculate everything the same way (the task text), so a convention can be a pair (old system,
Neuron NG), chosen per row by NEW_SYSTEM: whether the row's date is on or after the conversion (event 800).
"""
import polars as pl

from legacy import table

SYSTEM_CONVERSION = 800  # EVTTP: the night Neuron moved from COBOL to Neuron NG
HALF_UP = {"half_up": True, "down": False}
ERAS = {"old": "gt", "new": "ge"}  # the comparison with the conversion day that makes a row Neuron NG's


def conversion_day(legacy_dir):
    """The date of the system conversion."""
    return table(legacy_dir, "NREVNT").filter(pl.col("EV_EVTTP").eq(SYSTEM_CONVERSION))["EV_EFFDT"].min()


def new_system(legacy_dir, day: str, boundary: str = "new") -> pl.Expr:
    """Whether the date column `day` falls to Neuron NG; `boundary` is the system of the conversion day itself."""
    return getattr(pl.col(day), ERAS[boundary])(conversion_day(legacy_dir))


def by_era(choice, convention, flag: str = "NEW_SYSTEM") -> pl.Expr:
    """`convention` of `choice`, or of the old system and of Neuron NG by the row's `flag` for a pair."""
    match choice:
        case (old, new):
            return pl.when(pl.col(flag)).then(convention(new)).otherwise(convention(old))
    return convention(choice)


def half_up(name: str) -> pl.Expr:
    """The rounding flag of a convention name: "half_up" or "down" (cut off)."""
    return pl.lit(HALF_UP[name])
