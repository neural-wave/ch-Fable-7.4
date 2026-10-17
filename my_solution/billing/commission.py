"""Broker commission (task t0).

Rule: the broker who holds the policy on the day the money arrives (PR_RCVDT) earns a share
of the received amount (PR_AMTRC). The share is the NRCOMR rate of the broker's tier for the
premium type of the tariff, E for single and L for regular premiums.

Evidence on the train policies: 225,848 of 225,858 commissions exact. The broker on the due
date gives 225,846, the first broker 224,130. The 10 other rows differ by whole francs:
they were changed by hand and belong to task t5.
"""
from core import lookup, money
from legacy import portfolio, premiums, tables


def calculator(legacy_dir):
    """The commission of one paid premium item, as a function of the item.

    Broker and rate are both the ones valid on the money date of the item.
    """
    versions, kinds = portfolio.versions(legacy_dir), premiums.premium_types(legacy_dir)
    tiers = {row["BR_BRKNR"]: row["BR_TIER"] for row in tables.table(legacy_dir, "NRBROK")}
    rates = lookup.group(tables.table(legacy_dir, "NRCOMR"), "CR_TIER", "CR_PAYTP")

    def commission(item):
        policy, received = item["PR_POLNR"], item["PR_RCVDT"]
        tier = tiers[portfolio.version_on(versions[policy], received)["PH_BRKNR"]]
        rate = lookup.valid_on(rates[tier, kinds[policy]], received, "CR_VLDFR", "CR_VLDTO")
        return money.cents(item["PR_AMTRC"] * rate["CR_RATE"], received)

    return commission
