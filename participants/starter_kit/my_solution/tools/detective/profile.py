"""Profile a legacy export: the data problems that every migration meets, found by generic checks.

Every check looks at all tables and columns and returns rows of TABLE, COLUMN, CHECK, ROWS (how many rows are
affected) and EXAMPLES. None of them knows the tables; they only use the dictionary and the code lists:

- undecodable: a stored value that its type cannot decode, e.g. an impossible date
- case_variants: text values that differ only in upper and lower case, e.g. `eur` beside `EUR`
- empty_column: a column without any value (calculated columns that the export left out)
- empty_for_code: a column that is empty exactly for some codes of another column, e.g. calculated amounts that a
  job filled in for some booking types only
- short_rows: rows with fewer fields than the header, so their last columns are missing
- outside_description: values that the dictionary description does not list, e.g. `J` for "smoker (Y/N)"
- outside_code_list: values that are missing from the code list named like their column
- no_code_list: a column of few distinct codes without a code list of its name

A column with codes outside its list or without a list gets the code lists that hold all of its values as
EXAMPLES ("fits PRSTAT"), so a list with a different name is found too.
"""
import pathlib
import re

import polars as pl

from detective.load import LEGACY, columns, decoded, raw, tables

CODES = "NRCODE"  # the code lists: one row per domain and code
CODE_DOMAIN, CODE_VALUE = "CD_DOMAIN", "CD_CODE"
FEW_CODES = 12  # a column with at most this many distinct values looks like a code
EXAMPLES = 5
LISTED = re.compile(r"\(([A-Z0-9]{1,4}(?:=[^,/)]*)?(?:\s*[/,]\s*[A-Z0-9]{1,4}(?:=[^,/)]*)?)+)\)")


def finding(table: str, column: str, check: str, values: pl.Series, examples: list[str] | None = None) -> dict:
    """One row of the profile: how many rows `values` has, and `examples` or up to EXAMPLES distinct values."""
    shown = examples or values.drop_nulls().unique(maintain_order=True).head(EXAMPLES).cast(pl.String).to_list()
    return {"TABLE": table, "COLUMN": column, "CHECK": check, "ROWS": values.len(), "EXAMPLES": ", ".join(shown)}


def undecodable(table: str, stored: pl.DataFrame, typed: pl.DataFrame) -> list[dict]:
    """Values that are stored but decode to null (0 is the stored "no value" of numbers and dates)."""
    rows = []
    for column in typed.columns:
        kept = stored[column].str.strip_chars()
        lost = kept.filter(typed[column].is_null() & kept.is_not_null() & kept.ne("") & kept.ne("0"))
        rows.extend([finding(table, column, "undecodable", lost)] if lost.len() else [])
    return rows


def case_variants(table: str, typed: pl.DataFrame) -> list[dict]:
    """Text values whose upper case form is shared with another spelling."""
    rows = []
    for column in typed.select(pl.col(pl.String)).columns:
        spellings = typed.select(pl.col(column).drop_nulls().unique())
        shared = spellings.filter(pl.col(column).str.to_uppercase().is_duplicated())[column]
        variants = typed[column].filter(typed[column].is_in(shared.filter(shared.ne(shared.str.to_uppercase()))))
        rows.extend([finding(table, column, "case_variants", variants)] if variants.len() else [])
    return rows


def empty_columns(table: str, typed: pl.DataFrame) -> list[dict]:
    """Columns without any value."""
    empty = [column for column in typed.columns if typed[column].null_count() == typed.height]
    return [finding(table, column, "empty_column", typed[column]) for column in empty]


def code_columns(typed: pl.DataFrame) -> list[str]:
    """The columns with 2 to FEW_CODES distinct values."""
    counts = typed.select(pl.all().n_unique()).row(0, named=True)
    return [column for column, count in counts.items() if 1 < count <= FEW_CODES]


def empty_for_code(table: str, typed: pl.DataFrame) -> list[dict]:
    """Columns that are always empty for some codes of a code column and always filled for the others."""
    rows = []
    partly = [column for column in typed.columns if 0 < typed[column].null_count() < typed.height]
    for code in code_columns(typed):
        others = [column for column in partly if column != code]
        filled = typed.group_by(code).agg(pl.col(others).is_not_null().mean())
        for column in others:
            empty = filled.filter(pl.col(column).eq(0))[code]
            split = filled[column].is_in([0.0, 1.0]).all() and 0 < empty.len() < filled.height
            examples = [f"empty for {code} in {sorted(map(str, empty))}"]
            rows.extend([finding(table, column, "empty_for_code", typed[column].filter(typed[column].is_null()),
                                 examples)] if split else [])
    return rows


