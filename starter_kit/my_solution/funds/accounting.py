"""The tables of the fund accounting, and the replay of the bookings of one policy on them."""
from neuron import grouped, keyed, table
from policies.portfolio import Portfolio

from .market import Market
from .replay import PolicyAccounting


class FundAccounting(Portfolio):
    """The portfolio with its products, market data, allocations, agreements, events and premiums."""

    def __init__(self, legacy_dir):
        super().__init__(legacy_dir)
        self.market = Market(legacy_dir)
        self.products = keyed(table(legacy_dir, "NRPROD"), "PD_PRDCD")
        self.agreements = grouped(table(legacy_dir, "NRAGRE"), "AG_POLNR")
        self.allocations = grouped(table(legacy_dir, "NRALLO"), "AL_POLNR")
        self.events = grouped(table(legacy_dir, "NREVNT"), "EV_POLNR")
        self.premiums = grouped(table(legacy_dir, "NRPREM"), "PR_POLNR")

    def replay(self, policy_id, days):
        """The accounting of one policy, replayed to the end, with its units at the end of each of `days`."""
        policy = PolicyAccounting(self, policy_id)
        policy.replay(days)
        return policy
