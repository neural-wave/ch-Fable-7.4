"""Inclusion dependencies (IND) between the tables, found by Desbordante: the candidates for foreign keys.

An IND `A in B` says that all values of the columns A also appear in the columns B, as for a foreign key.

- Faida finds the exact INDs, also over two columns (`MAX_ARITY`), e.g. `PR_POLNR, PR_EVTNR` in NREVNT.
- Spider finds approximate INDs over one column, where up to `MAX_ERROR` of the values are missing.

Desbordante reads CSV files, so `profiling_file` writes the key candidates of every table into the cache.
"""
import contextlib
import functools
import pathlib
import shutil

import desbordante
import polars as pl

from neuron.load import cache_dir, tables
from neuron.schema.keys import key_candidates

MAX_ARITY = 2  # INDs over at most two columns
MAX_ERROR = 0.25  # approximate INDs: at most a quarter of the distinct values missing


def profiled_tables() -> list[str]:
    """The tables that take part in the search for INDs.

    NRDICT describes columns, not data, and a table without text or integer columns (NRILLU) has no key to link.
    """
    return [table for table in tables("NRDICT") if key_candidates(table).width]


def profiling_file(table: str) -> pathlib.Path:
    """`key_candidates` of a table as a CSV file for Desbordante, in the folder `profiling` of the cache.

    The file is written once per version of the export (see `cache_dir`).
    """
    path = cache_dir().joinpath("profiling", f"{table}.csv")
    if path.exists():
        return path
    path.parent.mkdir(exist_ok=True)
    key_candidates(table).write_csv(path)
    return path


def side(prefix: str, columns, names: list[tuple[str, list[str]]]) -> dict:
    """Table and column names of one side of an IND, as {"<prefix>table": ..., "<prefix>columns": "A, B"}.

    Desbordante gives the side as indices: of the table into `names`, and of the columns into its header.
    """
    table, cols = names[columns.table_index]
    return {f"{prefix}table": table, f"{prefix}columns": ", ".join(cols[i] for i in columns.column_indices)}


def ind_rows(inds, files: list[pathlib.Path], algorithm: str) -> list[dict]:
    """Desbordante IND objects as rows: table, columns, ref_table, ref_columns and the algorithm that found it.

    `files` must be the files in the order that Desbordante loaded them, so that the indices match.
    """
    names = [(path.stem, pl.read_csv(path, n_rows=0).columns) for path in files]
    return [{**side("", ind.get_lhs(), names), **side("ref_", ind.get_rhs(), names), "algorithm": algorithm}
            for ind in inds]


def exact_inds(sources: list[tuple]) -> list:
    """Exact INDs over up to `MAX_ARITY` columns (Faida).

    Faida spills its hashes to ./temp: they are written inside the cache and deleted afterwards.
    """
    algorithm = desbordante.ind.algorithms.Faida()
    folder = cache_dir().joinpath("profiling")
    with contextlib.chdir(folder):
        algorithm.load_data(tables=sources)
        algorithm.execute(max_arity=MAX_ARITY)
    shutil.rmtree(folder.joinpath("temp"), ignore_errors=True)
    return algorithm.get_inds()


def approximate_inds(sources: list[tuple]) -> list:
    """Approximate INDs over one column with at most `MAX_ERROR` of the values missing (Spider).

    They show references to rows that the export lacks; `relations` measures the exact share later.
    """
    algorithm = desbordante.aind.algorithms.Spider()
    algorithm.load_data(tables=sources)
    algorithm.execute(error=MAX_ERROR)
    return algorithm.get_inds()


@functools.cache
def discover_inds() -> pl.DataFrame:
    """All INDs between the tables: the exact ones of Faida, then the approximate ones of Spider.

    An IND that both find is kept once, as exact. Desbordante options go to `execute`, not to `load_data`,
    which ignores them.
    """
    files = [profiling_file(table) for table in profiled_tables()]
    sources = [(str(path), ",", True) for path in files]
    exact = ind_rows(exact_inds(sources), files, "Faida")
    approximate = ind_rows(approximate_inds(sources), files, "Spider (approx.)")
    return pl.DataFrame([*exact, *approximate]).unique(["table", "columns", "ref_table", "ref_columns"], keep="first",
                                     maintain_order=True)