def short_rows(table: str, folder: pathlib.Path) -> list[dict]:
    """Rows whose line has fewer separators than the header."""
    lines = pl.read_csv(folder / f"{table}.csv", has_header=False, separator="\x01", infer_schema=False,
                        quote_char=None).to_series()
    fields = lines.str.count_matches(";")
    short = lines.filter(fields.lt(fields.first()))
    return [finding(table, "", "short_rows", short)] if short.len() else []


def described_codes(description: str) -> set[str]:
    """The codes that a description lists in brackets: "smoker (Y/N)" -> {Y, N}, "(C=current, S=...)" -> {C, S}."""
    match = LISTED.search(description or "")
    parts = re.split(r"\s*[/,]\s*", match.group(1)) if match else []
    return {part.partition("=")[0] for part in parts}


def outside_description(table: str, typed: pl.DataFrame, folder: pathlib.Path) -> list[dict]:
    """Values of a column that its description in the dictionary does not list."""
    rows = []
    for column, description in columns(table, folder).select("COLUMN", "DESCRIPTION").iter_rows():
        listed = described_codes(description)
        values = typed[column].drop_nulls().cast(pl.String)
        outside = values.filter(values.is_in(sorted(listed)).not_()) if listed else values.clear()
        rows.extend([finding(table, column, "outside_description", outside,
                             [f"{description!r} lists {sorted(listed)}", *outside.unique().sort().head(EXAMPLES)])]
                    if outside.len() else [])
    return rows


def code_lists(folder: pathlib.Path = LEGACY) -> dict[str, set[str]]:
    """{domain: codes} of the code table."""
    codes = decoded(CODES, folder).group_by(CODE_DOMAIN).agg(pl.col(CODE_VALUE))
    return {domain: set(values) for domain, values in codes.iter_rows()}


def fitting_lists(values: pl.Series, lists: dict[str, set[str]]) -> list[str]:
    """The code lists that hold every distinct value of `values`."""
    distinct = set(values.unique().to_list())
    return [f"fits {domain}" for domain, codes in sorted(lists.items()) if distinct <= codes]


def coded_columns(table: str, typed: pl.DataFrame, lists: dict[str, set[str]]) -> list[dict]:
    """Columns named after a code list (the part after `_`) with values outside it, and code-like columns
    without a list of their name."""
    rows = []
    codes = code_columns(typed)
    for column in typed.columns:
        domain = column.partition("_")[2]
        values = typed[column].drop_nulls().cast(pl.String)
        fits = fitting_lists(values, lists)
        if domain in lists:
            outside = values.filter(values.is_in(sorted(lists[domain])).not_())
            rows.extend([finding(table, column, "outside_code_list", outside, fits)] if outside.len() else [])
        elif column in codes and typed[column].dtype == pl.String:
            rows.append(finding(table, column, "no_code_list", values, fits))
    return rows


def table_profile(table: str, folder: pathlib.Path, lists: dict[str, set[str]]) -> list[dict]:
    """All checks of one table."""
    stored = raw(table, folder)
    typed = decoded(table, folder)
    return [*undecodable(table, stored, typed), *case_variants(table, typed), *empty_columns(table, typed),
            *empty_for_code(table, typed), *short_rows(table, folder), *outside_description(table, typed, folder),
            *coded_columns(table, typed, lists)]


def profile(folder: pathlib.Path = LEGACY) -> pl.DataFrame:
    """The profile of the whole export, one row per table, column and check that found something."""
    lists = code_lists(folder)
    rows = [row for table in tables(folder) for row in table_profile(table, folder, lists)]
    return pl.DataFrame(rows).sort("CHECK", "TABLE", "COLUMN")


def described(table: str, folder: pathlib.Path = LEGACY) -> pl.DataFrame:
    """The dictionary of a table next to a summary of its decoded columns: nulls, distinct values, min, max."""
    typed = decoded(table, folder)
    summary = [{"COLUMN": column, "NULLS": typed[column].null_count(), "DISTINCT": typed[column].n_unique(),
                "MIN": str(typed[column].min()), "MAX": str(typed[column].max())} for column in typed.columns]
    return columns(table, folder).join(pl.DataFrame(summary), on="COLUMN", how="right")
