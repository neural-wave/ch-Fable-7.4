"""The residence of the policyholder, the tax rates and the tax currency, as Neuron knew them at a booking (t7).

NRHOLD names the policyholder of a policy and NRADDR the residence of a person, both with versions. Neuron took
the versions valid on the effective date TB_EFFDT among those entered up to its processing timestamp TB_CHGTS
(`legacy.valid_on` with `known_at`): an address entered later for the past does not change a booking made before
(BL10000487 event 96 contradicts today's view, never the view at the booking). The rates NRTAXR are looked up the
same way, so the Bollo batches of 2017 to 2019 used the rate version 1 and the fix of July 2019 the version 2.

Every function takes rows with the columns TB_POLNR, TB_EFFDT and TB_CHGTS, like NRTAXB.
"""
import polars as pl

from legacy import table, valid_on
from market import exchange_rates, rate_of
from tariff import signed_policies

RESIDENCE = ["AD_CNTRY", "AD_REGIO", "AD_TAXST", "AD_CHURCH"]  # the address columns that the taxes read


def residences(legacy_dir, rows: pl.DataFrame) -> pl.DataFrame:
    """`rows` with the holder HD_PERNR and the columns RESIDENCE of the address, null when Neuron knew none."""
    numbered = rows.with_row_index("ROW")
    holders = valid_on(numbered, table(legacy_dir, "NRHOLD"), {"TB_POLNR": "HD_POLNR"}, "TB_EFFDT", "HD",
                       known_at="TB_CHGTS")
    addresses = valid_on(holders, table(legacy_dir, "NRADDR"), {"HD_PERNR": "AD_PERNR"}, "TB_EFFDT", "AD",
                         known_at="TB_CHGTS")
    return numbered.join(holders.select("ROW", "HD_PERNR"), on="ROW", how="left").join(
        addresses.select("ROW", *RESIDENCE), on="ROW", how="left").drop("ROW")


def rate_versions(rows: pl.DataFrame, rates: pl.DataFrame, keys: list[str], known_at: str) -> pl.DataFrame:
    """ROW and TX_RATE of the rate of `rates` with the same `keys` valid on TB_EFFDT, as known at `known_at`."""
    found = valid_on(rows, rates, dict(zip(keys, keys, strict=True)), "TB_EFFDT", "TX", known_at=known_at)
    return found.select("ROW", "TX_RATE")


def tax_rates(legacy_dir, rows: pl.DataFrame, tax_type: pl.Expr, name: str, known_at: str = "TB_CHGTS",
              region: str | None = None) -> pl.DataFrame:
    """`rows` with the column `name`: the rate (millionths) of `tax_type` valid on TB_EFFDT, null without one.

    Only the versions entered up to the column `known_at` count. With `region`, a column of `rows`, a rate of
    that region (KIS of Bavaria and Baden-Wuerttemberg) wins over the rate for all regions (TX_REGIO blank).
    """
    numbered = rows.with_row_index("ROW").with_columns(TX_TAXTP=tax_type,
                                                       TX_REGIO=pl.col(region) if region else pl.lit(None, pl.String))
    rates = table(legacy_dir, "NRTAXR")
    regional = rate_versions(numbered, rates.drop_nulls("TX_REGIO"), ["TX_TAXTP", "TX_REGIO"], known_at)
    general = rate_versions(numbered, rates.filter(pl.col("TX_REGIO").is_null()), ["TX_TAXTP"], known_at)
    found = numbered.join(regional, on="ROW", how="left").join(general, on="ROW", how="left", suffix="_ALL")
    return found.with_columns(pl.coalesce("TX_RATE", "TX_RATE_ALL").alias(name)).drop(
        "ROW", "TX_TAXTP", "TX_REGIO", "TX_RATE", "TX_RATE_ALL")


def with_policies(legacy_dir, rows: pl.DataFrame) -> pl.DataFrame:
    """`rows` with the currency PH_CCY and the start date PH_BEGDT of the policy; no version ever changes them."""
    policies = signed_policies(legacy_dir).select(TB_POLNR="PH_POLNR", PH_CCY="PH_CCY", PH_BEGDT="PH_BEGDT")
    return rows.join(policies, on="TB_POLNR")


def with_tax_currency(legacy_dir, rows: pl.DataFrame, currency: pl.Expr) -> pl.DataFrame:
    """`rows` (with PH_CCY) with TAX_CCY = `currency` and the rates RP of PH_CCY and RT of TAX_CCY on TB_EFFDT.

    An amount of the policy currency is amount x RP / RT in the tax currency (`market`: francs per unit). The
    euro has rates from 31.12.1998 on; for the payouts before, the first rate stands in (an assumption).
    """
    policy = rate_of(legacy_dir, rows.with_columns(TAX_CCY=currency), "PH_CCY", "TB_EFFDT", "RP", same_day=True)
    tax = rate_of(legacy_dir, policy, "TAX_CCY", "TB_EFFDT", "RT", same_day=True)
    firsts = exchange_rates(legacy_dir).group_by(TAX_CCY="FX_CCY").agg(
        FIRST=pl.col("FX_RATE").sort_by("FX_RATDT").first())
    return tax.join(firsts, on="TAX_CCY", how="left").with_columns(RT=pl.coalesce("RT", "FIRST")).drop("FIRST")
