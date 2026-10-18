"""The prices of fund units in the currency of a policy: bid or ask price x the cross rate via CHF."""
from neuron import cents, era_rounding

REDEMPTION, ISSUE = "FP_BIDPR", "FP_ASKPR"  # NRFPRC: units are sold at the bid and bought at the ask price


class PolicyPrices:
    """The market data seen from a policy currency.

    NRFXRT gives every rate in CHF per unit, so a fund in EUR is valued in a USD policy via CHF.
    """

    def __init__(self, market, currency):
        self.market, self.currency = market, currency

    def fx(self, fund, day_):
        """Units of the policy currency per unit of the fund currency on `day_`.

        The cross rate is the CHF rate of the fund currency / the CHF rate of the policy currency.
        """
        return self.market.rate(self.market.currency[fund], day_) / self.market.rate(self.currency, day_)

    def worth(self, fund, units, day_):
        """Redemption value of `units` of a fund on `day_`: units x bid price x the cross rate, to the cent."""
        fx = self.fx(fund, day_)
        return cents(units * self.market.price(fund, day_) * fx, era_rounding(day_))

    def unit_price(self, fund, day_, side=REDEMPTION, fx_day=None):
        """The price of one unit on `day_` in the policy currency.

        The bid (REDEMPTION) or ask (ISSUE) price of the day, converted with the exchange rate of `fx_day`, by
        default the same day.
        """
        return self.market.price(fund, day_, side) * self.fx(fund, fx_day or day_)
