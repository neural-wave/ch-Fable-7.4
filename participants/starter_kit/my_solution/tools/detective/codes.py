"""The code lists of the export: the text of a code, for people and for the prompts of the LLM."""
import pathlib

import polars as pl

from detective.load import LEGACY, load
from detective.profile import CODE_DOMAIN, CODE_VALUE, CODES, code_lists, fitting_lists

TEXTS = ("CD_TXTDE", "CD_TXTEN")  # the text columns of the code table; the first one that is filled counts


def domain_of(frame: pl.DataFrame, column: str, folder: pathlib.Path = LEGACY) -> str | None:
    """The code list of `column`: the one named after it, else the only one that holds all its values."""
    lists = code_lists(folder)
    named = column.partition("_")[2]
    fits = [fit.removeprefix("fits ") for fit in fitting_lists(frame[column].drop_nulls().cast(pl.String), lists)]
    return named if named in lists and named in fits else (fits[0] if len(fits) == 1 else None)


def label(frame: pl.DataFrame, column: str, folder: pathlib.Path = LEGACY) -> pl.DataFrame:
    """`frame` with `<column>_TXT`: the text of each code from its code list (`domain_of`)."""
    domain = domain_of(frame, column, folder)
    texts = load(CODES, folder).filter(pl.col(CODE_DOMAIN).eq(domain)).select(
        pl.col(CODE_VALUE).alias("CODE"), pl.coalesce(TEXTS).alias(f"{column}_TXT"))
    return frame.with_columns(pl.col(column).cast(pl.String).alias("CODE")).join(texts, on="CODE", how="left").drop(
        "CODE")


def code_list(domain: str, folder: pathlib.Path = LEGACY) -> dict[str, str]:
    """{code: text} of one code list."""
    rows = load(CODES, folder).filter(pl.col(CODE_DOMAIN).eq(domain))
    return dict(rows.select(CODE_VALUE, pl.coalesce(TEXTS)).iter_rows())
