"""Investment of the premiums (PRM): how a paid premium becomes fund units.

Everything is decided on the money date PR_RCVDT: the allocation (the highest version valid
on that day), the entry charge and the pot. Each fund buys on its first price day after the
money date, at the ask price and with the exchange rate of the day before the trade.
The entry charge is the NRAGRE ENT rate of the policy, otherwise the NRENTC rate of the tier
of the broker who holds the policy on the money date. The arithmetic is in purchase.py and
trades.py.
"""
import account
import conventions as c
import lookup
import portfolio
import purchase
import trades


def entry_rate(export, policy_id, day):
    """Share of a premium received on `day` that Neuron keeps as entry charge."""
    agreed = export.agreement(policy_id, c.ENTRY_AGREEMENT, day)
    if agreed:
        return agreed["AG_RATE"]
    tier = export.tiers[portfolio.version_on(export.versions[policy_id], day)["PH_BRKNR"]]
    return lookup.valid_on(export.entry_rates[tier], day, "EC_VLDFR", "EC_VLDTO")["EC_RATE"]


def allocation(export, policy_id, day):
    """{fund: share} of the highest allocation version valid on `day`."""
    valid = lookup.valid_rows(export.allocations[policy_id], day, "AL_VLDFR", "AL_VLDTO")
    newest = lookup.group(valid, "AL_VRSNR")[max(row["AL_VRSNR"] for row in valid)]
    return {row["AL_FNDID"]: row["AL_PCTG"] for row in newest}


def buy(market, currency, position, premium, share, entry, received):
    """The PRM booking of one fund of a premium received on `received`."""
    fund = position[0]
    trade = market.next_price_day(fund, received)
    gross, net = purchase.invested(premium, share, entry, trade)
    return account.Booking(trade, c.PREMIUM, position, net, trades.bought(market, currency, fund, net, trade), gross)


def invest(export, contract, item):
    """The PRM bookings of one paid premium item, one per fund of the allocation."""
    received = item["PR_RCVDT"]
    entry, pot = entry_rate(export, contract.policy_id, received), purchase.pot(contract, received)
    funds = allocation(export, contract.policy_id, received)
    return [buy(export.market, contract.currency, (fund, pot), item["PR_AMTRC"], share, entry, received) for fund, share in funds.items()]


def bookings(export, contract):
    """The PRM bookings of all paid premiums of a policy."""
    return [booking for item in export.premiums.get(contract.policy_id, []) for booking in invest(export, contract, item)]
