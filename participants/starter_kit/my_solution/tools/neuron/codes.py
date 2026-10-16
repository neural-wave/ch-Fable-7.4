"""Code lists: the texts of the codes in NRCODE, and the code list that each code column uses.

SCHEMA.md says that the domain of a code column is its abbreviation (`EV_EVTTP` -> domain `EVTTP`).
`code_report` checks this convention on the data, because some columns break it (`PR_STATE` uses `PRSTAT`).
"""
import functools

import polars as pl

from neuron.load import dictionary, load, tables
from neuron.schema.keys import abbreviation, key_candidates

METADATA = ("NRCODE", "NRDICT")  # tables that describe codes and columns, not policies
DOMAINS = {"PR_STATE": "PRSTAT"}  # code columns whose domain is not their abbreviation (see `code_report`)


@functools.cache
def code_texts() -> dict[str, dict[str, str]]:
    """{domain: {code: text}} of the code lists in NRCODE.

    The export has the English texts in CD_TXTDE and leaves CD_TXTEN empty, so the first one filled is used.
    """
    texts = {}
    rows = load("NRCODE").select("CD_DOMAIN", "CD_CODE", pl.coalesce("CD_TXTEN", "CD_TXTDE")).iter_rows()
    for domain, code, text in rows:
        texts.setdefault(domain, {})[code] = text
    return texts


def domain_of(col: str) -> str:
    """The NRCODE domain of a code column: its abbreviation (SCHEMA.md), except for the columns in `DOMAINS`."""
    return DOMAINS.get(col, abbreviation(col))


def label(frame: pl.DataFrame, col: str) -> pl.DataFrame:
    """`frame` with the column `<col>_TXT`: the text of the code in `col`.

    Codes without a text in the domain of the column get null.
    """
    texts = code_texts()[domain_of(col)]
    text = pl.col(col).cast(pl.String).replace_strict(texts, default=None, return_dtype=pl.String)
    return frame.with_columns(text.alias(f"{col}_TXT"))


def column_values(table: str) -> list[dict]:
    """table, column and distinct values (sorted, as text) of every column of a table that can hold codes.

    Codes live in the text and integer columns, the key candidates of the table.
    """
    frame = key_candidates(table)
    return [{"table": table, "column": col, "values": sorted(set(frame[col].drop_nulls().cast(pl.String)))}
            for col in frame.columns]


def fitting_domains(values: list[str], domains: dict[str, set[str]]) -> list[str]:
    """The domains whose codes contain all `values`, sorted by name."""
    return sorted(domain for domain, codes in domains.items() if codes.issuperset(values))


def code_report(max_values: int = 30) -> pl.DataFrame:
    """Every code column: its NRCODE domain by name and the domains whose codes contain all of its values.

    A code column has 1 to `max_values` distinct values. Without a domain by name only text columns are kept,
    since small numbers like 1, 2 fit many domains by chance. `consistent` tells whether the name agrees with
    the values.
    """
    domains = {domain: set(codes) for domain, codes in code_texts().items()}
    rows = [{**row, "fitting": fitting_domains(row["values"], domains)}
            for table in tables(*METADATA) for row in column_values(table)]
    columns = pl.DataFrame(rows).filter(pl.col("values").list.len().is_between(1, max_values))
    name = pl.col("column").str.replace(r"^[^_]*_", "")
    report = columns.with_columns(domain_by_name=pl.when(name.is_in(list(domains))).then(name)).with_columns(
        values=pl.col("values").list.join(", "), domains_by_values=pl.col("fitting").list.join(", "),
        consistent=pl.col("fitting").list.contains(pl.col("domain_by_name")).fill_null(False))
    text = pl.col("column").is_in(dictionary().filter(pl.col("DC_TYPE").eq("C"))["DC_COLUMN"].implode())
    keep = pl.any_horizontal(pl.col("domain_by_name").is_not_null(),
                             pl.all_horizontal(pl.col("fitting").list.len().gt(0), text))
    return report.filter(keep).select("table", "column", "values", "domain_by_name", "domains_by_values", "consistent")
