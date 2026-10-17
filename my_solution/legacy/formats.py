"""Decoding the old formats of the Neuron export, as declared in the data dictionary NRDICT.

    C  text, padded with blanks on the right: trimmed
    N  integer with `scale` implied decimals: 123456 in N(2) is 1234.56, kept exact as Decimal
    D  date CYYMMDD: 1250131 is 2025-01-31, 970630 is 1997-06-30
"""
import datetime as dt
from decimal import Decimal

import conventions as c


def parts(text):
    """(year, month, day) of a CYYMMDD date as written, also an impossible one (30 Feb).

    C is 0 for 19xx and 1 for 20xx.
    """
    digits = f"{int(text):07d}"
    return int(f"{c.CENTURIES[digits[0]]}{digits[1:3]}"), int(digits[3:5]), int(digits[5:])


def day(text):
    """Legacy date CYYMMDD as a date.

    0 means no date and 9999999 an open end. Impossible dates of the export (30 Feb 1971)
    become None, so that no rule silently invents a date the system never had.
    """
    number = int(text)
    if number in c.SPECIAL_DATES:
        return c.SPECIAL_DATES[number]
    try:
        return dt.date(*parts(text))
    except ValueError:
        return None


def converter(kind, scale):
    """The function that turns the text of an NRDICT column of type `kind` into a value."""
    number = (lambda text: Decimal(f"{text}E-{scale}")) if scale else int
    return {"D": day, "N": number}.get(kind, str.strip)
