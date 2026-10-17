"""The CSV files of the Neuron extract: the legacy tables typed by the data dictionary NRDICT, and the targets.

Every table is read once per run and kept, so the tasks can load the tables they need without a cost.
"""
import csv
import functools
import itertools
import operator
import pathlib

from .days import stored_day
from .fields import convert, number

TEXT = ("C", 0)  # the type of a column that NRDICT does not describe


def read_csv(path, delimiter):
    """All records of a CSV file, the header included."""
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.reader(f, delimiter=delimiter))


@functools.cache
def dictionary(legacy_dir):
    """{(table, column): (type, scale)} read from NRDICT, the data dictionary of Neuron."""
    with open(pathlib.Path(legacy_dir, "NRDICT.csv"), newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f, delimiter=";"))
    return {(r["DC_TABLE"].strip(), r["DC_COLUMN"].strip()): (r["DC_TYPE"].strip(), number(r["DC_SCALE"]))
            for r in rows}


@functools.cache
def table(legacy_dir, name):
    """All rows of a legacy table as dicts of typed values."""
    header, *records = read_csv(pathlib.Path(legacy_dir, f"{name}.csv"), ";")
    types = dictionary(str(legacy_dir))
    columns = [(column.strip(), *types.get((name, column.strip()), TEXT)) for column in header]
    return [typed_row(columns, record) for record in records]


def typed_row(columns, values):
    """One record as {column: typed value}; `columns` are (name, type, scale).

    Records with fewer fields than the header (NRCODE) get None for the missing columns. A date field that
    holds no day adds the stored number as `<column>_RAW`.
    """
    padded = [*values, *itertools.repeat("", len(columns))]
    row = {name: convert(text, kind, scale) for (name, kind, scale), text in zip(columns, padded)}
    impossible_days = {f"{name}_RAW": stored for (name, kind, _), text in zip(columns, values)
                       if (stored := stored_day(kind, text, row[name]))}
    return {**row, **impossible_days}


def read_targets(targets_dir, task, key_types, value_types):
    """{key: value} of a target file, converted column by column, e.g. (str, int) -> (Decimal,).

    A key or value of one column is the value itself, of several columns a tuple. Only t5_outlier_detection
    may call this: every other value is calculated from the legacy tables.
    """
    _, *records = read_csv(pathlib.Path(targets_dir, f"{task}.csv"), ",")
    types = [*key_types, *value_types]
    key = operator.itemgetter(*range(len(key_types)))
    value = operator.itemgetter(*range(len(key_types), len(types)))
    rows = ([parse(text) for parse, text in zip(types, record)] for record in records)
    return {key(row): value(row) for row in rows}
