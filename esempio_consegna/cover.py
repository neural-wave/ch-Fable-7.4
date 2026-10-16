"""Sum at risk: what the death cover pays on top of the policy value.

Option RK_TARKEY[6]: A 1 % of the value, B the sum insured above it, C the sum insured.
"""
import conventions as c


def sum_at_risk(option, insured, value):
    """Sum at risk of `option` for a sum `insured` and a policy `value`."""
    return {"A": value * c.VALUE_AT_RISK, "B": max(insured - value, 0), "C": insured}[option]
