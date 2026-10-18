"""Market data of the funds: unit prices (NRFPRC) and exchange rates (NRFXRT)."""
from neuron import first_after, on_or_before, table


class Market:
    """Unit prices and exchange rates, read once per run.

    A restated price replaces the earlier publication (latest FP_CHGTS). Exchange rates are CHF per unit; NRFXRT
    also has some currency codes in lower case.
    """

    def __init__(self, legacy_dir):
        restated_last = sorted(table(legacy_dir, "NRFPRC"), key=lambda row: row["FP_CHGTS"])
        self.prices = {(row["FP_FNDID"], row["FP_PRCDT"]): row for row in restated_last}
        self.rates = {(row["FX_CCY"].upper(), row["FX_RATDT"]): row["FX_RATE"] for row in table(legacy_dir, "NRFXRT")}
        self.price_days, self.rate_days = days_by_name(self.prices), days_by_name(self.rates)
        self.currency = {row["FD_FNDID"]: row["FD_CCY"] for row in table(legacy_dir, "NRFUND")}

    def price_day(self, fund, day_, after=False):
        """The last price date of the fund on or before `day_`, or with `after` the first one after it.

        A day without a price uses the price before it; premiums are invested on the first price date after the
        money date.
        """
        return (first_after if after else on_or_before)(self.price_days[fund], day_)

    def price(self, fund, day_, side="FP_BIDPR"):
        """The bid (redemption) or FP_ASKPR (issue) price that is valid on `day_`."""
        return self.prices[fund, self.price_day(fund, day_)][side]

    def rate(self, currency, day_):
        """CHF per unit of `currency` on the last rate date on or before `day_`."""
        return self.rates[currency, on_or_before(self.rate_days[currency], day_)]


def days_by_name(series):
    """{name: sorted days} of a dict keyed by (name, day)."""
    days = {}
    for name, day_ in sorted(series):
        days.setdefault(name, []).append(day_)
    return days
