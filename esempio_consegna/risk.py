"""Risk charge (RSK): the monthly price of the death cover, taken from the value.

    charge = sum at risk x qx(mortality table, sex, insurance age) x loading / 12

The sex is the 3rd character of the tariff key (M, W, or U for the sex of the person).
The value is the policy value less the ADM and AMC of the same month (cover.py). The
loading is 1 + RK_LOAD, times the smoker factor of the tariff for smokers. The charge
never takes more than that value.
"""
import conventions as c
import cover
import money


def death_rate(export, contract, tariff, age):
    """Yearly mortality rate of the insured at `age`, with the loading of the policy."""
    insured = export.risks[contract.policy_id]
    person = export.persons[insured["RK_PERNR"]]
    sex = c.SEX.get(insured["RK_TARKEY"][c.SEX_POSITION], person["PS_SEX"])
    smoker = tariff["CG_SMKFAC"] if person["PS_SMOKE"] == c.SMOKER else 1
    return export.mortality[tariff["CG_MORTTB"], sex, age] * (1 + insured["RK_LOAD"]) * smoker


def monthly_charge(export, contract, tariff, value, age, day):
    """The risk charge of a month for a policy `value` after ADM and AMC, at `age`."""
    insured = export.risks[contract.policy_id]
    at_risk = cover.sum_at_risk(insured["RK_TARKEY"][c.OPTION_POSITION], insured["RK_SUMIN"], value)
    charge = money.cents(at_risk * death_rate(export, contract, tariff, age) / c.MONTHS_PER_YEAR, day)
    return min(charge, max(value, 0))
