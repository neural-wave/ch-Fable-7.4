"""The charge rules of one unit-linked policy: agreements, pots, and the charges of a monthly charge run."""
from neuron import add_months, era_rounding, first_valid, grouped, is_cobol
from policies.risk import risk_charge

from .fees import management_fee, pot
from .splitting import net_values, split

POT_RATE = {"1": "CG_AMCP1", "2": "CG_AMCP2"}  # management charge of pot 1 (initial units) and pot 2


class ChargeRules:
    """The charges of a policy, from its offer, its insured person and its individual agreements (NRAGRE).

    The money received in the first `initial_months` of the product buys initial units (pot 1).
    """

    def __init__(self, offer, insured, agreements, initial_months):
        self.offer, self.start, self.insured = offer, offer["PH_BEGDT"], insured
        self.agreements = grouped(agreements, "AG_FEETP")
        self.initial_end = add_months(self.start, initial_months)

    def agreed_rate(self, fee_type, day_, default):
        """The rate of the first agreement of a fee type (ENT, AMC) valid on `day_`, else the `default` rate."""
        agreement = first_valid(self.agreements.get(fee_type, []), "AG", day_)
        return agreement["AG_RATE"] if agreement else default

    def pot(self, received):
        """The pot of the units that a premium received on a day buys."""
        return pot(received, self.initial_end)

    def monthly_charges(self, tariff, values, day_):
        """{charge: {holding: amount}} of a charge run: admin fee, management charge and risk charge, in this order.

        `values` are the values of the holdings. The admin fee and the risk charge are split by value; the risk
        charge sees the value after the admin fee and the management charge.
        """
        rounding = era_rounding(day_)
        admin = split(tariff["CG_ADMFEE"], values, rounding)
        management = {key: management_fee(value, self.agreed_rate("AMC", day_, tariff[POT_RATE[key[1]]]),
                                          self.start, day_) for key, value in values.items()}
        net = net_values(values, admin, management)
        risk = split(self.risk_charge(tariff, sum(net.values()), day_), net, rounding)
        return {"admin": admin, "management": management, "risk": risk}

    def risk_charge(self, tariff, value, day_):
        """The monthly risk charge of the policy value, at most the value left (BL10004387, December 2020)."""
        insured_age = self.insured.policy_year_age(self.start, day_, is_cobol(self.offer["PH_APPDT"]))
        return min(risk_charge(self.insured, tariff, value, insured_age, era_rounding(day_)), max(value, 0))
