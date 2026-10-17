"""Read the Neuron export: one CSV file per table (`;`, header row), typed by the data dictionary NRDICT.

The dictionary gives every column a type code:
- C text, padded with blanks on the right
- N integer with implied decimals; the stored integer is kept, so all arithmetic stays exact
- D date as CYYMMDD (C = 0 for 19xx, 1 for 20xx); 0 means no date, 9999999 an open end
- T timestamp as YYYYMMDDHHMMSS
"""
import datetime as dt
import functools
import pathlib

import polars as pl

DICTIONARY = "NRDICT"
OPEN_END = 9_999_999
LAST_DAY = dt.date(9999, 12, 31)
CENTURY = 10_000  # CYYMMDD // CENTURY = C * 100 + YY: the years since 1900


def text(column: str) -> pl.Expr:
    """A C column without its padding."""
    return pl.col(column).str.strip_chars_end()


def number(column: str) -> pl.Expr:
    """An N column as its stored integer."""
    return pl.col(column).str.strip_chars().cast(pl.Int64, strict=False)


def date(column: str) -> pl.Expr:
    """A D column as a date: null for 0 or an impossible day, LAST_DAY for an open end."""
    stored = number(column)
    year = stored.floordiv(CENTURY).add(1900).cast(pl.String)
    month_day = stored.mod(CENTURY).cast(pl.String).str.zfill(4)
    calendar = pl.concat_str(year, month_day).str.to_date("%Y%m%d", strict=False)
    return pl.when(stored.eq(OPEN_END)).then(pl.lit(LAST_DAY)).otherwise(calendar)


def lenient_date(column: str, impossible: str) -> pl.Expr:
    """A D column as a date where an impossible day such as 31 April is read by `impossible`: "clamp" to the last
    day of the month or "roll" into the next one."""
    stored = number(column)
    first = pl.date(stored.floordiv(CENTURY).add(1900), stored.mod(CENTURY).floordiv(100), 1)
    rolled = first.dt.offset_by(pl.format("{}d", stored.mod(100).sub(1)))
    days = {"roll": rolled, "clamp": pl.min_horizontal(rolled, first.dt.month_end())}
    return days[impossible]


def timestamp(column: str) -> pl.Expr:
    """A T column as a datetime."""
    return pl.col(column).str.strip_chars().str.to_datetime("%Y%m%d%H%M%S", strict=False)


DECODERS = {"C": text, "N": number, "D": date, "T": timestamp}


def raw(legacy_dir, name: str) -> pl.DataFrame:
    """Table `name` as stored text."""
    return pl.read_csv(pathlib.Path(legacy_dir, f"{name}.csv"), separator=";", infer_schema=False,
                       truncate_ragged_lines=True)


@functools.cache
def types(legacy_dir) -> dict[str, str]:
    """{column: type code} of every column of the export."""
    dictionary = raw(legacy_dir, DICTIONARY).select(text("DC_COLUMN"), text("DC_TYPE"))
    return dict(dictionary.iter_rows())


@functools.cache
def table(legacy_dir, name: str) -> pl.DataFrame:
    """Table `name`, every column decoded by its type."""
    stored = raw(legacy_dir, name)
    kinds = types(legacy_dir)
    return stored.with_columns(DECODERS[kinds[column]](column).alias(column) for column in stored.columns)


def version_on(rows: pl.DataFrame, versions: pl.DataFrame, on: dict[str, str], day: str | None,
               order: str) -> pl.DataFrame:
    """`rows` with the row of `versions` valid on the date column `day` (VLDFR <= day <= VLDTO), the highest
    `order` winning; with `day` None the last version by `order`.

    `on` maps the columns of `rows` to the key columns of `versions`; the validity columns end in VLDFR, VLDTO.
    """
    alias = order.partition("_")[0]
    match day:
        case None:
            last = versions.sort(order).unique(list(on.values()), keep="last")
            return rows.join(last, left_on=list(on), right_on=list(on.values()), how="left")
    indexed = rows.with_row_index("ROW")
    candidates = indexed.select("ROW", day, *on).join(versions, left_on=list(on), right_on=list(on.values()))
    valid = candidates.filter(pl.col(day).is_between(pl.col(f"{alias}_VLDFR"), pl.col(f"{alias}_VLDTO")))
    chosen = valid.sort(order).unique("ROW", keep="last").drop(day, *on)
    return indexed.join(chosen, on="ROW", how="left").drop("ROW")


def versions_on(versions: pl.DataFrame, day, key: str, order: str) -> pl.DataFrame:
    """The row of every `key` of `versions` valid on the date `day`, the highest `order` winning."""
    alias = order.partition("_")[0]
    valid = versions.filter(pl.lit(day).is_between(pl.col(f"{alias}_VLDFR"), pl.col(f"{alias}_VLDTO")))
    return valid.sort(order).unique(key, keep="last")
