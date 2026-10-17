"""Risk charge (RSK): the monthly price of the death cover, taken from the value.

    charge = sum at risk x qx(mortality table, sex, insurance age) x loading / 12

The value is the policy value less the ADM and AMC of the same month (cover.py); the
yearly rate with its loading is in mortality.py. The charge never takes more than the value.
"""
import conventions as c
from core import money
from insurance import cover, mortality


def monthly_charge(export, contract, tariff, value, age, day):
    """The risk charge of a month for a policy `value` after ADM and AMC, at `age`."""
    insured = export.risks[contract.policy_id]
    at_risk = cover.sum_at_risk(insured["RK_TARKEY"][c.OPTION_POSITION], insured["RK_SUMIN"], value)
    charge = money.cents(at_risk * mortality.death_rate(export, contract, tariff, age) / c.MONTHS_PER_YEAR, day)
    return min(charge, max(value, 0))
