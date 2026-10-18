"""The bookings of one policy replayed on its fund account: premiums, charge runs and customer orders."""
import bisect
from collections import defaultdict

from neuron import latest, valid
from .account import FundAccount
from policies.codes import CHARGE_RUN, SALES, SWITCH

from .bookings import PROCESSING_ORDER, event_bookings, premium_bookings
from .charges import ChargeRules
from .fees import net_premium


class PolicyAccounting:
    """The bookings of one policy on its FundAccount, with the tables of a FundAccounting.

    `snapshots` keeps the units at the end of the requested days, `charges` the charges booked on each
    (calendar year of the booking day, charge).
    """

    def __init__(self, accounting, policy_id):
        self.accounting, self.policy_id = accounting, policy_id
        self.versions, self.offer = accounting.policies[policy_id], accounting.offer(policy_id)
        self.rules = ChargeRules(self.offer, accounting.insured(policy_id), accounting.agreements.get(policy_id, []),
                                 accounting.products[self.offer["PH_PRDCD"]]["PD_INIMON"])
        self.account = FundAccount(accounting.market, latest(self.versions, "PH")["PH_CCY"])
        self.snapshots, self.charges = {}, defaultdict(list)

    def replay(self, days):
        """Processes the bookings in the PROCESSING_ORDER and keeps the units at the end of each of `days`.

        Only the days from the start of the policy count. The units of a day are taken before the first booking
        of a later day, so they include the bookings of the day itself.
        """
        pending = sorted(days)
        pending = pending[bisect.bisect_left(pending, self.offer["PH_BEGDT"]):]
        for booking in sorted(self.bookings(), key=PROCESSING_ORDER):
            complete = bisect.bisect_left(pending, booking.day)
            self.keep(pending[:complete])
            pending = pending[complete:]
            booking.apply(booking.day)
        self.keep(pending)

    def keep(self, days):
        """Keeps the current units as the units at the end of each of `days`."""
        if days:
            self.snapshots.update(dict.fromkeys(days, dict(self.account.units)))

    def bookings(self):
        """The bookings of the events and of the paid premiums, each with the handler that books it."""
        handlers = {CHARGE_RUN: self.charge_run, SWITCH: self.switch, **dict.fromkeys(SALES, self.sell)}
        tables, policy_id = self.accounting, self.policy_id
        return [*event_bookings(tables.events.get(policy_id, []), handlers),
                *premium_bookings(tables.premiums.get(policy_id, []), tables.allocations.get(policy_id, []),
                                  tables.market, self.invest)]

    def record(self, charge, day_, amount):
        """Records a charge in the calendar year of its booking day."""
        self.charges[day_.year, charge].append(amount)

    def invest(self, premium, share, trade_day):
        """The premium share net of the entry charge buys units of the fund, in the pot of its money date.

        The entry charge is the agreed one, otherwise the one of the broker tier on the money date.
        """
        received = premium["PR_RCVDT"]
        tier_rate = self.accounting.entry_rate(valid(self.versions, "PH", received), received)
        entry_rate = self.rules.agreed_rate("ENT", received, tier_rate)
        net, entry_charge = net_premium(premium["PR_AMTRC"], share["AL_PCTG"], entry_rate, trade_day)
        self.record("entry", trade_day, entry_charge)
        self.account.invest((share["AL_FNDID"], self.rules.pot(received)), net, trade_day)

    def sell(self, event, trade_day):
        """Withdrawal, surrender or death claim: EV_PCTG of the units of every holding are sold."""
        for key in self.account.holdings():
            self.account.sell(key, event["EV_PCTG"], trade_day)

    def switch(self, event, trade_day):
        """EV_PCTG of the units of each pot of EV_FNDID buy units of EV_TOFND in the same pot, at the bid price."""
        for key in self.account.holdings_of(event["EV_FNDID"]):
            amount = self.account.sell(key, event["EV_PCTG"], trade_day)
            self.account.book((event["EV_TOFND"], key[1]), amount, trade_day)

    def charge_run(self, event, trade_day):
        """Books the monthly charges of the holdings (see `ChargeRules.monthly_charges`).

        Each charge of each holding is a booking of its own, with its own unit rounding.
        """
        keys = self.account.holdings()
        if keys:
            values = {key: self.account.prices.worth(key[0], self.account.units[key], trade_day) for key in keys}
            charges = self.rules.monthly_charges(self.accounting.tariff(self.policy_id, trade_day), values, trade_day)
            for name, parts in charges.items():
                self.record(name, trade_day, sum(parts.values()))
            for key in keys:
                for parts in charges.values():
                    self.account.cancel(key, parts[key], trade_day)
