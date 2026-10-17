"""The offer that the projection illustrates (task t2), as it stood on the application date.

The offer is the first version of the policy. Its figures are the ones valid on the
application date PH_APPDT: the tariff, the illustration rate of NRILLU and the entry
charge of the tier of the broker of the offer. No agreement applies to an offer, and the
application date also decides the rounding.
"""
import dataclasses
import datetime as dt
from decimal import Decimal

import export
from accounting import purchase
from core import lookup
from insurance import ages


@dataclasses.dataclass(frozen=True)
class Offer:
    """The figures of an offer.

    `premium` is the premium after the entry charge, `rate` the yearly illustration rate
    and `age` the insurance age at the start.
    """

    day: dt.date
    frequency: str
    premium: Decimal
    tariff: dict
    rate: Decimal
    age: int


def offer(data, contract):
    """The `Offer` of a policy."""
    first = min(data.versions[contract.policy_id], key=export.VERSION)
    day, tier = first["PH_APPDT"], data.tiers[first["PH_BRKNR"]]
    entry = lookup.valid_on(data.entry_rates[tier], day, "EC_VLDFR", "EC_VLDTO")["EC_RATE"]
    _, premium = purchase.invested(first["PH_PREMI"], 1, entry, day)
    rate = lookup.valid_on(data.illustration, day, "IL_VLDFR", "IL_VLDTO")["IL_RATE"]
    age = ages.insured_age(data, contract, contract.start)
    return Offer(day, first["PH_FREQ"], premium, data.tariff(contract.policy_id, day), rate, age)
