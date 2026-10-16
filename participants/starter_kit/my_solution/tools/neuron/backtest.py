"""Backtesting of t1: the due dates of the submission for a past extract date against the real ones in NRPREM.

The targets of t1 cover one year and the train policies only. The past due dates PR_DUEDT are free labels for
every policy, public ones included: pretend the export was taken on 30 June of an earlier year, compute the due
dates of the following year and compare them with the ones Neuron really created. Policies with a new version in
that year are left out, since the rule assumes that nothing changes after the extract date.
"""
import datetime as dt

import polars as pl

from legacy import as_date, table
from neuron.load import LEGACY
from submission import t1_next_due_dates


def due_lists(rows: pl.DataFrame, name: str) -> pl.DataFrame:
    """PR_POLNR and the sorted list of its due dates (column `due`) as the column `name`."""
    return rows.group_by("PR_POLNR").agg(pl.col("due").sort().alias(name))


def predicted_dues(extract: dt.date) -> pl.DataFrame:
    """PR_POLNR and due of every due date that the submission computes after `extract`."""
    rows = [(policy, due) for (policy, _), (due, _) in t1_next_due_dates(LEGACY, extract).items()]
    return pl.DataFrame(rows, schema=["PR_POLNR", "due"], orient="row")


def actual_dues(extract: dt.date, horizon: dt.date) -> pl.DataFrame:
    """PR_POLNR and due of every real due date PR_DUEDT after `extract`, up to and including `horizon`."""
    dues = table(LEGACY, "NRPREM").select("PR_POLNR", due=as_date("PR_DUEDT"))
    return dues.filter(pl.col("due").is_between(extract, horizon, closed="right"))


def backtest(extract: dt.date) -> dict:
    """How many policies get exactly their real due dates of the year after `extract`.

    A policy whose real list is shorter usually stopped paying in that year without a new version.
    """
    horizon = extract.replace(year=extract.year + 1)
    changed = table(LEGACY, "NRPOLH").filter(as_date("PH_VLDFR").is_between(extract, horizon, closed="right"))
    both = due_lists(predicted_dues(extract), "predicted").join(due_lists(actual_dues(extract, horizon), "actual"),
                                                                on="PR_POLNR", how="left")
    checked = both.filter(pl.col("PR_POLNR").is_in(changed["PH_POLNR"].implode()).not_())
    same = checked.filter(pl.col("predicted").eq(pl.col("actual")).fill_null(False))
    return {"extract": extract, "policies": checked.height, "identical": same.height}


def backtests(years: range = range(2008, 2026)) -> pl.DataFrame:
    """`backtest` for 30 June of every year in `years`."""
    return pl.DataFrame([backtest(dt.date(year, 6, 30)) for year in years])
