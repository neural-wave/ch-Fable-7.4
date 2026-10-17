"""Neuron migration challenge: the formulas found by the lab pipeline (clustering + optimal trees + exact score).

Each function gets the folder `legacy_dir` with the NR*.csv files and returns the calculated values.
Dates are `datetime.date`, amounts are `decimal.Decimal`. Every value is calculated from `legacy_dir`; only
t5 reads target files. The shared helpers (typed tables, versions, rounding) are in `neuron.py`.
"""
import datetime as dt
from decimal import Decimal

from neuron import cents, grouped, keyed, read_targets, table, valid


def t0_commission(legacy_dir):
    """amount = PR_AMTRC x NRCOMR.CR_RATE[CR_TIER = BR_TIER@PR_RCVDT, CR_PAYTP = RK_TARKEY[6]], ROUND_HALF_UP.

    Lab candidate C3.1.1: 225848 / 225858 train rows exact (holdout 44051 / 44052).
    """
    commission_rates = keyed(table(legacy_dir, "NRCOMR"), "CR_TIER", "CR_PAYTP")
    policy_headers = grouped(table(legacy_dir, "NRPOLH"), "PH_POLNR")
    brokers = keyed(table(legacy_dir, "NRBROK"), "BR_BRKNR")
    insured_risks = keyed(table(legacy_dir, "NRRISK"), "RK_POLNR")
    result = {}
    for premium_item in table(legacy_dir, "NRPREM"):
        if premium_item["PR_STATE"] == "P":
            policy_header = valid(policy_headers[premium_item["PR_POLNR"]], "PH", premium_item["PR_RCVDT"])
            broker = brokers[policy_header["PH_BRKNR"]]
            insured_risk = insured_risks[premium_item["PR_POLNR"]]
            commission_rate = commission_rates[broker["BR_TIER"], insured_risk["RK_TARKEY"][5]]["CR_RATE"]
            result[premium_item["PR_POLNR"], premium_item["PR_DUENR"]] = cents(premium_item["PR_AMTRC"] * commission_rate)
    return result


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


CHECKED = {  # task: (function, key converters, value converters) of the tasks whose rules are implemented
    "t0_commission": (t0_commission, (str, int), (Decimal,)),
}


def t5_outlier_detection(legacy_dir, targets_dir) -> set[tuple[str, object]]:
    """{(task, key)} of the target values that differ from the rules: the values that were changed by hand."""
    outliers = set()
    for task, (rule, key_types, value_types) in CHECKED.items():
        computed = rule(legacy_dir)
        for key, value in read_targets(targets_dir, task, key_types, value_types).items():
            if key in computed and computed[key] != value:
                outliers.add((task, key))
    return outliers
