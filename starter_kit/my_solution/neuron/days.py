"""The legacy date format of Neuron: numbers CYYMMDD, with special values for no date and an open end."""
import calendar
import datetime as dt

OPEN_END = dt.date(9999, 12, 31)
SPECIAL_DAYS = {0: None, 9999999: OPEN_END}  # no date, open end


def day(n, month_end=False):
    """Legacy date CYYMMDD as a date.

    C is 0 for 19xx and 1 for 20xx: `1250131` is 2025-01-31, `970630` is 1997-06-30. An impossible day such as
    31 September (NRPERS.PS_BIRTH) is None, or the last day of its month with `month_end`.
    """
    n = int(n)
    if n in SPECIAL_DAYS:
        return SPECIAL_DAYS[n]
    years, month_day = divmod(n, 10000)
    (month, day_), year = divmod(month_day, 100), 1900 + years
    last = calendar.monthrange(year, month)[1]
    return dt.date(year, month, min(day_, last)) if day_ <= last or month_end else None


def stored_day(kind, text, value):
    """The number stored in a date field that is no day, such as 930931; 0 for every other field.

    `kind` is the NRDICT type of the field, `text` its content and `value` its converted value. The typed row keeps the number in
    `<column>_RAW`, like the lab store, so a rule can still read the month of an impossible day.
    """
    return int(text or 0) if kind == "D" and value is None else 0
