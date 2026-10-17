"""The timeline of one entity, e.g. a policy: every row of the export that refers to it, in the order of its dates.

The tables come from the relation graph (`schema.relations`): every table with a relation to the entity's table
gives its rows of the entity, and the tables they refer to give the context (the insured person, the broker,
the product). A row is dated by its first date column in the order of the dictionary.
"""
import pathlib

import polars as pl

from detective.load import LEGACY, columns, load
from detective.schema import relations

ENTITY = "NRPOLH"  # the policy header: the entity of most targets


def referring(table: str, folder: pathlib.Path) -> list[tuple[str, str, str]]:
    """(table, column, referenced column) of the single column relations to `table`."""
    edges = relations(folder).filter(pl.col("REFERENCED").eq(table), pl.col("COLUMNS").list.len().eq(1))
    return [(name, cols[0], referenced[0]) for name, cols, _, referenced in edges.iter_rows()]


def referred(table: str, folder: pathlib.Path) -> list[tuple[str, str, str]]:
    """(referenced table, column, referenced column) of the single column relations from `table`."""
    edges = relations(folder).filter(pl.col("TABLE").eq(table), pl.col("COLUMNS").list.len().eq(1))
    return [(other, cols[0], referenced[0]) for _, cols, other, referenced in edges.iter_rows()]


def described_rows(table: str, rows: pl.DataFrame, folder: pathlib.Path) -> pl.DataFrame:
    """TABLE, DATE and ROW: each row dated by its first date column and written as `COLUMN=value` pairs."""
    dates = columns(table, folder).filter(pl.col("TYPE").eq("D"))["COLUMN"].to_list()
    date = pl.coalesce(dates) if dates else pl.lit(None, pl.Date)
    text = pl.concat_str([pl.format(f"{column}={{}}", pl.col(column)) for column in rows.columns], separator="  ",
                         ignore_nulls=True)
    return rows.select(TABLE=pl.lit(table), DATE=date, ROW=text)


def timeline(key: str, table: str = ENTITY, folder: pathlib.Path = LEGACY) -> pl.DataFrame:
    """TABLE, DATE, ROW of every row that refers to `key` of `table`; the context rows (no date) first."""
    own = [(table, column, column) for column in {referenced for _, _, referenced in referring(table, folder)}]
    parts = [(name, load(name, folder).filter(pl.col(column).eq(key))) for name, column, _ in
             [*own, *referring(table, folder)]]
    context = [(other, load(other, folder).join(rows.select(pl.col(column).alias(target)).unique(), on=target))
               for name, rows in parts for other, column, target in referred(name, folder)]
    described = [described_rows(name, rows, folder) for name, rows in [*parts, *context] if rows.height]
    return pl.concat(described).unique(maintain_order=True).sort("DATE", nulls_last=False, maintain_order=True)
