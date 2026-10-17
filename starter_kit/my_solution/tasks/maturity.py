"""t2: the maturity value that the offer projected, month by month from the start to the end date."""
from neuron import table
from policies.portfolio import Portfolio
from policies.projection import Projection


def t2_projected_maturity_value(legacy_dir):
    """{policy_id: maturity_value} of every insured risk, projected with the parameters of the offer.

    The offer is the first policy version, with the parameters valid on its application date (NRILLU gives
    the growth rate of the projection).
    """
    portfolio = Portfolio(legacy_dir)
    illustration_rates = table(legacy_dir, "NRILLU")
    return {policy_id: Projection(portfolio, policy_id, illustration_rates).maturity_value()
            for policy_id in portfolio.risks}
