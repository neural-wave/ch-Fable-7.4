"""The history of one policy: its rows in every table of the export, to read it like a case file.

The policy number column of a table ends in `_POLNR` (`PH_POLNR`, `PR_POLNR`, ...). Reading the timeline of a
policy next to its targets shows which events and versions a rule has to take into account.
"""
import polars as pl

from neuron.load import load, tables


def policy_column(frame: pl.DataFrame) -> str | None:
    """The policy number column of a legacy table (`XX_POLNR`).

    None for the tables without policies, like the products or the fund prices.
    """
    return next((col for col in frame.columns if col.endswith("_POLNR")), None)


def timeline(policy_id: str) -> dict[str, pl.DataFrame]:
    """{table: rows of the policy `policy_id`} for every table with a policy number column.

    The tables come in alphabetical order, each with its rows in the order of the export.
    """
    rows = {}
    for name in tables():
        frame = load(name)
        col = policy_column(frame)
        if col:
            rows[name] = frame.filter(pl.col(col).eq(policy_id))
    return rows
