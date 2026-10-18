"""The fund value of a policy on a day and the premiums it has paid, from the unit accounting of `funds`."""
import datetime as dt
import functools
from decimal import Decimal

from funds import FundAccounting
from policies.codes import is_paid

from .amounts import ZERO

CENT = Decimal("0.01")


@functools.cache
def fund_accounting(legacy_dir):
    """The unit accounting of the extract.

    Built once per legacy folder: both t7 tasks and all their events and years share it.
    """
    return FundAccounting(legacy_dir)


@functools.cache
def fund_value(legacy_dir, policy_id, day_):
    """(fund value, paid premiums / 100) of a policy on `day_`.

    The fund value is the bid value of the units held at the end of `day_`. On a day that sells every unit
    (a surrender) the units of the day before count, at the prices of `day_`.
    """
    accounting = fund_accounting(legacy_dir)
    policy = accounting.replay(policy_id, [day_])
    units = policy.snapshots.get(day_, {})
    if sum(units.values()) == 0:
        units = units_before(accounting, policy_id, day_)
    value = sum((holding_value(accounting, policy, fund, unit_count, day_)
                 for (fund, _), unit_count in units.items() if unit_count and unit_count > 0), ZERO)
    return value, paid_premiums(accounting.premiums.get(policy_id, [])) / 100


def units_before(accounting, policy_id, day_):
    """The units of a policy at the end of the day before `day_`.

    They give the fund value of a surrender day, whose bookings have sold every unit by the end of the day.
    """
    day_before = day_ - dt.timedelta(days=1)
    return accounting.replay(policy_id, [day_before]).snapshots.get(day_before, {})


def holding_value(accounting, policy, fund, unit_count, day_):
    """units x bid price x FX of a holding on `day_`, rounded to the cent.

    The rounding is the default of `decimal` (half even), not the half up of `neuron.cents`.
    """
    return (unit_count * accounting.market.price(fund, day_) * policy.account.prices.fx(fund, day_)).quantize(CENT)


def paid_premiums(premiums):
    """The sum of PR_AMTRC of the paid premium items that have a day the money was received."""
    return sum((premium["PR_AMTRC"] for premium in premiums if is_paid(premium) and premium["PR_RCVDT"]), ZERO)
