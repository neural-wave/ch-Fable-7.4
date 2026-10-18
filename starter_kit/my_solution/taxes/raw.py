"""The tax tables as CSV rows of strings, and the NRTAXB bookings grouped as the t7 tasks read them."""
import csv
import functools
import pathlib
from collections import defaultdict

from .days import stored_day


def read_rows(legacy_dir, name):
    """The rows of the table NR<name> as dicts of strings, one by one.

    NRBOOK has millions of rows: it is streamed, never kept.
    """
    with open(pathlib.Path(legacy_dir, f"NR{name}.csv"), encoding="utf-8") as f:
        yield from csv.DictReader(f, delimiter=";")


@functools.cache
def raw_table(legacy_dir, name):
    """All rows of the table NR<name> as dicts of strings.

    Read once per folder and table and shared by every caller: the rows must not be changed.
    """
    return list(read_rows(legacy_dir, name))


def grouped_bookings(legacy_dir, key_of):
    """{key: [booking, ...]} of the NRTAXB bookings in the order of the table.

    `key_of` gives the key of a booking; a booking without a key (None) is left out.
    """
    groups = defaultdict(list)
    for booking in raw_table(legacy_dir, "TAXB"):
        key = key_of(booking)
        if key:
            groups[key].append(booking)
    return groups


def booking_days(bookings, tax_type):
    """The days (TB_EFFDT) of the bookings of `tax_type`, in their order; the bookings without a day are left out."""
    days = (stored_day(booking["TB_EFFDT"]) for booking in bookings if booking["TB_TAXTP"] == tax_type)
    return list(filter(None, days))
