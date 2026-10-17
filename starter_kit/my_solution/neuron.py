"""Shared helpers of the submission: legacy tables typed by the data dictionary NRDICT, versions, rounding.

Types follow SCHEMA.md and NRDICT:
- C -> trimmed text,
- N(0) -> int, N(s) -> Decimal with s decimals,
- D -> date, where 0 = no date (None), 9999999 = open end and impossible days such as 930931 -> None,
- T -> datetime.
Empty fields are None.
"""
import calendar
import csv
import datetime as dt
import functools
import pathlib
from decimal import ROUND_HALF_UP, Decimal

OPEN_END = dt.date(9999, 12, 31)
CENT = Decimal("0.01")


def day(n):
    """Legacy date CYYMMDD as a date.

    C is 0 for 19xx and 1 for 20xx: `1250131` is 2025-01-31, `970630` is 1997-06-30.
    """
    n = int(n)
    if n == 0:
        return None
    if n == 9999999:
        return OPEN_END
    try:
        return dt.date(1900 + n // 10000, n // 100 % 100, n % 100)
    except ValueError:  # e.g. 31 September in NRPERS.PS_BIRTH
        return None


@functools.cache
def dictionary(legacy_dir):
    """{(table, column): (type, scale)} read from NRDICT, the data dictionary of Neuron."""
    with open(pathlib.Path(legacy_dir) / "NRDICT.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f, delimiter=";"))
    return {(r["DC_TABLE"].strip(), r["DC_COLUMN"].strip()): (r["DC_TYPE"].strip(), int(r["DC_SCALE"].strip() or 0))
            for r in rows}


def convert(text, kind, scale):
    """One legacy field in the Python type of its NRDICT type (see the module docstring)."""
    text = text.strip()
    if not text:
        return None
    if kind == "D":
        return day(text)
    if kind == "T":
        return dt.datetime.strptime(text, "%Y%m%d%H%M%S")
    if kind == "N":
        return Decimal(int(text)).scaleb(-scale) if scale else int(text)
    return text


@functools.cache
def table(legacy_dir, name):
    """All rows of a legacy table as dicts of typed values, read once per run.

    Rows with fewer fields than the header (NRCODE) get None for the missing columns.
    """
    types = dictionary(str(legacy_dir))
    with open(pathlib.Path(legacy_dir) / f"{name}.csv", newline="", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=";")
        header = [h.strip() for h in next(reader)]
        kinds = [types.get((name, h), ("C", 0)) for h in header]
        padding = [""] * len(header)
        return [{h: convert(v, *k) for h, k, v in zip(header, kinds, values + padding)} for values in reader]


def add_months(day, months):
    """The same day of the month, `months` later (or earlier, when negative).

    A day that the new month lacks becomes its last day: 31 January + 1 month is 28 or 29 February, and the
    next month continues from that date, so due dates on the 31st drift to the 28th when computed one by one.
    """
    month = day.month - 1 + months
    year, month = day.year + month // 12, month % 12 + 1
    return dt.date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


def keyed(rows, *key):
    """{key: row} of a table whose key columns are unique, e.g. brokers by BR_BRKNR."""
    return {row[key[0]] if len(key) == 1 else tuple(row[k] for k in key): row for row in rows}


def grouped(rows, *key):
    """{key: [row, ...]}, e.g. all versions of each policy in NRPOLH."""
    groups = {}
    for row in rows:
        groups.setdefault(row[key[0]] if len(key) == 1 else tuple(row[k] for k in key), []).append(row)
    return groups


def latest(versions, alias):
    """The latest version of a versioned row.

    Highest version number <alias>_VRSNR; tables with a validity period but no version number use the
    latest valid-from date <alias>_VLDFR.
    """
    number, start = f"{alias}_VRSNR", f"{alias}_VLDFR"
    return max(versions, key=lambda v: (v.get(number) or 0, v.get(start) or dt.date.min))


def valid(versions, alias, on):
    """The version valid on day `on`.

    SCHEMA.md: a version is valid when VLDFR <= on <= VLDTO (both days included); when several versions are
    valid, the highest version number wins. When none is valid, the latest version is used.
    """
    start, end = f"{alias}_VLDFR", f"{alias}_VLDTO"
    live = [v for v in versions if on and (v[start] or dt.date.min) <= on <= (v[end] or OPEN_END)]
    return latest(live or versions, alias)


def read_targets(targets_dir, task, key_types, value_types):
    """{key: value} of a target file, converted column by column, e.g. (str, int) -> (Decimal,).

    Only t5_outlier_detection may call this: every other value is calculated from the legacy tables.
    """
    with open(pathlib.Path(targets_dir) / f"{task}.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))[1:]
    n = len(key_types)
    result = {}
    for row in rows:
        key = tuple(convert(v) for convert, v in zip(key_types, row[:n]))
        value = tuple(convert(v) for convert, v in zip(value_types, row[n:]))
        result[key[0] if n == 1 else key] = value[0] if len(value) == 1 else value
    return result


def cents(amount, rounding=ROUND_HALF_UP):
    """Amount rounded to the cent; Neuron rounds half up (0.925 -> 0.93)."""
    return Decimal(amount).quantize(CENT, rounding)
