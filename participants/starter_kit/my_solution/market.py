"""Market data: unit prices and exchange rates, each the last one on or before a date.

- prices are sometimes restated: the latest publication (FP_CHGTS) of a fund and day counts
- exchange rates are CHF per unit of a currency; a cross rate goes via CHF. Some currency codes are written in
  lower case (profile check `case_variants`), so codes are compared in upper case
"""
import functools

import polars as pl

from legacy import table


@functools.cache
def prices(legacy_dir) -> pl.DataFrame:
    """The unit prices of every fund and price day, latest publication only, sorted by day."""
    latest = table(legacy_dir, "NRFPRC").sort("FP_CHGTS").unique(["FP_FNDID", "FP_PRCDT"], keep="last")
    return latest.sort("FP_PRCDT")


@functools.cache
def rates(legacy_dir) -> pl.DataFrame:
    """FX_CCY (upper case), FX_RATDT and FX_RATE (CHF per unit), sorted by day."""
    rows = table(legacy_dir, "NRFXRT").with_columns(pl.col("FX_CCY").str.to_uppercase())
    return rows.unique(["FX_CCY", "FX_RATDT"], keep="last").sort("FX_RATDT")


def price_on(legacy_dir, rows: pl.DataFrame, fund: str, day: str) -> pl.DataFrame:
    """`rows` with FP_PRCDT, FP_BIDPR, FP_ASKPR and FP_MIDPR: the last price of `fund` on or before `day`."""
    ordered = rows.with_row_index("ROW").sort(day)
    found = ordered.join_asof(prices(legacy_dir).drop("FP_CHGTS"), left_on=day, right_on="FP_PRCDT", by_left=fund,
                              by_right="FP_FNDID", strategy="backward", check_sortedness=False)
    return found.sort("ROW").drop("ROW")


def rate_on(legacy_dir, rows: pl.DataFrame, currency: str, day: str, name: str) -> pl.DataFrame:
    """`rows` with `name`: CHF per unit of the currency column `currency`, the last rate on or before `day`."""
    keyed = rows.with_row_index("ROW").with_columns(FX_CCY=pl.col(currency).str.to_uppercase()).sort(day)
    found = keyed.join_asof(rates(legacy_dir).rename({"FX_RATE": name}), left_on=day, right_on="FX_RATDT",
                            by="FX_CCY", strategy="backward", check_sortedness=False)
    return found.sort("ROW").drop("ROW", "FX_CCY", "FX_RATDT")


def price_day_after(legacy_dir, rows: pl.DataFrame, fund: str, day: str, name: str) -> pl.DataFrame:
    """`rows` with `name`: the first day after `day` with a price of `fund`."""
    ordered = rows.with_row_index("ROW").with_columns(NEXT_DAY=pl.col(day).dt.offset_by("1d")).sort("NEXT_DAY")
    days = prices(legacy_dir).select("FP_FNDID", name=pl.col("FP_PRCDT")).rename({"name": name})
    found = ordered.join_asof(days, left_on="NEXT_DAY", right_on=name, by_left=fund, by_right="FP_FNDID",
                              strategy="forward", check_sortedness=False, coalesce=False)
    return found.sort("ROW").drop("ROW", "NEXT_DAY", "FP_FNDID", strict=False)
