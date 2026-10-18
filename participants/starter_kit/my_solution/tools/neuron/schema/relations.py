"""Relations between the tables: every IND of Desbordante checked exactly and described by a few features.

An IND counts as a relation when it can be a foreign key (`is_relation`). The features say why:

- `error`: share of the distinct values that are missing in the referenced columns (0 for an exact IND)
- `coverage`: share of the referenced values that are used
- `same_format`, `same_name`: the same NRDICT type and length, the same business key (naming convention)
- `ref_key_prefix`: the referenced columns are the leading columns of the documented key
"""
import functools

import polars as pl

from neuron.load import dictionary
from neuron.schema.inclusions import MAX_ERROR, discover_inds
from neuron.schema.keys import abbreviation, declared_keys, key_candidates

MIN_COVERAGE = 0.8  # columns with different names must share 80 % of the referenced values
COLUMNS = ["table", "columns", "ref_table", "ref_columns", "algorithm", "arity", "values", "ref_values", "error",
           "missing", "same_format", "same_name", "ref_key_prefix", "coverage"]


@functools.cache
def distinct_values(table: str, cols: str) -> pl.DataFrame:
    """Distinct non-null value combinations of the columns `cols` ("A, B") of a table, as text."""
    return key_candidates(table).select(pl.col(cols.split(", ")).cast(pl.String)).drop_nulls().unique()


def missing_values(table: str, cols: str, ref_table: str, ref_cols: str) -> pl.DataFrame:
    """Value combinations of `table` that do not appear in `ref_table`: the exceptions of an IND."""
    ref = distinct_values(ref_table, ref_cols).rename(dict(zip(ref_cols.split(", "), cols.split(", "), strict=True)))
    return distinct_values(table, cols).join(ref, on=cols.split(", "), how="anti")


def formats() -> dict[str, str]:
    """{column: NRDICT type and length, e.g. "C12"}: two columns can only be linked with the same format."""
    return dict(dictionary().select("DC_COLUMN", pl.concat_str("DC_TYPE", "DC_LEN")).iter_rows())


def facts(ind: dict, keys: dict[str, list[str]], format_of: dict[str, str]) -> dict:
    """The IND `ind` checked exactly on the data, with what the features need for both of its sides.

    The counts of distinct and missing values, the formats and business keys of the columns, and the leading
    columns of the documented key of the referenced table.
    """
    cols, ref_cols = ind["columns"].split(", "), ind["ref_columns"].split(", ")
    missing = missing_values(ind["table"], ind["columns"], ind["ref_table"], ind["ref_columns"])
    return {**ind, "arity": len(cols), "values": distinct_values(ind["table"], ind["columns"]).height,
            "ref_values": distinct_values(ind["ref_table"], ind["ref_columns"]).height,
            "missing_values": missing.height, "missing": str(missing.head(3).rows()),
            "formats": [format_of[col] for col in cols], "ref_formats": [format_of[col] for col in ref_cols],
            "keys": [abbreviation(col) for col in cols], "ref_keys": [abbreviation(col) for col in ref_cols],
            "ref_cols": sorted(ref_cols), "key_prefix": sorted(keys.get(ind["ref_table"], [])[:len(ref_cols)])}


def features() -> dict[str, pl.Expr]:
    """The features of the module docstring, as expressions over the columns of `facts`.

    A side without values counts as one value, so that the shares stay defined.
    """
    return {"error": pl.col("missing_values").truediv(pl.max_horizontal("values", 1)),
            "same_format": pl.col("formats").eq(pl.col("ref_formats")),
            "same_name": pl.col("keys").eq(pl.col("ref_keys")),
            "ref_key_prefix": pl.col("ref_cols").eq(pl.col("key_prefix")),
            "coverage": pl.col("values").sub(pl.col("missing_values")).truediv(pl.max_horizontal("ref_values", 1))}


def is_relation() -> pl.Expr:
    """An IND is a relation when it can be a foreign key.

    It needs the same format, at least two values, at most `MAX_ERROR` missing, and referenced columns that are
    the leading columns of the documented key (a counter like PH_VRSNR in `PH_POLNR, PH_VRSNR` only means
    something together with PH_POLNR). The link is either the same business key (naming convention of
    SCHEMA.md) or an exact single-column link that covers most of the referenced values.
    """
    by_data = pl.all_horizontal(pl.col("arity").eq(1), pl.col("error").eq(0), pl.col("coverage").ge(MIN_COVERAGE))
    return pl.all_horizontal(pl.col("same_format"), pl.col("ref_key_prefix"), pl.col("values").ge(2),
                             pl.col("error").le(MAX_ERROR), pl.any_horizontal(pl.col("same_name"), by_data))


@functools.cache
def relations() -> pl.DataFrame:
    """Every IND found by Desbordante, checked exactly, with its features and the flag `relation`.

    The relations come first, then the other INDs, each sorted by table and columns.
    """
    keys, format_of = declared_keys(), formats()
    checked = pl.DataFrame([facts(ind, keys, format_of) for ind in discover_inds().iter_rows(named=True)])
    frame = checked.with_columns(**features()).select(COLUMNS).with_columns(relation=is_relation())
    return frame.sort(["relation", "table", "columns"], descending=[True, False, False])
