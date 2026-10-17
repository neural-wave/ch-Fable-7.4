"""A target as the discovery loop sees it: its file, its keys, its values and the export rows it describes.

A `TaskSpec` is all the loop needs to know about a new target. `spec_for` writes it from the target file alone:
the key columns are the columns before the first value column, and the anchor is the export table whose key
holds the key values of the target (`anchor_of`): commissions per premium item -> NRPREM (PR_POLNR, PR_DUENR).
Values alone can mislead (due numbers 1, 2, 3 fit into event numbers too), so a column must also be named like
the target column, in its abbreviation or its description (`likeness`). A key column that no table holds, e.g. a
valuation date, stays a parameter of the rule.
"""
import dataclasses
import difflib
import itertools
import pathlib

import polars as pl

from detective.load import LEGACY, columns, load, tables
from detective.schema import SKIPPED, abbreviation, keyed, keys
from detective.targets import TARGETS, target

FIT = 0.999  # the share of the distinct target keys that a table column must hold
ALIKE = 0.5  # the least likeness of the names of a target column and its export column


@dataclasses.dataclass(frozen=True)
class TaskSpec:
    """A target file and the export rows it describes."""

    target: str  # the target file without .csv
    keys: tuple[str, ...]  # its key columns
    values: tuple[str, ...]  # its value columns
    anchor: str | None = None  # the export table with one row per target row (or per entity of the target)
    anchor_keys: tuple[str, ...] = ()  # the columns of `anchor` that match the first `keys`
    folder: pathlib.Path = TARGETS  # where the target file is: the targets, or the diagnostics made from the export

    def frame(self, folder: pathlib.Path | None = None) -> pl.DataFrame:
        """The target rows."""
        return target(self.target, folder or self.folder)

    def joined(self, folder: pathlib.Path | None = None, legacy: pathlib.Path = LEGACY) -> pl.DataFrame:
        """The target rows with the columns of their anchor row."""
        rows = self.frame(folder)
        anchored = self.keys[:len(self.anchor_keys)]
        anchor = load(self.anchor, legacy).unique(list(self.anchor_keys), keep="last") if self.anchor else None
        return rows.join(anchor, left_on=list(anchored), right_on=list(self.anchor_keys), how="left",
                         coalesce=False) if self.anchor else rows


def holders(values: pl.Series, legacy: pathlib.Path) -> list[tuple[str, str]]:
    """(table, column) of the export columns of the same type that hold almost all distinct `values`."""
    distinct = values.drop_nulls().unique()
    found = []
    for table in [name for name in tables(legacy) if name not in SKIPPED]:
        frame = load(table, legacy)
        same = [column for column, dtype in frame.schema.items() if dtype == values.dtype]
        found.extend((table, column) for column in same if distinct.is_in(frame[column].unique()).mean() >= FIT)
    return found


def likeness(name: str, table: str, column: str, legacy: pathlib.Path) -> float:
    """How alike a target column name is to an export column: its abbreviation or its description, 0 to 1."""
    description = columns(table, legacy).filter(pl.col("COLUMN").eq(column))["DESCRIPTION"].item()
    plain = name.replace("_", "").lower()
    spellings = [abbreviation(column).lower(), description.replace(" ", "").lower()]
    return max(difflib.SequenceMatcher(None, plain, spelling).ratio() for spelling in spellings)


def held(rows: pl.DataFrame, names: tuple[str, ...], table: str, cols: tuple[str, ...], legacy: pathlib.Path) -> float:
    """The share of the distinct target key tuples `names` that occur as rows of `cols` in `table`."""
    wanted = rows.select(names).unique()
    found = load(table, legacy).select(cols).unique().rename(dict(zip(cols, names, strict=True)))
    return wanted.join(found, on=list(names), how="semi").height / wanted.height


def anchor_of(rows: pl.DataFrame, key_columns: tuple[str, ...], legacy: pathlib.Path = LEGACY):
    """(table, columns) of the export table whose key holds the longest leading part of the target keys.

    Every column must be named alike (ALIKE), and the table must hold the key tuples, not only each value. A
    table whose columns are a key without versions wins over a versioned one, then the names most alike.
    """
    for size in range(len(key_columns), 0, -1):
        leading = key_columns[:size]
        candidates = [[(table, column) for table, column in holders(rows[name], legacy)
                       if likeness(name, table, column, legacy) >= ALIKE] for name in leading]
        tables_found = set.intersection(*[{table for table, _ in found} for found in candidates])
        options = [(table, combo) for table in sorted(tables_found) for combo in itertools.product(
            *[[column for name, column in found if name == table] for found in candidates]) if len(set(combo)) == size]
        def rank(option):
            exact = set(option[1]) in [set(key) for key in keys(option[0], legacy)]
            alike = sum(likeness(name, option[0], column, legacy) for name, column in zip(leading, option[1]))
            return (not exact, -alike)
        fitting = [option for option in options if keyed(*option, legacy) and held(rows, leading, *option, legacy) >= FIT]
        ranked = sorted(fitting, key=rank)
        if ranked:
            return ranked[0]
    return None, ()


def spec_for(name: str, values: tuple[str, ...], folder: pathlib.Path = TARGETS,
             legacy: pathlib.Path = LEGACY) -> TaskSpec:
    """The TaskSpec of a target file whose value columns are `values`; the columns before them are its keys."""
    rows = target(name, folder)
    key_columns = tuple(rows.columns[:rows.columns.index(values[0])])
    anchor, anchor_keys = anchor_of(rows, key_columns, legacy)
    return TaskSpec(name, key_columns, values, anchor, tuple(anchor_keys), folder)
