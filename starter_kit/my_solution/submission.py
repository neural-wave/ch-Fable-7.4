"""Neuron migration challenge: the formulas found by the lab pipeline (clustering + optimal trees + exact score).

Each function gets the folder `legacy_dir` with the NR*.csv files and returns the calculated values.
Dates are `datetime.date`, amounts are `decimal.Decimal`. Every value is calculated from `legacy_dir`; only
t5 reads target files. t0 is generated here by `lab freeze`; t1 to t4 are in the package `tasks`, written
with the rules of `policies` and `funds` and the helpers of `neuron`.
"""
from neuron import cents, grouped, keyed, table, valid
from tasks import t1_next_due_dates, t2_projected_maturity_value, t3_surrender_value, t4_annual_statement
from tasks.outliers import outliers

__all__ = ["t0_commission", "t1_next_due_dates", "t2_projected_maturity_value", "t3_surrender_value",
           "t4_annual_statement", "t5_outlier_detection"]


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


def t5_outlier_detection(legacy_dir, targets_dir):
    """{(task, key)} of the target values that differ from the rules: the values that were changed by hand.

    Every task is recalculated with its rule and compared with its target file (see `tasks.outliers`).
    """
    rules = {"t0_commission": t0_commission, "t1_next_due_dates": t1_next_due_dates,
             "t2_projected_maturity_value": t2_projected_maturity_value, "t3_surrender_value": t3_surrender_value,
             "t4_annual_statement": t4_annual_statement}
    return outliers(rules, legacy_dir, targets_dir)
