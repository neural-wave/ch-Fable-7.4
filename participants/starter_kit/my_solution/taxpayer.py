"""The residence of the policyholder, the tax rates and the tax currency, as Neuron knew them at a booking (t7).

NRHOLD names the policyholder of a policy and NRADDR the residence of a person, both with versions. Neuron took
the versions valid on the effective date TB_EFFDT among those entered up to its processing timestamp TB_CHGTS
(`legacy.valid_on` with `known_at`): an address entered later for the past does not change a booking made before
(BL10000487 event 96 contradicts today's view, never the view at the booking). The rates NRTAXR are looked up the
same way, so the Bollo batches of 2017 to 2019 used the rate version 1 and the fix of July 2019 the version 2.

Every function takes rows with the columns TB_POLNR, TB_EFFDT and TB_CHGTS, like NRTAXB.
"""
import polars as pl

from conventions import CONVERSION, ROUNDING, TAXES
from legacy import as_date, table, valid_on
from market import exchange_rates, rate_of
from tariff import signed_policies

RESIDENCE = ["AD_CNTRY", "AD_REGIO", "AD_TAXST", "AD_CHURCH"]  # the address columns that the taxes or their checks read


PROCESSED = pl.col("TB_CHGTS").floordiv(1_000_000).cast(pl.String).str.to_date("%Y%m%d")  # the day of TB_CHGTS


def processed_by_neuron_ng(day: pl.Expr = PROCESSED) -> pl.Expr:
    """True where Neuron NG processed the row: `day`, the day of its timestamp TB_CHGTS, is from CONVERSION on."""
    return day.ge(CONVERSION)


def rounds_half_up(country: pl.Expr, modes: dict[str, str] = ROUNDING, day: pl.Expr = PROCESSED) -> pl.Expr:
    """True where Neuron rounds an amount of `country` half up, false where it truncates to the cent.

    The mode of the country in `modes` (`conventions.ROUNDING`) decides: "system", the system that processed the
    row on `day` (`processed_by_neuron_ng`): COBOL truncated, Neuron NG rounds half up; "truncate" always;
    "half_up" always.
    """
    mode = country.replace_strict(modes, default="system")
    return pl.when(mode.eq("system")).then(processed_by_neuron_ng(day)).otherwise(mode.eq("half_up"))


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

    The rate is that of the country of the tax type (TX_CNTRY, `conventions.TAXES`), the key of NRTAXR. Only the
    versions entered up to the column `known_at` count. With `region`, a column of `rows`, a rate of that region
    (KIS of Bavaria and Baden-Wuerttemberg) wins over the rate for all regions (TX_REGIO blank).
    """
    numbered = rows.with_row_index("ROW").with_columns(
        TX_TAXTP=tax_type, TX_CNTRY=tax_type.replace_strict(TAXES, default=None),
        TX_REGIO=pl.col(region) if region else pl.lit(None, pl.String))
    rates = table(legacy_dir, "NRTAXR")
    regional = rate_versions(numbered, rates.drop_nulls("TX_REGIO"), ["TX_CNTRY", "TX_TAXTP", "TX_REGIO"], known_at)
    general = rate_versions(numbered, rates.filter(pl.col("TX_REGIO").is_null()), ["TX_CNTRY", "TX_TAXTP"], known_at)
    found = numbered.join(regional, on="ROW", how="left").join(general, on="ROW", how="left", suffix="_ALL")
    return found.with_columns(pl.coalesce("TX_RATE", "TX_RATE_ALL").alias(name)).drop(
        "ROW", "TX_TAXTP", "TX_CNTRY", "TX_REGIO", "TX_RATE", "TX_RATE_ALL")


def blended_rates(legacy_dir, rows: pl.DataFrame, tax_type: pl.Expr, name: str, start: str = "PH_BEGDT",
                  known_at: str = "TB_CHGTS") -> pl.DataFrame:
    """`rows` with the column `name`: the rate of `tax_type` averaged over the days from `start` to TB_EFFDT, each
    day at the rate valid on it (millionths, rounded half up), as the Italian substitute tax takes the gain of every
    period at the rate of the period. Equal to the rate of TB_EFFDT when no day falls before a change.

    Only the versions entered up to the column `known_at` count; of several versions valid on the same days the
    highest version wins, as in `legacy.valid_on`.
    """
    numbered = rows.with_row_index("ROW")
    keys = numbered.select("ROW", start, "TB_EFFDT", known_at, TX_TAXTP=tax_type)
    rates = table(legacy_dir, "NRTAXR").filter(pl.col("TX_REGIO").is_null())
    spans = keys.join(rates, on="TX_TAXTP").filter(pl.col("TX_CHGTS").le(pl.col(known_at)))
    spans = spans.sort("TX_VRSNR").unique(["ROW", "TX_VLDFR"], keep="last")
    first = pl.max_horizontal(as_date(start), as_date("TX_VLDFR"))
    last = pl.min_horizontal(as_date("TB_EFFDT"), as_date("TX_VLDTO").fill_null(as_date("TB_EFFDT")))
    days = last.sub(first).dt.total_days().add(1).clip(0)
    weighted = spans.with_columns(DAYS=days).group_by("ROW").agg(
        RATE_DAYS=pl.col("DAYS").cast(pl.Int128).mul(pl.col("TX_RATE")).sum(), DAYS=pl.col("DAYS").sum())
    blended = pl.col("RATE_DAYS").add(pl.col("DAYS").floordiv(2)).floordiv(pl.col("DAYS").clip(1))
    return numbered.join(weighted, on="ROW", how="left").with_columns(blended.cast(pl.Int64).alias(name)).drop(
        "ROW", "RATE_DAYS", "DAYS")


def with_policies(legacy_dir, rows: pl.DataFrame) -> pl.DataFrame:
    """`rows` with the currency PH_CCY, the start date PH_BEGDT and the premium frequency PH_FREQ of the policy; no
    version ever changes them.

    A row of an unknown policy stays, with nulls: its amounts become null instead of disappearing.
    """
    policies = signed_policies(legacy_dir).select(TB_POLNR="PH_POLNR", PH_CCY="PH_CCY", PH_BEGDT="PH_BEGDT",
                                                  PH_FREQ="PH_FREQ")
    return rows.join(policies, on="TB_POLNR", how="left")


def with_tax_currency(legacy_dir, rows: pl.DataFrame, currency: pl.Expr, date: str = "TB_EFFDT") -> pl.DataFrame:
    """`rows` (with PH_CCY) with TAX_CCY = `currency` and the rates RP of PH_CCY and RT of TAX_CCY on `date`.

    An amount of the policy currency is amount x RP / RT in the tax currency (`market`: francs per unit). The
    euro has rates from 31.12.1998 on; for the days before, the first rate stands in (an assumption).
    """
    policy = rate_of(legacy_dir, rows.with_columns(TAX_CCY=currency), "PH_CCY", date, "RP", same_day=True)
    tax = rate_of(legacy_dir, policy, "TAX_CCY", date, "RT", same_day=True)
    firsts = exchange_rates(legacy_dir).group_by(TAX_CCY="FX_CCY").agg(
        FIRST=pl.col("FX_RATE").sort_by("FX_RATDT").first())
    return tax.join(firsts, on="TAX_CCY", how="left").with_columns(RT=pl.coalesce("RT", "FIRST")).drop("FIRST")
