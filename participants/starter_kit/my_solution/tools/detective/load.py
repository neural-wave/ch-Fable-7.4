"""Load a legacy export: one CSV file per table, typed by the data dictionary that the export carries.

The dictionary (NRDICT here) has one row per column with its type code, length and scale. Each type code has a
decoder (`DECODERS`), so a new export needs a new dictionary name or new decoders, not new code:

- C text, padded with blanks on the right
- N integer with `scale` implied decimals; kept as the stored integer, so all arithmetic stays exact
- D date as CYYMMDD (C = 0 for 19xx, 1 for 20xx), 0 = no date, 9999999 = open end
- T timestamp as YYYYMMDDHHMMSS

The first load of a table writes a parquet copy to `cache/detective/<version>/`; the version is the time of the
newest CSV file, so a changed export gets a new folder.
"""
import datetime as dt
import functools
import pathlib

import polars as pl

ROOT = pathlib.Path(__file__).resolve().parents[5]
LEGACY = ROOT / "participants" / "legacy"
CACHE = ROOT / "cache" / "detective"
DICTIONARY = "NRDICT"
SEPARATOR = ";"
OPEN_END = dt.date(9999, 12, 31)


def text(column: str) -> pl.Expr:
    """A C column: the blanks of the fixed length cut off."""
    return pl.col(column).str.strip_chars_end()


def integer(column: str) -> pl.Expr:
    """An N column: the stored integer, its implied decimals kept (see `scale`)."""
    return pl.col(column).str.strip_chars().cast(pl.Int64, strict=False)


def date(column: str) -> pl.Expr:
    """A D column: CYYMMDD -> date; 0 -> null, 9999999 -> OPEN_END, an impossible day (31.11.) -> null."""
    stored = integer(column)
    year = stored.floordiv(1_000_000).mul(100).add(stored.floordiv(10_000).mod(100)).add(1900)
    iso = pl.format("{}-{}-{}", year, stored.floordiv(100).mod(100).cast(pl.String).str.zfill(2),
                    stored.mod(100).cast(pl.String).str.zfill(2))
    calendar = iso.str.to_date("%Y-%m-%d", strict=False)
    return pl.when(stored.eq(9_999_999)).then(pl.lit(OPEN_END)).when(stored.eq(0)).then(None).otherwise(calendar)


def timestamp(column: str) -> pl.Expr:
    """A T column: YYYYMMDDHHMMSS -> datetime."""
    return pl.col(column).str.strip_chars().str.to_datetime("%Y%m%d%H%M%S", strict=False)


DECODERS = {"C": text, "N": integer, "D": date, "T": timestamp}


def version(folder: pathlib.Path = LEGACY) -> str:
    """The version of an export: the modification time of its newest CSV file."""
    newest = max(path.stat().st_mtime for path in folder.glob("*.csv"))
    return dt.datetime.fromtimestamp(newest).strftime("%Y%m%d-%H%M%S")


def raw(name: str, folder: pathlib.Path = LEGACY) -> pl.DataFrame:
    """Table `name` as stored: every column text, short rows filled up with nulls."""
    return pl.read_csv(folder / f"{name}.csv", separator=SEPARATOR, infer_schema=False, truncate_ragged_lines=True)


@functools.cache
def dictionary(folder: pathlib.Path = LEGACY) -> pl.DataFrame:
    """The data dictionary: TABLE, COLUMN, TYPE, LENGTH, SCALE, DESCRIPTION, one row per column of the export."""
    stored = raw(DICTIONARY, folder)
    names = dict(zip(stored.columns, ["TABLE", "COLUMN", "TYPE", "LENGTH", "SCALE", "DESCRIPTION"], strict=True))
    return stored.rename(names).with_columns(text("TABLE"), text("COLUMN"), text("TYPE"), integer("LENGTH"),
                                             integer("SCALE").fill_null(0), text("DESCRIPTION"))


def columns(name: str, folder: pathlib.Path = LEGACY) -> pl.DataFrame:
    """The dictionary rows of table `name`."""
    return dictionary(folder).filter(pl.col("TABLE").eq(name))


def tables(folder: pathlib.Path = LEGACY) -> list[str]:
    """The tables of the export, as the dictionary lists them."""
    return dictionary(folder)["TABLE"].unique(maintain_order=True).to_list()


def decoded(name: str, folder: pathlib.Path = LEGACY) -> pl.DataFrame:
    """Table `name` with every column decoded by its type code; a column the dictionary misses stays text."""
    types = dict(columns(name, folder).select("COLUMN", "TYPE").iter_rows())
    stored = raw(name, folder)
    return stored.with_columns(DECODERS[types[column]](column).alias(column) for column in stored.columns
                               if column in types)


def load(name: str, folder: pathlib.Path = LEGACY) -> pl.DataFrame:
    """Table `name`, decoded, from the parquet cache of its export version (written on the first load)."""
    path = CACHE / version(folder) / f"{name}.parquet"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        decoded(name, folder).write_parquet(path)
    return pl.read_parquet(path)


def kept(name: str, compute, folder: pathlib.Path = LEGACY) -> pl.DataFrame:
    """A frame derived from the export: computed by `compute()` once per export version, then read as parquet."""
    path = CACHE / version(folder) / f"{name}.parquet"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        compute().write_parquet(path)
    return pl.read_parquet(path)


def scale(name: str, column: str, folder: pathlib.Path = LEGACY) -> int:
    """The implied decimals of an N column: 2 for amounts in cents, 6 for rates, prices and units."""
    rows = columns(name, folder).filter(pl.col("COLUMN").eq(column))
    return rows["SCALE"].item()
