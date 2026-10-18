"""The fields of the extract in the Python type of their NRDICT type.

Types follow SCHEMA.md and NRDICT:
- C -> trimmed text,
- N(0) -> int, N(s) -> Decimal with s decimals,
- D -> date (see `days.py`): 0 = no date (None), 9999999 = open end, an impossible day such as 930931 -> None,
- T -> datetime.
Empty fields are None.
"""
import datetime as dt
from decimal import Decimal

from .days import day


def number(text):
    """A whole number field, 0 when it is empty."""
    return int(text.strip() or 0)


def decimal(text, scale):
    """An N field: an int without decimals, else a Decimal with `scale` decimals (12345 with scale 2 is 123.45)."""
    return Decimal(int(text)).scaleb(-scale) if scale else int(text)


PARSERS = {  # NRDICT DC_TYPE: parser(text, scale); C and any other type stay text
    "D": lambda text, scale: day(text),
    "T": lambda text, scale: dt.datetime.strptime(text, "%Y%m%d%H%M%S"),
    "N": decimal,
}


def convert(text, kind, scale):
    """One field in the Python type of its NRDICT type (see the module docstring)."""
    text = text.strip()
    return PARSERS.get(kind, lambda text, scale: text)(text, scale) if text else None
