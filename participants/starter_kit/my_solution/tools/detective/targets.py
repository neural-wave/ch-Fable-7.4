"""The target files: the values the legacy system calculated, typed exactly from their text.

A target file is comma-separated text. Its column types come from the values, not from a list per file:

- ISO dates (2025-12-31) become dates
- whole numbers become integers
- decimals become integers in units of their last decimal (cents for 1234.56), so they compare exactly
- everything else stays text, without surrounding blanks
"""
import pathlib

import polars as pl

from detective.load import ROOT

TARGETS = ROOT / "participants" / "targets"
PATTERNS = {"date": r"^\d{4}-\d{2}-\d{2}$", "integer": r"^-?\d+$", "decimal": r"^-?\d+\.\d+$"}


def kind(values: pl.Series) -> str:
    """date, integer, decimal or text: the first pattern that all values of a text column match."""
    filled = values.drop_nulls()
    return next((name for name, pattern in PATTERNS.items() if filled.str.contains(pattern).all()), "text")


def decimals(values: pl.Series) -> int:
    """The most decimals of a decimal column."""
    return values.drop_nulls().str.split(".").list.last().str.len_chars().max()


def typed(column: str, values: pl.Series) -> pl.Expr:
    """The expression that turns a text column of a target file into its type."""
    found = kind(values)
    places = decimals(values) if found == "decimal" else 0
    converted = {"date": pl.col(column).str.to_date("%Y-%m-%d"), "integer": pl.col(column).cast(pl.Int64),
                 "decimal": pl.col(column).cast(pl.Decimal(38, places)).mul(10 ** places).cast(pl.Int64),
                 "text": pl.col(column).str.strip_chars()}
    return converted[found]


def target(name: str, folder: pathlib.Path = TARGETS) -> pl.DataFrame:
    """The target file `name` (without .csv), every column typed from its values."""
    text = pl.read_csv(folder / f"{name}.csv", infer_schema=False)
    return text.select(typed(column, text[column]) for column in text.columns)


def names(folder: pathlib.Path = TARGETS) -> list[str]:
    """The target files of `folder`."""
    return sorted(path.stem for path in folder.glob("*.csv"))
