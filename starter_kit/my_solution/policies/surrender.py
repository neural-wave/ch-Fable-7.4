"""The surrender value of a policy: its value after the surrender penalty (NRSURR, NRWAIV)."""
from decimal import Decimal

from neuron import cents, era_rounding, table

from .codes import is_closed


class Penalties:
    """The surrender penalties of NRSURR and the waiver periods of NRWAIV."""

    def __init__(self, legacy_dir):
        self.rates = {(row["SR_SCALE"], row["SR_YEAR"]): row["SR_RATE"] for row in table(legacy_dir, "NRSURR")}
        self.waivers = table(legacy_dir, "NRWAIV")

    def rate(self, scale, policy_year, day_):
        """The penalty rate of a scale in a policy year.

        It is 0 when the scale has no rate for the year, and in a waiver period, which waives the penalty of
        every policy on the days it is valid.
        """
        if any(waiver["WV_VLDFR"] <= day_ <= waiver["WV_VLDTO"] for waiver in self.waivers):
            return 0
        return self.rates.get((scale, policy_year), 0)


def surrender_value(version, policy_value, penalty, day_):
    """The policy value after the penalty, rounded in the era of the valuation day.

    Surrendered and death claim policies have nothing left to surrender, and the value is never negative.
    """
    if is_closed(version):
        return Decimal(0)
    return max(cents(policy_value * (1 - penalty), era_rounding(day_)), Decimal(0))
