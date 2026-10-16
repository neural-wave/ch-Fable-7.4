"""Neuron migration challenge: the rules of Neuron as code, calculated from the export in `legacy_dir`.

Each function gets the folder `legacy_dir` with the NR*.csv files and returns the calculated values. Dates are
`datetime.date`, amounts are `decimal.Decimal`. The rules found for each task are in the docstrings and README.md.

Check the solution locally against the train targets with `python check.py`.
"""
import datetime as dt
from decimal import Decimal

import polars as pl

from legacy import table, valid_on
from money import francs, share

REVERSAL = 900  # event type that reverses the event EV_REVNR
SINGLE_PREMIUM = "E"  # payment frequency PH_FREQ of single premium policies


def received_premiums(legacy_dir) -> pl.DataFrame:
    """Premium items whose money was received and whose receipt was not reversed.

    The money date PR_RCVDT is 0 while nothing was received. A later event 900 can reverse the receipt event
    PR_EVTNR: then the money counts as not received.
    """
    events = table(legacy_dir, "NREVNT")
    reversals = events.filter(pl.col("EV_EVTTP").eq(REVERSAL)).select("EV_POLNR", "EV_REVNR")
    items = table(legacy_dir, "NRPREM").filter(pl.col("PR_RCVDT").gt(0))
    return items.join(reversals, left_on=["PR_POLNR", "PR_EVTNR"], right_on=["EV_POLNR", "EV_REVNR"], how="anti")


def premium_type() -> pl.Expr:
    """Premium type PAYTP of the commission rates NRCOMR, from the payment frequency of the policy.

    E for single premium policies (frequency E), L for regular premiums.
    """
    single = pl.col("PH_FREQ").eq(SINGLE_PREMIUM)
    return pl.when(single).then(pl.lit("E")).otherwise(pl.lit("L")).alias("PAYTP")


def commission_rates(legacy_dir, items: pl.DataFrame) -> pl.DataFrame:
    """`items` with the commission rate CR_RATE that is valid on their money date PR_RCVDT.

    The rate depends on the tier of the broker of the policy version valid on that date and on the premium
    type. NRCOMR has no version numbers, so the newest start date wins there.
    """
    policies = valid_on(items, table(legacy_dir, "NRPOLH"), {"PR_POLNR": "PH_POLNR"}, "PR_RCVDT", "PH")
    brokers = policies.join(table(legacy_dir, "NRBROK"), left_on="PH_BRKNR", right_on="BR_BRKNR")
    return valid_on(brokers.with_columns(premium_type()), table(legacy_dir, "NRCOMR"),
                    {"BR_TIER": "CR_TIER", "PAYTP": "CR_PAYTP"}, "PR_RCVDT", "CR", newest="VLDFR")


def t0_commission(legacy_dir) -> dict[tuple[str, int], Decimal]:
    """{(policy_id, due_nr): commission} of every premium item received and not reversed.

    Commission = received amount PR_AMTRC x rate, rounded half up to the cent. The rate comes from NRCOMR by
    - the tier of the broker of the policy version valid on the money date PR_RCVDT (a broker change counts from
      its validity date, also when it was entered later), and
    - the premium type: E for single premium policies (frequency E), L for regular premiums.
    """
    rated = commission_rates(legacy_dir, received_premiums(legacy_dir))
    commissions = rated.select("PR_POLNR", "PR_DUENR", francs(share(pl.col("PR_AMTRC"), pl.col("CR_RATE"))))
    return {(policy, due_nr): commission for policy, due_nr, commission in commissions.iter_rows()}


def t1_next_due_dates(legacy_dir, extract_date: dt.date) -> dict[tuple[str, int], tuple[dt.date, dt.date]]:
    """{(policy_id, n): (due_date, collection_date)} for the due dates after `extract_date`, n = 1, 2, ..."""
    return {}


def t2_projected_maturity_value(legacy_dir) -> dict[str, Decimal]:
    """{policy_id: maturity_value}"""
    return {}


def t3_surrender_value(legacy_dir, valuation_dates: list[dt.date]) -> dict[tuple[str, dt.date], Decimal]:
    """{(policy_id, valuation_date): surrender_value}"""
    return {}


def t4_annual_statement(legacy_dir) -> dict[tuple[str, int], tuple[Decimal, ...]]:
    """{(policy_id, year): (premiums, entry_charges, admin_fees, management_fees, risk_charges, total_charges)}"""
    return {}


def t5_outlier_detection(legacy_dir, targets_dir) -> set[tuple[str, object]]:
    """{(task, key)} of the values that were changed by hand.

    `targets_dir` holds the target files (t0 to t4) of the policies to check, in the format of `targets/`. This is
    the only function that may read target files. Example keys: ("t2_projected_maturity_value", "BL10000042"),
    ("t4_annual_statement", ("BL10000042", 2021)).
    """
    return set()
