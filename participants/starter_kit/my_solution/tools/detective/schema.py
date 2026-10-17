"""The structure of a legacy export, found in the data: the keys of every table and the relations between them.

Nothing here is written by hand; it comes from the data and the dictionary:

- keys: the minimal unique column combinations of a table (HyUCC of Desbordante). Big tables are searched on a
  sample, and every key found is verified on the whole table.
- inclusion dependencies: columns whose values all occur in another column (Spider of Desbordante), then pairs of
  such columns between the same two tables, verified exactly. An integer 0 counts as "no value", since a legacy
  export often stores a missing reference as 0.
- relations: the inclusion dependencies that can be foreign keys. Both sides are identifiers (text or integers
  without decimals, never dates or amounts) of the same type and length in the dictionary. The referenced columns
  are a key, or a key without its validity period and version number (a versioned table: one row per day). And
  every referencing column either has more than a handful of values or the same name after the table alias
  (`RK_POLNR` -> `PH_POLNR`). Of the pairs between two tables only those with the most such names stay, so a due
  number that happens to fit into the event numbers does not hide the event number.
- graph: the tables as nodes and the relations as edges (networkx), for the features of `features`.
"""
import functools
import itertools
import pathlib

import desbordante
import networkx as nx
import polars as pl

from detective.load import LEGACY, columns, kept, load, tables

SAMPLE = 200_000  # rows of a big table that HyUCC searches; the keys are then verified on all rows
FEW_VALUES = 10  # a column with fewer distinct values is a code, not a reference, unless its name says so
SKIPPED = ("NRDICT", "NRCODE")  # the metadata of the export
VALIDITY = ("VRSNR", "VLDFR", "VLDTO")  # the abbreviations of a version number and a validity period


def abbreviation(column: str) -> str:
    """The name of a column without its table alias: PH_POLNR -> POLNR."""
    return column.partition("_")[2]


def for_desbordante(frame: pl.DataFrame):
    """`frame` as a pandas frame of Python strings, the form Desbordante reads."""
    return frame.select(pl.all().cast(pl.String)).to_pandas().astype(object)


def reference_values(frame: pl.DataFrame) -> pl.DataFrame:
    """`frame` as text for the inclusion tests, an integer 0 read as "no value"."""
    integers = frame.select(pl.col(pl.Int64)).columns
    return frame.with_columns(pl.col(integers).replace(0, None)).select(pl.all().cast(pl.String))


@functools.cache
def keys(table: str, folder: pathlib.Path = LEGACY) -> tuple[tuple[str, ...], ...]:
    """The minimal keys of `table`, smallest first; each one is unique on the whole table."""
    frame = load(table, folder)
    sample = frame.sample(min(SAMPLE, frame.height), seed=0) if frame.height > SAMPLE else frame
    search = desbordante.ucc.algorithms.HyUCC()
    search.load_data(table=for_desbordante(sample))
    search.execute()
    found = [tuple(sample.columns[index] for index in ucc.indices) for ucc in search.get_uccs()]
    unique = [key for key in found if frame.select(pl.struct(key).n_unique()).item() == frame.height]
    return tuple(sorted(unique, key=lambda key: (len(key), key)))


def declared(table: str, column: str, folder: pathlib.Path) -> tuple:
    """(type, length, scale) of a column in the dictionary."""
    return columns(table, folder).filter(pl.col("COLUMN").eq(column)).select("TYPE", "LENGTH", "SCALE").row(0)


def identifier(table: str, column: str, folder: pathlib.Path) -> bool:
    """Whether a column can identify something: text, or an integer without decimals."""
    kind, _, decimals = declared(table, column, folder)
    return kind == "C" or (kind == "N" and decimals == 0)


def keyed(table: str, cols: tuple[str, ...], folder: pathlib.Path) -> bool:
    """Whether `cols` are a key of `table`, alone or with a version number and validity period."""
    rest = [set(key) - set(cols) for key in keys(table, folder) if set(cols) <= set(key)]
    return any(all(abbreviation(column) in VALIDITY for column in extra) for extra in rest)


def linkable(table: str, column: str, other: str, other_column: str, folder: pathlib.Path) -> bool:
    """Whether a column can refer to another: identifiers of the same type, named alike or with many values."""
    count = load(table, folder).select(pl.col(column).replace(0, None).n_unique()).item()
    named = abbreviation(column) == abbreviation(other_column)
    typed = declared(table, column, folder) == declared(other, other_column, folder)
    return typed and identifier(table, column, folder) and (named or count > FEW_VALUES)


