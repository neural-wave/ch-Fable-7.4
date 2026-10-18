"""t3: the surrender value of the policies on the valuation dates."""
from funds import FundAccounting
from neuron import policy_years, valid
from policies.surrender import Penalties, surrender_value


def t3_surrender_value(legacy_dir, valuation_dates):
    """{(policy_id, valuation_date): surrender_value} of the policies started on or before the valuation date.

    policy value = sum of units x bid price x FX per fund and pot, each rounded to the cent;
    surrender value = policy value x (1 - NRSURR penalty of the product scale and the completed policy years),
    no penalty in an NRWAIV period, 0 for surrendered and death claim policies and for a negative value.
    """
    accounting, penalties = FundAccounting(legacy_dir), Penalties(legacy_dir)
    result = {}
    for policy_id, versions in accounting.policies.items():
        policy = accounting.replay(policy_id, valuation_dates)
        for valuation_date, units in policy.snapshots.items():
            version = valid(versions, "PH", valuation_date)
            policy_value = sum(policy.account.prices.worth(fund, unit_count, valuation_date)
                               for (fund, _), unit_count in units.items())
            scale = accounting.products[version["PH_PRDCD"]]["PD_SRPSCL"]
            penalty = penalties.rate(scale, policy_years(policy.offer["PH_BEGDT"], valuation_date), valuation_date)
            result[policy_id, valuation_date] = surrender_value(version, policy_value, penalty, valuation_date)
    return result
