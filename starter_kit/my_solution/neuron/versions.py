"""Versioned rows: the validity period <alias>_VLDFR to <alias>_VLDTO and the version number <alias>_VRSNR."""
import datetime as dt

from .days import OPEN_END


def is_valid_on(row, alias, on):
    """True when VLDFR <= on <= VLDTO: both days are included, and an empty end is open."""
    return (row[f"{alias}_VLDFR"] or dt.date.min) <= on <= (row[f"{alias}_VLDTO"] or OPEN_END)


def first_valid(rows, alias, on):
    """The first row in the order of the table that is valid on `on`, or None."""
    return next((row for row in rows if is_valid_on(row, alias, on)), None)


def latest(versions, alias):
    """The latest version of a versioned row.

    Highest version number; tables with a validity period but no version number use the latest valid-from date.
    """
    number, start = f"{alias}_VRSNR", f"{alias}_VLDFR"
    return max(versions, key=lambda v: (v.get(number) or 0, v.get(start) or dt.date.min))


def valid(versions, alias, on):
    """The version valid on day `on`.

    SCHEMA.md: when several versions are valid, the highest version number wins. When none is valid (or there
    is no day), the latest version is used.
    """
    live = [v for v in versions if on and is_valid_on(v, alias, on)]
    return latest(live or versions, alias)
