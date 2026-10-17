"""The amounts of the tax bookings of Neuron and the two tables of t7, in cents of the tax currency.

NRTAXB names every tax booking of Neuron with its type, event, effective date and processing timestamp; only the
amount is missing. So the rules do not decide again whether a tax was due: they calculate the amount of every
booking, with the rates valid on the effective date as Neuron knew them at the processing time (`taxpayer`).

- STP: the Swiss stamp duty on the premium of its event (the single premium, event 2), converted to francs
- VST, SOS: the taxable base of the payout (`payouts`) x the rate
- KST: the base x the rate; a church member pays base x KST / (1 + KST x KIS), section 32d EStG. SOL and KIS:
  the KST x their rate, KIS of the region of residence
- BOL, BOC: the Bollo (`bollo`)

Every amount is rounded once: half up, in Germany truncated (`conventions.TRUNCATED`).
"""
import functools
import math

import polars as pl

from bollo import bollo_bookings
from conventions import (ANNUAL_TAXES, CHURCH_MEMBER, CHURCH_REDUCED, CHURCH_TAX, PREMIUM_STAMP, REMITTANCE,
                         STAMP_DUTY, STAMP_DUTY_COUNTRY, SURCHARGES, TAX_CURRENCY, TAXES, TRUNCATED, WITHHELD)
from legacy import as_date, table
from money import RATE_UNIT, rounded
from payouts import EVENT, payouts
from taxpayer import tax_rates, with_policies, with_tax_currency

SHARE_OF_SHARE = math.prod([RATE_UNIT, RATE_UNIT])  # two rates in millionths multiplied
BOOKING = ["TB_POLNR", "TB_EVTNR", "TB_TAXTP", "TB_EFFDT"]  # the columns of a booking besides TB_AMOUNT
PAYOUT_AMOUNTS = {"withholding": WITHHELD, "surcharges": SURCHARGES, "stamp_duty": STAMP_DUTY}  # name -> types
ANNUAL_AMOUNTS = {f"{TAXES[tax].lower()}_{tax.lower()}": tax for tax in ANNUAL_TAXES}  # ch_stp -> STP, ...


def half_up(tax_type: pl.Expr) -> pl.Expr:
    """True where Neuron rounds the tax `tax_type` half up, false where it truncates (by its country)."""
    return tax_type.replace_strict(TAXES).is_in(TRUNCATED).not_()


def premium_stamp_duty(legacy_dir, bookings: pl.DataFrame) -> pl.DataFrame:
    """The STP `bookings` with TB_AMOUNT: the premium of their event, in francs, x the rate."""
    premiums = table(legacy_dir, "NRPREM").select(TB_POLNR="PR_POLNR", TB_EVTNR="PR_EVTNR",
                                                  PREMIUM=pl.coalesce("PR_AMTRC", "PR_AMTDU"))
    rows = with_policies(legacy_dir, bookings.join(premiums, on=EVENT))
    currency = pl.col("TB_TAXTP").replace_strict(TAXES).replace_strict(TAX_CURRENCY)
    rated = tax_rates(legacy_dir, with_tax_currency(legacy_dir, rows, currency), pl.col("TB_TAXTP"), "RATE")
    taxed = pl.col("PREMIUM").cast(pl.Int128).mul(pl.col("RP")).mul(pl.col("RATE"))
    whole = pl.col("RT").cast(pl.Int128).mul(RATE_UNIT)
    return rated.with_columns(TB_AMOUNT=rounded(taxed, whole, half_up(pl.col("TB_TAXTP"))))


def capital_gains_tax() -> pl.Expr:
    """The KST of the payout: base x KST_RATE, for a church member / (1 + KST_RATE x KIS_RATE)."""
    church = pl.when(pl.col("AD_CHURCH").eq(CHURCH_MEMBER)).then(pl.col("KIS_RATE").fill_null(0)).otherwise(0)
    taxed = pl.col("TAXABLE_BASE").cast(pl.Int128).mul(pl.col("KST_RATE")).mul(RATE_UNIT)
    whole = pl.lit(SHARE_OF_SHARE, pl.Int128).add(pl.col("KST_RATE").mul(church))
    return rounded(taxed, whole, half_up(pl.lit(CHURCH_REDUCED)))


