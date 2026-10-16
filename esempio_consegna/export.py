"""The data of the Neuron export that the accounting reads, grouped by policy once.

`Export` holds the reference tables (tariffs, rates, mortality, market) and the data of every
policy; `Contract` gathers what the accounting needs to know of one policy. Start, end,
currency and initial period come from the first version, the surrender scale from the last;
a policy is closed from the first version in a closed state (surrendered or death).
"""
import dataclasses
import datetime as dt
import functools
import operator

import ages
import conventions as c
import legacy
import lookup
import market
import months
import orders
import portfolio
import premiums

VERSION = operator.itemgetter("PH_VRSNR")


@dataclasses.dataclass(frozen=True)
class Contract:
    """One policy: `pot_limit` ends the initial period, `closed` is the day it was closed."""

    policy_id: str
    start: dt.date
    end: dt.date
    currency: str
    pot_limit: dt.date
    scale: int
    closed: dt.date


class Export:
    """Reference data and policy data of one export folder, ready to look up."""

    def __init__(self, legacy_dir):
        table = functools.partial(legacy.table, legacy_dir)
        self.versions = portfolio.versions(legacy_dir)
        self.premiums = lookup.group(premiums.paid_items(legacy_dir), "PR_POLNR")
        self.orders = orders.customer_orders(legacy_dir)
        self.market = market.Market(legacy_dir)
        self.births = ages.births(legacy_dir)
        self.risks = {row["RK_POLNR"]: row for row in table("NRRISK")}
        self.persons = {row["PS_PERNR"]: row for row in table("NRPERS")}
        self.products = {row["PD_PRDCD"]: row for row in table("NRPROD")}
        self.tiers = {row["BR_BRKNR"]: row["BR_TIER"] for row in table("NRBROK")}
        self.allocations = lookup.group(table("NRALLO"), "AL_POLNR")
        self.agreements = lookup.group(table("NRAGRE"), "AG_POLNR", "AG_FEETP")
        self.entry_rates = lookup.group(table("NRENTC"), "EC_TIER")
        self.tariffs = lookup.group(table("NRCHRG"), "CG_TARFAM", "CG_TARGEN")
        self.mortality = {(r["MO_TABID"], r["MO_SEX"], r["MO_AGE"]): r["MO_QX"] for r in table("NRMORT")}
        self.surrender_rates = {(r["SR_SCALE"], r["SR_YEAR"]): r["SR_RATE"] for r in table("NRSURR")}
        self.waivers = table("NRWAIV")
        self.illustration = table("NRILLU")

    def contract(self, policy_id):
        """The `Contract` of a policy, from its versions."""
        history = self.versions[policy_id]
        first, last = min(history, key=VERSION), max(history, key=VERSION)
        states = lookup.group(history, "PH_STATE")
        closed = min((version["PH_VLDFR"] for state in c.CLOSED for version in states.get(state, [])), default=dt.date.max)
        pot_limit = months.add_months(first["PH_BEGDT"], self.products[first["PH_PRDCD"]]["PD_INIMON"])
        scale = self.products[last["PH_PRDCD"]]["PD_SRPSCL"]
        return Contract(policy_id, first["PH_BEGDT"], first["PH_ENDDT"], first["PH_CCY"], pot_limit, scale, closed)

    def agreement(self, policy_id, fee, day):
        """The NRAGRE row that replaces a tariff rate of the policy on `day`, or None."""
        return lookup.valid_on(self.agreements.get((policy_id, fee), []), day, "AG_VLDFR", "AG_VLDTO")

    def tariff(self, policy_id, day):
        """The NRCHRG row of the tariff of the policy valid on `day` (family and generation)."""
        key = self.risks[policy_id]["RK_TARKEY"]
        return lookup.valid_on(self.tariffs[key[:2], key[3:5]], day, "CG_VLDFR", "CG_VLDTO")


@functools.cache
def load(legacy_dir):
    """The `Export` of a folder, read once."""
    return Export(legacy_dir)
