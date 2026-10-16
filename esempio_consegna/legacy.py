"""Reading the tables of the Neuron export.

One generic loader converts every column by the type the data dictionary NRDICT declares
for it (see formats.py), so that no table needs reading code of its own.
"""
import functools
import pathlib

import polars as pl

import conventions as c
import formats


def read(legacy_dir, name, column=None, values=()):
    """Raw text rows of one export file: `;`-separated, header row, empty fields are None.

    With `column`, only the rows whose trimmed value is in `values` are kept, before any
    conversion and while the file is scanned: the way to read the few customer orders among
    the 6.8 million NRBOOK rows without holding the whole file in memory.
    """
    frame = pl.scan_csv(pathlib.Path(legacy_dir, f"{name}.csv"), separator=c.SEPARATOR, infer_schema_length=0)
    keep = pl.col(column).str.strip_chars().is_in(values) if column else pl.lit(True)
    return frame.filter(keep).collect().iter_rows(named=True)


@functools.cache
def dictionary(legacy_dir):
    """{(table, column): (type, scale)} from NRDICT; unknown columns are read as text."""
    rows = read(legacy_dir, "NRDICT")
    return {(r["DC_TABLE"].strip(), r["DC_COLUMN"].strip()): (r["DC_TYPE"].strip(), int(r["DC_SCALE"] or 0))
            for r in rows}


@functools.cache
def table(legacy_dir, name, column=None, values=()):
    """All rows of a legacy table (or those selected by `column`) as dicts of typed values.

    An empty field means no value and becomes None. Tables are read once and cached.
    """
    types, rows = dictionary(legacy_dir), list(read(legacy_dir, name, column, values))
    convert = {column: formats.converter(*types.get((name, column), ("C", 0))) for column in next(iter(rows), {})}
    return [{k: convert[k](v) if v else None for k, v in row.items()} for row in rows]
