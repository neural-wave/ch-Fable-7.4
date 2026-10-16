"""Keys of the tables: the ones documented in SCHEMA.md against the ones that HyUCC finds in the data.

HyUCC (Desbordante) finds the minimal unique column combinations of a table, its candidate keys. Only text and
integer columns take part (`key_candidates`): dates, timestamps and amounts are no keys.
"""
import functools
import re

import desbordante
import polars as pl
import polars.selectors as cs

from neuron.load import DATA, dictionary, load

KEY_FORMATS = ["C(0)", "N(0)"]  # NRDICT type(scale) of the columns that can be keys: text and integers
HEADER = re.compile(r"^### (NR\w+): (.*)$", flags=re.MULTILINE)  # e.g. "### NRPOLH: Policy (key PH_POLNR, ...)"
KEY = re.compile(r"\s*\(key ([^)]*)\)")


def abbreviation(col: str) -> str:
    """Business key of a column: `RK_POLNR` -> `POLNR`.

    SCHEMA.md: the prefix names the table and the abbreviation the business key, so the same abbreviation in
    two tables is the same key.
    """
    return col.split("_", 1)[1]


def table_header(table: str, header: str) -> dict:
    """Description and documented key columns of one table header of SCHEMA.md.

    The key is the list in "(key A, B)" at the end of the header; the description is the rest.
    """
    key = KEY.search(header)
    return {"table": table, "description": KEY.sub("", header), "key": key.group(1).split(", ") if key else []}


@functools.cache
def schema_tables() -> pl.DataFrame:
    """Description and documented key of every table, from the headers `### NRPOLH: ... (key PH_POLNR, ...)`.

    The descriptions also label the tables in the overview of the notebook.
    """
    text = DATA.joinpath("SCHEMA.md").read_text(encoding="utf-8")
    rows = [table_header(table, header) for table, header in HEADER.findall(text)]
    return pl.DataFrame(rows, schema={"table": pl.String, "description": pl.String, "key": pl.List(pl.String)})


def declared_keys() -> dict[str, list[str]]:
    """{table: documented key columns}.

    Tables without a documented key get an empty list.
    """
    return dict(schema_tables().select("table", "key").iter_rows())


@functools.cache
def key_columns() -> list[str]:
    """Columns that can be keys, by their NRDICT format: text and integers.

    Dates, timestamps and amounts (numbers with decimals) are no keys.
    """
    formats = pl.format("{}({})", "DC_TYPE", pl.col("DC_SCALE").fill_null("0"))
    return dictionary().filter(formats.is_in(KEY_FORMATS))["DC_COLUMN"].to_list()


@functools.cache
def key_candidates(table: str) -> pl.DataFrame:
    """The text and integer columns of a table, where keys live.

    An integer 0 means "no reference" (e.g. EV_REVNR of an event that reverses nothing) and becomes null.
    """
    frame = load(table, raw=True)
    return frame.select(cs.by_name(key_columns(), require_all=False)).with_columns(cs.integer().replace(0, None))


def discover_keys(table: str) -> list[tuple[str, ...]]:
    """Minimal unique column combinations of a table (HyUCC), the smallest first.

    Empty columns cannot identify a row and are left out.
    """
    frame = load(table, raw=True)
    frame = frame.select(col for col in frame.columns if frame[col].is_not_null().any())
    algorithm = desbordante.ucc.algorithms.HyUCC()
    algorithm.load_data(table=frame.to_pandas())
    algorithm.execute()
    found = (tuple(frame.columns[i] for i in ucc.indices) for ucc in algorithm.get_uccs())
    return sorted(found, key=lambda key: (len(key), key))


def key_check(key: list[str], found: list[tuple[str, ...]]) -> dict:
    """Is the documented `key` unique (it contains a found key) and minimal (it is one of the found keys)?

    Both are None for a table without a documented key.
    """
    if key:
        found_keys = {frozenset(k) for k in found}
        return {"unique": any(k.issubset(key) for k in found_keys), "minimal": found_keys.issuperset([frozenset(key)])}
    return {"unique": None, "minimal": None}


def key_report() -> pl.DataFrame:
    """Documented key of every table against the keys that HyUCC finds, with the three smallest of them.

    A documented key that is not unique, or not minimal, is a hint about the data: duplicates, or a key column
    that the data does not need.
    """
    rows = []
    for table, key in declared_keys().items():
        found = discover_keys(table)
        rows.append({"table": table, "declared_key": ", ".join(key), **key_check(key, found),
                     "keys_found": len(found), "smallest_keys": " | ".join(", ".join(k) for k in found[:3])})
    return pl.DataFrame(rows)
