"""Exploration loader: the tables of `legacy.table`, decoded into readable types and cached as parquet.

`legacy.table`, the reader of the submission, keeps the stored integers that exact money needs. For exploring,
`load` decodes them by their type in the data dictionary NRDICT:

- `N` numbers with `DC_SCALE` implied decimals become floats (`N(2)` 123456 -> 1234.56)
- `D` dates `CYYMMDD` become dates (`1250131` -> 2025-01-31, `970630` -> 1997-06-30); `0` and impossible dates
  (the export has e.g. 31 November) become null, the open end `9999999` becomes 9999-12-31
- `T` timestamps `YYYYMMDDHHMMSS` become datetimes

The data folder is `$NEURON_DATA`, by default the `participants` folder that contains this hand-in.
"""
import datetime as dt
import functools
import os
import pathlib

import polars as pl

import legacy

HAND_IN = pathlib.Path(__file__).resolve().parents[2]  # my_solution, from my_solution/tools/neuron/load.py
DATA = pathlib.Path(os.environ.get("NEURON_DATA", HAND_IN.parents[1]))  # participants: legacy/, targets/
LEGACY = DATA.joinpath("legacy")
CACHE = DATA.parent.joinpath("cache")
EXTRACT_DATE = dt.date(2026, 6, 30)  # the day of the export
OPEN_END = dt.date(9999, 12, 31)
CENTURY = 19_000_000  # CYYMMDD + 19000000 = YYYYMMDD: C is 0 for 19xx and 1 for 20xx


@functools.cache
def dictionary() -> pl.DataFrame:
    """The data dictionary NRDICT itself.

    One row per column with its table, type, length, scale (implied decimals) and description.
    """
    return legacy.read(LEGACY, "NRDICT")


def column_types() -> dict[str, tuple[str, int]]:
    """{column: (type, scale)} of every column in NRDICT, e.g. {"PR_AMTRC": ("N", 2)}.

    Text, dates and timestamps have no scale in NRDICT; they get 0.
    """
    scale = pl.col("DC_SCALE").cast(pl.Int64).fill_null(0)
    return {col: (kind, digits) for col, kind, digits in dictionary().select("DC_COLUMN", "DC_TYPE", scale).iter_rows()}


def tables(*excluded: str) -> list[str]:
    """Names of the tables in the export folder (e.g. "NRPOLH"), sorted, without the tables `excluded`.

    The metadata tables NRDICT and NRCODE are often excluded: they describe columns and codes, not policies.
    """
    return sorted({path.stem for path in LEGACY.glob("NR*.csv")}.difference(excluded))


@functools.cache
def cache_dir() -> pathlib.Path:
    """Folder for the files derived from the export, named after the modification time of its newest CSV.

    A changed export gets a new folder, so a derived file is never older than its source and needs no freshness
    check. Delete `CACHE` after changing a decoder.
    """
    version = max(path.stat().st_mtime_ns for path in LEGACY.glob("NR*.csv"))
    folder = CACHE.joinpath(str(version))
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def scaled(value: pl.Expr, scale: int) -> pl.Expr:
    """A stored `N` integer with `scale` implied decimals as a float, rounded to its decimals.

    Integers (scale 0) stay integers, since they are counters and keys like PH_VRSNR.
    """
    if scale:
        return value.truediv(pl.lit(10).pow(scale)).round(scale)
    return value


def decode(col: str, kind: str, scale: int) -> pl.Expr:
    """Expression that decodes the stored value of column `col` by its NRDICT type `kind` and `scale`.

    The decoders of all types are built and the one of `kind` is used; text stays as it is.
    """
    value = pl.col(col)
    date = value.add(CENTURY).cast(pl.String).str.to_date("%Y%m%d", strict=False)
    decoded = {"N": scaled(value, scale), "D": pl.when(value.eq(9_999_999)).then(pl.lit(OPEN_END)).otherwise(date),
               "T": value.cast(pl.String).str.strptime(pl.Datetime, "%Y%m%d%H%M%S")}
    return decoded.get(kind, value).alias(col)


def decoded_table(name: str) -> pl.DataFrame:
    """The table `name` of `legacy.table` with every column decoded (see `decode`).

    Columns that NRDICT does not list are treated as text.
    """
    types = column_types()
    frame = legacy.table(LEGACY, name)
    return frame.with_columns(decode(col, *types.get(col, ("C", 0))) for col in frame.columns)


def load(name: str, raw: bool = False) -> pl.DataFrame:
    """Table `name` (e.g. "NRPOLH") decoded for exploring, or with `raw=True` the stored integers.

    Both are cached as parquet in `cache_dir()`, so that NRBOOK (390 MB of CSV) loads in a second.
    """
    cached = cache_dir().joinpath(f"{name}_raw.parquet" if raw else f"{name}.parquet")
    if cached.exists():
        return pl.read_parquet(cached)
    frame = legacy.table(LEGACY, name) if raw else decoded_table(name)
    frame.write_parquet(cached)
    return frame
