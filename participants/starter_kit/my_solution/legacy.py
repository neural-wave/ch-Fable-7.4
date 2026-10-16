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