def payout_taxes(legacy_dir, bookings: pl.DataFrame) -> pl.DataFrame:
    """The withholding taxes and surcharges of the payouts in `bookings` with TB_AMOUNT.

    VST and SOS are the base x their rate, SOL and KIS the KST x their rate.
    """
    residents = payouts(legacy_dir).select(*EVENT, "TAXABLE_BASE", "AD_REGIO", "AD_CHURCH")
    rows = tax_rates(legacy_dir, bookings.join(residents, on=EVENT), pl.col("TB_TAXTP"), "RATE", region="AD_REGIO")
    german = tax_rates(legacy_dir, rows, pl.lit(CHURCH_REDUCED), "KST_RATE")
    church = tax_rates(legacy_dir, german, pl.lit(CHURCH_TAX), "KIS_RATE", region="AD_REGIO")
    tax_type = pl.col("TB_TAXTP")
    taxed = pl.when(tax_type.is_in(SURCHARGES)).then("KST").otherwise("TAXABLE_BASE").cast(pl.Int128)
    amount = rounded(taxed.mul(pl.col("RATE")), RATE_UNIT, half_up(tax_type))
    return church.with_columns(KST=capital_gains_tax()).with_columns(
        TB_AMOUNT=pl.when(tax_type.eq(CHURCH_REDUCED)).then("KST").otherwise(amount))


@functools.cache
def tax_bookings(legacy_dir) -> pl.DataFrame:
    """Every tax booking of NRTAXB with the columns BOOKING and its TB_AMOUNT in cents of the tax currency."""
    bookings = table(legacy_dir, "NRTAXB").drop("TB_AMOUNT", "TB_REMDT")
    tax_type = pl.col("TB_TAXTP")
    calculated = [premium_stamp_duty(legacy_dir, bookings.filter(tax_type.eq(PREMIUM_STAMP))),
                  payout_taxes(legacy_dir, bookings.filter(tax_type.is_in([*WITHHELD, *SURCHARGES]))),
                  bollo_bookings(legacy_dir, bookings)]
    return pl.concat([part.select(*BOOKING, pl.col("TB_AMOUNT").cast(pl.Int64)) for part in calculated])


def remittance() -> pl.Expr:
    """The day Neuron paid the taxes of a payout to the tax office, null without tax.

    The country of the withholding decides, Italy for stamp duty alone; the day comes from REMITTANCE.
    """
    withheld = pl.col("withholding").add(pl.col("surcharges"))
    country = pl.when(withheld.ne(0)).then("AD_CNTRY").otherwise(pl.lit(STAMP_DUTY_COUNTRY))
    first = as_date("TB_EFFDT").dt.month_start().dt.offset_by("1mo")
    days = country.replace_strict(REMITTANCE, default=None, return_dtype=pl.Int64)
    return pl.when(withheld.add(pl.col("stamp_duty")).ne(0)).then(first.add(pl.duration(days=days)))


def payout_table(legacy_dir) -> pl.DataFrame:
    """policy_id, event_nr, country, taxable_base and the PAYOUT_AMOUNTS (cents), remittance_date of every payout."""
    tax_type, amount = pl.col("TB_TAXTP"), pl.col("TB_AMOUNT")
    amounts = tax_bookings(legacy_dir).group_by(EVENT).agg(
        **{name: amount.filter(tax_type.is_in(types)).sum() for name, types in PAYOUT_AMOUNTS.items()})
    rows = payouts(legacy_dir).join(amounts, on=EVENT, how="left").with_columns(pl.col(*PAYOUT_AMOUNTS).fill_null(0))
    return rows.select(pl.col("TB_POLNR").alias("policy_id"), pl.col("TB_EVTNR").alias("event_nr"),
                       pl.col("AD_CNTRY").fill_null("").alias("country"), pl.col("TAXABLE_BASE").alias("taxable_base"),
                       *PAYOUT_AMOUNTS, remittance().alias("remittance_date"))


def annual_table(legacy_dir) -> pl.DataFrame:
    """policy_id, year and the ANNUAL_AMOUNTS (cents) of the bookings effective in the year, if any is not 0."""
    tax_type, amount = pl.col("TB_TAXTP"), pl.col("TB_AMOUNT")
    booked = tax_bookings(legacy_dir).with_columns(year=as_date("TB_EFFDT").dt.year())
    years = booked.group_by(policy_id="TB_POLNR", year="year").agg(
        **{name: amount.filter(tax_type.eq(tax)).sum() for name, tax in ANNUAL_AMOUNTS.items()})
    return years.filter(pl.any_horizontal(pl.col(*ANNUAL_AMOUNTS).ne(0)))
