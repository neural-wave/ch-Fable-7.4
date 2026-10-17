"""The projection of an offer: the maturity value it showed the customer, month by month (t2)."""
from decimal import Decimal

from neuron import era_rounding, is_cobol, months_between, valid

from .codes import MONTHS_PER_DUE
from .projection_month import next_month


class Projection:
    """The offer of one policy with the tariff, the entry charge and the growth rate of its application date.

    The COBOL version (offers applied before the system change) cuts the cents off, Neuron NG rounds half up.
    """

    def __init__(self, portfolio, policy_id, illustration_rates):
        self.offer = portfolio.offer(policy_id)
        applied, self.start = self.offer["PH_APPDT"], self.offer["PH_BEGDT"]
        self.tariff, self.insured = portfolio.tariff(policy_id, applied), portfolio.insured(policy_id)
        self.entry_rate = portfolio.entry_rate(self.offer, applied)
        self.yearly_rate = valid(illustration_rates, "IL", applied)["IL_RATE"]  # the growth of the illustration
        self.rounding, self.entry_age = era_rounding(applied), self.insured.entry_age(self.start, is_cobol(applied))
        self.months_per_due = MONTHS_PER_DUE.get(self.offer["PH_FREQ"])  # None: a single premium

    def maturity_value(self):
        """The value at the end date, after the months from the start date to the month before the end date."""
        value = Decimal(0)
        for month in range(months_between(self.start, self.offer["PH_ENDDT"])):
            value = next_month(self, value, month)
        return value
