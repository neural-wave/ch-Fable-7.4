"""Reading the Neuron export and looking up the version of a row that is valid on a date.

The export is a folder of `;`-separated CSV files, one per table, described by the data dictionary NRDICT
(formats: see SCHEMA.md). Values stay the integers they are stored as: amounts in cents (`N(2)`), rates in
millionths (`N(6)`), dates as `CYYMMDD` and timestamps as `YYYYMMDDHHMMSS`.

- Integers keep the money arithmetic exact, without floats.
- `CYYMMDD` dates sort like the dates themselves (`970630` < `1070326` < `9999999`, the open end), so the
  validity of a version is a plain comparison of integers.
"""
import functools
import pathlib

import polars as pl

STORED_AS = {"C": pl.String, "N": pl.Int64, "D": pl.Int64, "T": pl.Int64}  # NRDICT type -> polars type
CENTURY = 19_000_000  # CYYMMDD + 19000000 = YYYYMMDD: C is 0 for 19xx and 1 for 20xx


def read(legacy_dir, name: str) -> pl.DataFrame:
    """The file `<name>.csv` of the export, every column as text.

    Reading text first keeps the values exactly as exported; `parse` converts them by their NRDICT type.
    """
    return pl.read_csv(pathlib.Path(legacy_dir, f"{name}.csv"), separator=";", infer_schema=False)


@functools.cache
def column_types(legacy_dir) -> dict[str, str]:
    """{column: type} from the data dictionary NRDICT.

    The types are C text, N number, D date `CYYMMDD` and T timestamp `YYYYMMDDHHMMSS`.
    """
    dictionary = read(legacy_dir, "NRDICT")
    return dict(zip(dictionary["DC_COLUMN"], dictionary["DC_TYPE"], strict=True))


def parse(col: str, kind: str) -> pl.Expr:
    """Expression that converts the text of column `col` to its NRDICT type `kind`.

    Fixed-width fields are padded with blanks: they are removed, and an empty field becomes null.
    """
    text = pl.col(col).str.strip_chars()
    return pl.when(text.ne("")).then(text).cast(STORED_AS[kind]).alias(col)


@functools.cache
def table(legacy_dir, name: str) -> pl.DataFrame:
    """A legacy table (e.g. "NRPOLH") with every column converted by its NRDICT type.

    Columns that NRDICT does not list stay text. The result is cached, since several tasks read the same tables.
    """
    types = column_types(legacy_dir)
    frame = read(legacy_dir, name)
    return frame.with_columns(parse(col, types.get(col, "C")) for col in frame.columns)


def valid_on(rows: pl.DataFrame, versions: pl.DataFrame, on: dict[str, str], date: str, prefix: str,
             newest: str = "VRSNR") -> pl.DataFrame:
    """Every row of `rows` joined with the version of `versions` that is valid on its column `date`.

    `on` maps the key columns of `rows` to those of `versions`. A version is valid from `<prefix>_VLDFR` to
    `<prefix>_VLDTO`, both days included. If several versions are valid, the one with the highest
    `<prefix>_<newest>` wins: the version number, so a change counts from its validity date even when it
    was entered later.
    """
    joined = rows.with_row_index("row").join(versions, left_on=list(on), right_on=list(on.values()))
    valid = joined.filter(pl.col(date).is_between(pl.col(f"{prefix}_VLDFR"), pl.col(f"{prefix}_VLDTO")))
    return valid.sort(f"{prefix}_{newest}").unique("row", keep="last").drop("row")


def as_date(col: str) -> pl.Expr:
    """The legacy date `CYYMMDD` of column `col` as a date, e.g. 1260630 -> 2026-06-30.

    The open end 9999999 and the empty date 0 are no calendar days and become null.
    """
    return pl.col(col).add(CENTURY).cast(pl.String).str.to_date("%Y%m%d", strict=False)


def as_lenient_date(col: str) -> pl.Expr:
    """The legacy date `CYYMMDD` of column `col` as a date, where an impossible day runs on into the next month.

    The export has birth dates such as 31 November (`861131`). Counted like a lenient calendar, the day after
    30 November, 1 December. Valid dates stay as they are.
    """
    day = pl.col(col).add(CENTURY)
    first = pl.date(day.floordiv(10_000), day.floordiv(100).mod(100), 1)
    return first.add(pl.duration(days=day.mod(100).sub(1)))


def as_cyymmdd(day) -> pl.Expr:
    """The date `day` as the legacy integer `CYYMMDD`, to compare it with the stored dates."""
    return pl.lit(day).dt.strftime("%Y%m%d").cast(pl.Int64).sub(CENTURY)


def versions_on(versions: pl.DataFrame, day, key: str, prefix: str) -> pl.DataFrame:
    """The version of every `key` (e.g. every policy) that is valid on the date `day`.

    As in `valid_on`: valid from `<prefix>_VLDFR` to `<prefix>_VLDTO`, both days included, and the highest
    version number `<prefix>_VRSNR` wins. A key without a valid version on that day is left out.
    """
    valid = versions.filter(as_cyymmdd(day).is_between(pl.col(f"{prefix}_VLDFR"), pl.col(f"{prefix}_VLDTO")))
    return valid.sort(f"{prefix}_VRSNR").unique(key, keep="last")