def names_alike(cols: tuple[str, ...], other_cols: tuple[str, ...]) -> int:
    """How many columns have the same name after the table alias as the column they refer to."""
    return sum(abbreviation(column) == abbreviation(other) for column, other in zip(cols, other_cols, strict=True))


def single_inclusions(names: list[str], folder: pathlib.Path) -> list[tuple[str, str, str, str]]:
    """(table, column, referenced table, referenced column) of every column whose values occur in another one."""
    sets = [(table, column, values) for table in names
            for column, values in reference_values(load(table, folder)).to_dict().items()]
    distinct = [(table, column, values.drop_nulls().unique()) for table, column, values in sets]
    kept = [(table, column, values) for table, column, values in distinct if values.len()]
    search = desbordante.ind.algorithms.Spider()
    search.load_data(tables=[for_desbordante(values.to_frame()) for _, _, values in kept])
    search.execute()
    pairs = [(ind.get_lhs().table_index, ind.get_rhs().table_index) for ind in search.get_inds()]
    return [(kept[left][0], kept[left][1], kept[right][0], kept[right][1]) for left, right in pairs]


def is_relation(inclusion: tuple[str, str, str, str], folder: pathlib.Path) -> bool:
    """Whether a single column inclusion can be a foreign key (see the module docstring)."""
    table, column, other, other_column = inclusion
    return (column != other_column and linkable(table, column, other, other_column, folder)
            and keyed(other, (other_column,), folder))


def holds(table: str, cols: tuple[str, ...], other: str, other_cols: tuple[str, ...], folder: pathlib.Path) -> bool:
    """Whether every row of `cols` (no part 0 or empty) occurs as a row of `other_cols`."""
    left = reference_values(load(table, folder).select(cols)).drop_nulls()
    right = reference_values(load(other, folder).select(other_cols)).rename(dict(zip(other_cols, cols, strict=True)))
    return left.height > 0 and left.join(right.unique(), on=list(cols), how="anti").height == 0


def pair_inclusions(singles: list[tuple[str, str, str, str]], folder: pathlib.Path) -> list[tuple]:
    """Pairs of single inclusions between the same two tables that hold together and point to a key."""
    found = []
    links = [inclusion for inclusion in singles if linkable(*inclusion, folder)]
    selves = {(table, column, table, column) for table, *_ in singles for key in keys(table, folder) for column in key}
    ordered = sorted([*links, *selves], key=lambda inclusion: (inclusion[0], inclusion[2], inclusion[1]))
    for (table, other), group in itertools.groupby(ordered, key=lambda inclusion: (inclusion[0], inclusion[2])):
        pairs = [((table, (first[1], second[1]), other, (first[3], second[3])))
                 for first, second in itertools.combinations(list(group), 2)]
        held = [pair for pair in pairs if len(set(pair[1])) == len(set(pair[3])) == 2 and pair[1] != pair[3]
                and keyed(other, pair[3], folder) and holds(*pair, folder)]
        most = max([names_alike(pair[1], pair[3]) for pair in held], default=0)
        found.extend(pair for pair in held if names_alike(pair[1], pair[3]) == most)
    return found


@functools.cache
def relations(folder: pathlib.Path = LEGACY) -> pl.DataFrame:
    """TABLE, COLUMNS, REFERENCED, REFERENCED_COLUMNS of every relation; pairs of columns first. Kept per export
    version (`load.kept`)."""
    return kept("relations", lambda: found_relations(folder), folder)


def found_relations(folder: pathlib.Path) -> pl.DataFrame:
    """The relations of the export, searched as the module docstring says."""
    names = [table for table in tables(folder) if table not in SKIPPED]
    singles = single_inclusions(names, folder)
    pairs = pair_inclusions(singles, folder)
    paired = {(table, column, other) for table, cols, other, _ in pairs for column in cols}
    kept = [(table, (column,), other, (other_column,)) for table, column, other, other_column in singles
            if is_relation((table, column, other, other_column), folder) and (table, column, other) not in paired]
    rows = [{"TABLE": table, "COLUMNS": list(cols), "REFERENCED": other, "REFERENCED_COLUMNS": list(other_cols)}
            for table, cols, other, other_cols in [*pairs, *kept]]
    return pl.DataFrame(rows)


def graph(folder: pathlib.Path = LEGACY) -> nx.MultiDiGraph:
    """The tables as nodes and every relation as an edge from the referencing to the referenced table."""
    network = nx.MultiDiGraph()
    for table, cols, other, other_cols in relations(folder).iter_rows():
        network.add_edge(table, other, columns=tuple(cols), referenced=tuple(other_cols))
    return network
