"""Fund prices and exchange rates, looked up the way Neuron did.

NRFPRC keeps every publication of a price: when a price was restated, the latest one (by
FP_CHGTS) is the price of that day. NRFXRT gives the CHF value of one unit of each currency;
80 of its rows carry the code in lower case ('usd') and Neuron used them as well. A lookup on
a day takes the last value published on or before that day.
"""
import bisect

from legacy import tables


def series(points):
    """{key: (days, values)} sorted by day, from {(key, day): value}.

    `values` starts with None, the value before the first day, so that the value on a day
    sits at the position bisect gives for that day.
    """
    out = {}
    for (key, day), value in sorted(points.items()):
        days, values = out.setdefault(key, ([], [None]))
        days.append(day)
        values.append(value)
    return out


def last_on(table, key, day, before=False):
    """The value of `key` on the last day on or before `day` (strictly before if `before`)."""
    days, values = table[key]
    return values[(bisect.bisect_left if before else bisect.bisect_right)(days, day)]


class Market:
    """Bid and ask prices of the funds and CHF rates of the currencies, over time."""

    def __init__(self, legacy_dir):
        published = sorted(tables.table(legacy_dir, "NRFPRC"), key=lambda row: row["FP_CHGTS"])
        self.prices = series({(r["FP_FNDID"], r["FP_PRCDT"]): (r["FP_BIDPR"], r["FP_ASKPR"]) for r in published})
        rates = tables.table(legacy_dir, "NRFXRT")
        self.rates = series({(r["FX_CCY"].upper(), r["FX_RATDT"]): r["FX_RATE"] for r in rates})
        self.currency = {r["FD_FNDID"]: r["FD_CCY"] for r in tables.table(legacy_dir, "NRFUND")}

    def bid(self, fund, day):
        """Bid price of a fund on `day`: what Neuron pays for a unit it takes out."""
        return last_on(self.prices, fund, day)[0]

    def ask(self, fund, day):
        """Ask price of a fund on `day`: what a premium pays for a unit."""
        return last_on(self.prices, fund, day)[1]

    def next_price_day(self, fund, day):
        """The first day after `day` with a price of the fund: the trade date of a premium."""
        days = self.prices[fund][0]
        return days[bisect.bisect_right(days, day)]

    def chf(self, currency, day, before=False):
        """CHF value of one unit of `currency` on `day`, or on the day before if `before`."""
        return last_on(self.rates, currency, day, before)
