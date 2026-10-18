"""The dates of the tax tables as Neuron stores them, YYMMDD, CYYMMDD or YYYYMMDD, and their validity periods.

The stored open ends 9999999 and 1111231 are no day, like an empty field.
"""
import datetime as dt

NO_DAY = {"", "9999999", "1111231"}
DATE_LENGTHS = (6, 7, 8)


def stored_day(text):
    """The day of a stored date, or None.

    None for an empty field, an open end, a length that is no date format and an impossible date.
    """
    text = str(text).strip()
    if text in NO_DAY or len(text) not in DATE_LENGTHS:
        return None
    try:
        return dt.date(stored_year(text[:-4]), int(text[-4:-2]), int(text[-2:]))
    except ValueError:
        return None


def stored_year(digits):
    """The year of the digits before MMDD.

    YYYY is the year; CYY has the century C (1 is the 2000s, any other the 1900s); YY from 50 to 99 is in the
    1900s, below 50 in the 2000s.
    """
    if len(digits) == 4:
        return int(digits)
    if len(digits) == 3:
        return (2000 if digits[0] == "1" else 1900) + int(digits[1:])
    return (1900 if int(digits) >= 50 else 2000) + int(digits)


def is_valid_on(row, alias, day_):
    """True when <alias>_VLDFR <= day_ <= <alias>_VLDTO.

    A row without a start day is never valid; an empty or open end is open.
    """
    start, end = stored_day(row[f"{alias}_VLDFR"]), stored_day(row[f"{alias}_VLDTO"])
    return start is not None and start <= day_ and (end is None or end >= day_)
