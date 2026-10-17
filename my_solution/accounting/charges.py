"""The monthly charge run of a policy: ADM, AMC and RSK on one monthly anniversary.

A run sees the units traded before its day and charges ADM and AMC on the values before the
run. ADM is the fixed monthly fee of the tariff (CG_ADMFEE), shared by the positions in
proportion to their value and never more than the policy value. The AMC of each position
is charged at the yearly rate of its pot (CG_AMCP1, CG_AMCP2), or at the rate agreed for the
policy (NRAGRE AMC), see fees.py. The risk charge is computed on what is left after them, in
total, and shared by the positions in proportion to what is left in each. Every charge takes
units out at the bid price of the run day. A run with no position worth anything charges
nothing: the end of the runs.
"""
import collections

import conventions as c
from accounting import fees, sharing
from core import money
from insurance import ages, risk


def admin_fees(tariff, values, day):
    """{position: ADM} of the run on `day`."""
    return sharing.pro_rata(min(tariff["CG_ADMFEE"], sum(values.values())), values, day)


def management_fees(export, contract, tariff, values, day):
    """{position: AMC} of the run on `day`."""
    agreed = export.agreement(contract.policy_id, c.AMC_AGREEMENT, day)
    rates = {pot: agreed["AG_RATE"] if agreed else tariff[column] for pot, column in c.AMC_RATES.items()}
    share, basis = fees.period(contract.start, day)
    return money.positive({position: fees.amc(value, rates[position[1]], share, basis, day) for position, value in values.items()})


def charge(export, contract, account, values, day):
    """The ADM, AMC and RSK bookings of a run on positions worth `values`."""
    tariff = export.tariff(contract.policy_id, day)
    admin, management = admin_fees(tariff, values, day), management_fees(export, contract, tariff, values, day)
    left = collections.Counter(values)
    left.subtract(admin)
    left.subtract(management)
    total = risk.monthly_charge(export, contract, tariff, sum(left.values()), ages.insured_age(export, contract, day), day)
    pieces = ((c.ADMIN, admin), (c.MANAGEMENT, management), (c.RISK, sharing.pro_rata(total, money.positive(left), day)))
    return [account.charge(kind, position, amount, day) for kind, split in pieces for position, amount in split.items()]


def run(export, contract, account, day):
    """The bookings of the run on `day`; none when no position is worth anything."""
    values = account.values(day)
    if values:
        return charge(export, contract, account, values, day)
    return []
