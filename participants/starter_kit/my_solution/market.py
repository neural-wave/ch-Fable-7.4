"""Market data: the unit prices of the funds and the exchange rates, as Neuron knew them on a date.

- A fund has a price on its pricing days only. A booking or a valuation takes the last price date on or before
  its date (the price date BK_PRCDT of NRBOOK is always that day), and of that day the last publication
  FP_CHGTS: a corrected price replaces the first one.
- Exchange rates FX_RATE are francs per unit of a currency (CHF itself is 1). Some rows have the currency in
  lower case; they are the same currencies.
- An amount in the policy currency PH_CCY is worth amount x RP / RF in the fund currency FD_CCY, where RP and RF
  are the rates of the two currencies.
"""
import functools

import polars as pl

from legacy import table


@functools.cache
def unit_prices(legacy_dir) -> pl.DataFrame:
    """FP_FNDID, FP_PRCDT, FP_BIDPR and FP_ASKPR (millionths): the last publication of every fund and price date."""
    prices = table(legacy_dir, "NRFPRC").sort("FP_CHGTS").unique(["FP_FNDID", "FP_PRCDT"], keep="last")
    return prices.select("FP_FNDID", "FP_PRCDT", "FP_BIDPR", "FP_ASKPR").sort("FP_PRCDT")


@functools.cache
def exchange_rates(legacy_dir) -> pl.DataFrame:
    """FX_CCY (upper case), FX_RATDT and FX_RATE (millionths of a franc per unit of the currency)."""
    rates = table(legacy_dir, "NRFXRT").with_columns(pl.col("FX_CCY").str.to_uppercase())
    return rates.sort("FX_RATDT")


def with_prices(legacy_dir, frame: pl.DataFrame, date: str) -> pl.DataFrame:
    """`frame` with FP_BIDPR and FP_ASKPR of its fund BK_FNDID on the last price date on or before its column `date`."""
    return frame.sort(date).join_asof(unit_prices(legacy_dir), left_on=date, right_on="FP_PRCDT",
                                      by_left="BK_FNDID", by_right="FP_FNDID", check_sortedness=False)


def rate_of(legacy_dir, frame: pl.DataFrame, currency: str, date: str, name: str, same_day: bool) -> pl.DataFrame:
    """`frame` with the column `name`: the last rate of its column `currency` on or before its column `date`.

    Without `same_day`, the rate must be from a day before `date`: the rates of that day are not known yet.
    """
    rates = exchange_rates(legacy_dir).rename({"FX_CCY": currency, "FX_RATE": name})
    return frame.sort(date).join_asof(rates, left_on=date, right_on="FX_RATDT", by=currency,
                                      allow_exact_matches=same_day, check_sortedness=False).drop("FX_RATDT")


def with_exchange_rates(legacy_dir, frame: pl.DataFrame, date: str, same_day: bool) -> pl.DataFrame:
    """`frame` with RP and RF: the rates of the policy currency PH_CCY and of the fund currency FD_CCY (`rate_of`)."""
    policy = rate_of(legacy_dir, frame, "PH_CCY", date, "RP", same_day)
    return rate_of(legacy_dir, policy, "FD_CCY", date, "RF", same_day)
