"""The policies of the extract with the parameters of their tariffs, as the tasks t2 to t4 read them."""
from neuron import grouped, keyed, table, valid

from .insured import Insured


class Portfolio:
    """Policy versions (NRPOLH), risks, insured persons, brokers and the tariff parameters."""

    def __init__(self, legacy_dir):
        self.policies = grouped(table(legacy_dir, "NRPOLH"), "PH_POLNR")
        self.risks = keyed(table(legacy_dir, "NRRISK"), "RK_POLNR")
        self.persons = keyed(table(legacy_dir, "NRPERS"), "PS_PERNR")
        self.brokers = keyed(table(legacy_dir, "NRBROK"), "BR_BRKNR")
        self.tariffs = grouped(table(legacy_dir, "NRCHRG"), "CG_TARFAM", "CG_TARGEN")
        self.entry_rates = grouped(table(legacy_dir, "NRENTC"), "EC_TIER")
        self.mortality = keyed(table(legacy_dir, "NRMORT"), "MO_TABID", "MO_SEX", "MO_AGE")

    def offer(self, policy_id):
        """The first version of a policy: the offer the customer signed."""
        return min(self.policies[policy_id], key=lambda version: version["PH_VRSNR"])

    def tariff(self, policy_id, day_):
        """The NRCHRG charges valid on `day_` of the tariff family RK_TARKEY[0:2] and generation RK_TARKEY[3:5]."""
        tariff_key = self.risks[policy_id]["RK_TARKEY"]
        return valid(self.tariffs[tariff_key[:2], tariff_key[3:5]], "CG", day_)

    def entry_rate(self, version, day_):
        """The entry charge rate valid on `day_` for the tier of the broker of a policy version."""
        tier = self.brokers[version["PH_BRKNR"]]["BR_TIER"]
        return valid(self.entry_rates[tier], "EC", day_)["EC_RATE"]

    def insured(self, policy_id):
        """The insured person of the risk of a policy."""
        risk = self.risks[policy_id]
        return Insured(risk, self.persons[risk["RK_PERNR"]], self.mortality)
