"""Neuron migration challenge: the rules of Neuron as code, calculated from the export in `legacy_dir`.

Every rule here was found by the discovery loop in `tools/detective` and cites its finding (README.md).
"""
import datetime as dt

import polars as pl

from accounting import accounting, holdings
from commission import commissions
from money import francs
from outliers import outliers
from projection import maturity_values
from schedule import next_due_dates
from statement import LAST_YEAR, statements
from surrender import surrender_values


def t0_commission(legacy_dir):
    """{(policy_id, due_nr): commission} of every premium item received and not reversed (`commission`)."""
    rows = commissions(legacy_dir).with_columns(francs(pl.col("amount")))
    return {(policy, due_nr): amount for policy, due_nr, amount in rows.iter_rows()}


def t1_next_due_dates(legacy_dir, extract_date):
    """{(policy_id, n): (due_date, collection_date)} of the year after `extract_date` (`schedule`)."""
    rows = next_due_dates(legacy_dir, extract_date)
    return {(policy, n): (due, collection) for policy, n, due, collection in rows.iter_rows()}


def t2_projected_maturity_value(legacy_dir):
    """{policy_id: maturity_value} as the offer projected it (`projection`)."""
    rows = maturity_values(legacy_dir).with_columns(francs(pl.col("maturity_value")))
    return dict(rows.iter_rows())


def t3_surrender_value(legacy_dir, valuation_dates):
    """{(policy_id, valuation_date): surrender_value} of the simulated fund accounting (`accounting`, `surrender`)."""
    held = holdings(accounting(legacy_dir, max(valuation_dates)), valuation_dates)
    rows = surrender_values(legacy_dir, held).select("BK_POLNR", "VALUATION", francs(pl.col("SURRENDER_VALUE")))
    return {(policy, day): value for policy, day, value in rows.iter_rows()}


def t4_annual_statement(legacy_dir):
    """{(policy_id, year): (premiums, entry_charges, admin_fees, management_fees, risk_charges, total_charges)} of
    the simulated fund accounting (`accounting`, `statement`)."""
    bookings = accounting(legacy_dir, dt.date(LAST_YEAR, 12, 31))
    rows = statements(legacy_dir, bookings).with_columns(francs(pl.exclude("BK_POLNR", "YEAR")))
    return {(policy, year): amounts for policy, year, *amounts in rows.iter_rows()}


def t5_outlier_detection(legacy_dir, targets_dir):
    """{(task, key)} of the target values in `targets_dir` that differ from the rules by whole francs
    (`outliers`)."""
    return outliers(legacy_dir, targets_dir)
