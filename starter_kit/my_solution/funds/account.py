"""The units of one policy per (fund, pot), booked in the policy currency."""
import datetime as dt
from collections import defaultdict
from decimal import Decimal

from neuron import era_rounding

from .prices import ISSUE, PolicyPrices

UNIT = Decimal("0.000001")  # units are booked with 6 decimals
ONE_DAY = dt.timedelta(days=1)


class FundAccount:
    """{(fund, pot): units}, with the prices of the funds in the currency of the policy.

    Every booking rounds its units like the era of its day: cut off by COBOL, half up by Neuron NG.
    """

    def __init__(self, market, currency):
        self.prices, self.units = PolicyPrices(market, currency), defaultdict(Decimal)

    def holdings(self):
        """The (fund, pot) keys that hold units; a holding that was sold out keeps 0 units."""
        return [key for key, units in self.units.items() if units > 0]

    def holdings_of(self, fund):
        """The (fund, pot) keys of one fund that hold units."""
        return [key for key in self.holdings() if key[0] == fund]

    def book(self, key, amount, day_, **price):
        """Buys (amount > 0) or cancels (amount < 0) the units of an amount in the policy currency.

        Charges and switches are booked at the bid price and the exchange rate of the day; `price` can choose
        another side and exchange rate day (see `PolicyPrices.unit_price`).
        """
        unit_price = self.prices.unit_price(key[0], day_, **price)
        self.units[key] += (amount / unit_price).quantize(UNIT, era_rounding(day_))

    def cancel(self, key, amount, day_):
        """Cancels the units of a charge amount at the bid price."""
        self.book(key, -amount, day_)

    def invest(self, key, amount, day_):
        """Buys units with a premium: at the ask price, with the exchange rate of the day before."""
        self.book(key, amount, day_, side=ISSUE, fx_day=day_ - ONE_DAY)

    def sell(self, key, share, day_):
        """Sells a share of the units of a holding and returns the amount at the bid price.

        The units sold are rounded first; the amount is the value of the rounded units.
        """
        units = -(self.units[key] * share).quantize(UNIT, era_rounding(day_))
        self.units[key] += units
        return -self.prices.worth(key[0], units, day_)
