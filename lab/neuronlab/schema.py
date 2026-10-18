"""The machine-readable data dictionary NRDICT: column types, lengths, scales and descriptions of every table."""
import csv
import dataclasses
import functools
import re

from . import paths


@dataclasses.dataclass(frozen=True)
class Column:
    table: str
    name: str
    type: str  # C text, N number with `scale` implied decimals, D date CYYMMDD, T timestamp
    length: int
    scale: int
    desc: str

    @property
    def abbreviation(self):
        """`RK_POLNR` -> `POLNR`: the same abbreviation means the same business key (SCHEMA.md conventions)."""
        return self.name.split("_", 1)[1]

    @property
    def is_amount(self):
        return self.type == "N" and self.scale > 0

    @property
    def is_key_like(self):
        """Columns that can take part in joins: text codes, whole numbers and dates."""
        return self.type in ("C", "D") or (self.type == "N" and self.scale == 0)

    @property
    def snake(self):
        """Readable identifier from the description, e.g. `BR_TIER` -> `broker_tier`."""
        words = re.sub(r"\(.*?\)", "", self.desc).lower()
        words = re.sub(r"[^a-z0-9]+", "_", words).strip("_")
        return words or self.name.lower()


@functools.cache
def dictionary():
    """{table: [Column, ...]} in file order, read with the standard library (NRDICT describes itself too)."""
    tables = {}
    with open(paths.LEGACY / "NRDICT.csv", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter=";"):
            row = {k: (v or "").strip() for k, v in row.items()}
            column = Column(row["DC_TABLE"], row["DC_COLUMN"], row["DC_TYPE"], int(row["DC_LEN"] or 0),
                            int(row["DC_SCALE"] or 0), row["DC_DESC"])
            tables.setdefault(column.table, []).append(column)
    return tables


def columns(table):
    return dictionary()[table]


def column(table, name):
    return next(c for c in columns(table) if c.name == name)


def find(name):
    """Column spec by column name alone (the two-letter prefix identifies the table)."""
    return next((c for cols in dictionary().values() for c in cols if c.name == name), None)


def alias(table):
    """Two-letter prefix of the columns of a table, e.g. NRPOLH -> PH."""
    return columns(table)[0].name.split("_", 1)[0]


def validity(table):
    """(valid from, valid to, version) column names of a table with validity periods, else None."""
    names = {c.abbreviation: c.name for c in columns(table)}
    if "VLDFR" in names and "VLDTO" in names:
        return names["VLDFR"], names["VLDTO"], names.get("VRSNR")
    return None


DECLARED_KEY = re.compile(r"^### (NR\w{4}):.*\(key ([^)]+)\)")


@functools.cache
def declared_keys():
    """{table: [key columns]} from the headings of SCHEMA.md, e.g. NRPOLH -> [PH_POLNR, PH_VRSNR]."""
    path = paths.REPO / "SCHEMA.md"
    if not path.exists():
        return {}
    found = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        m = DECLARED_KEY.match(line)
        if m:
            found[m.group(1)] = [c.strip() for c in m.group(2).split(",")]
    return found


def key_of(table, uccs):
    """The key of a table: the one SCHEMA.md declares when profiling confirms it (or did not run), else the first UCC."""
    mined = [sorted(u) for u in uccs or []]
    declared = declared_keys().get(table)
    if declared and (not mined or sorted(declared) in mined):
        return declared
    return mined[0] if mined else None
