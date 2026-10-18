"""The monthly risk charge for the death benefit of the cover (NRRISK, NRMORT, NRCHRG)."""
from neuron import cents

SUM_AT_RISK = {  # RK_TARKEY[6], the death benefit of the cover
    "A": lambda value, sum_insured: value / 100,  # the value plus 1 %
    "B": lambda value, sum_insured: max(sum_insured - value, 0),  # the value, at least the sum insured
    "C": lambda value, sum_insured: sum_insured,  # the value plus the sum insured
}


def risk_charge(insured, tariff, value, insured_age, rounding):
    """Sum at risk x qx x (1 + loading) x smoker factor / 12, for a policy `value`.

    qx is the death rate of the mortality table of the tariff for the sex and the age of the insured; the
    loading RK_LOAD comes from the underwriting of the risk.
    """
    risk = insured.risk
    death_rate = insured.mortality[tariff["CG_MORTTB"], insured.sex, insured_age]["MO_QX"]
    smoker_factor = tariff["CG_SMKFAC"] if insured.smoker else 1
    sum_at_risk = SUM_AT_RISK[risk["RK_TARKEY"][6]](value, risk["RK_SUMIN"])
    return cents(sum_at_risk * death_rate * (1 + risk["RK_LOAD"]) * smoker_factor / 12, rounding)
