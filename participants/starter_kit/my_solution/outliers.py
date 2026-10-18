"""Outlier detection (t5): the target values that were changed by hand.

The rules of t0 to t4 reproduce every value that Neuron calculated. Each train value that they miss is right in
every step before it (t2 every policy year, t3 every booking, holding and policy value, t4 the other columns of
the row) and differs by whole francs: a manual correction, most of them listed in NREXCP. So a target value that
differs from its rule is an outlier. t1 has none: its values are the dates of the schedule, and no correction in
NREXCP concerns them.

The rules give their values as tables in the format of the target files, with the amounts in cents (`TARGETS`).
"""
import pathlib

import polars as pl

TARGETS = {  # target file -> its key columns and its amount columns
    "t0_commission": (["policy_id", "due_nr"], ["amount"]),
    "t2_projected_maturity_value": (["policy_id"], ["maturity_value"]),
    "t3_surrender_value": (["policy_id", "valuation_date"], ["surrender_value"]),
    "t4_annual_statement": (["policy_id", "year"], ["premiums", "entry_charges", "admin_fees", "management_fees",
                                                    "risk_charges", "total_charges"]),
}
CENTS = 100  # an amount of a target file has two decimals


def target_table(targets_dir, task: str) -> pl.DataFrame:
    """The target file of `task`: its keys (dates parsed, policy_id without blanks) and its amounts in cents.

    The amounts are read as text and converted exactly, never through floats.
    """
    keys, amounts = TARGETS[task]
    text = dict.fromkeys(["policy_id", *amounts], pl.String)
    frame = pl.read_csv(pathlib.Path(targets_dir, f"{task}.csv"), schema_overrides=text, try_parse_dates=True)
    cents = [pl.col(amount).cast(pl.Decimal(38, 2)).mul(CENTS).cast(pl.Int64) for amount in amounts]
    return frame.select(pl.col("policy_id").str.strip_chars(), *keys[1:], *cents)


def outliers(task: str, expected: pl.DataFrame, predicted: pl.DataFrame) -> set[tuple[str, tuple]]:
    """(task, key) of the rows of `expected` whose amounts differ from the rule's amounts in `predicted`.

    Both tables have the columns of TARGETS. A key that the rule does not give is no outlier: there is no value
    of the rule to differ from.
    """
    keys, amounts = TARGETS[task]
    rule = predicted.select(*keys, *amounts)
    both = expected.cast(dict(rule.select(keys).schema)).join(rule, on=keys, suffix="_RULE")
    changed = both.filter(pl.any_horizontal([pl.col(amount).ne(pl.col(f"{amount}_RULE")) for amount in amounts]))
    return {(task, key) for key in changed.select(keys).iter_rows()}
