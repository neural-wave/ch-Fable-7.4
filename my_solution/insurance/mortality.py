"""Yearly mortality rate of the insured: the qx of the tariff's table, with the loading.

The sex is the 3rd character of the tariff key (M, W, or U for the sex of the person).
The loading is 1 + RK_LOAD, times the smoker factor of the tariff for smokers.
"""
import conventions as c


def death_rate(export, contract, tariff, age):
    """Yearly mortality rate of the insured at `age`, with the loading of the policy."""
    insured = export.risks[contract.policy_id]
    person = export.persons[insured["RK_PERNR"]]
    sex = c.SEX.get(insured["RK_TARKEY"][c.SEX_POSITION], person["PS_SEX"])
    smoker = tariff["CG_SMKFAC"] if person["PS_SMOKE"] == c.SMOKER else 1
    return export.mortality[tariff["CG_MORTTB"], sex, age] * (1 + insured["RK_LOAD"]) * smoker
