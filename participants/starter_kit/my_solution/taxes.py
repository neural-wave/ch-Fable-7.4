"""The amounts of the tax bookings of Neuron and the two tables of t7, in cents of the tax currency.

NRTAXB names every tax booking of Neuron with its type, event, effective date and processing timestamp; only the
amount is missing. So the rules do not decide again whether a tax was due: they calculate the amount of every
booking, with the rates valid on the effective date as Neuron knew them at the processing time (`taxpayer`).

- STP: the Swiss stamp duty on the premium of its event (the single premium, event 2), converted to francs
- VST, SOS: the taxable base of the payout (`payouts`) x the rate
- KST: the base x the rate; with a KIS booking for the payout base x KST / (1 + KST x KIS), section 32d EStG.
  SOL and KIS: the KST x their rate, KIS of the region of residence
- BOL, BOC: the Bollo (`bollo`)

Every amount is rounded once, by the system that processed it: COBOL truncates, Neuron NG rounds half up
(`taxpayer.rounds_half_up`, the mode of the country in `conventions.ROUNDING`). A booking
whose payout, premium or rate is missing keeps a null amount, so a check can find it (`t7lab/t7_check.py`, next to
the hand-in).
"""
import functools

import polars as pl

from bollo import bollo_bookings
from conventions import (ANNUAL_TAXES, BASE_WITHOUT_TAX, BLENDED_RATES, CHURCH_REDUCED, CHURCH_REDUCES_KST,
                         CHURCH_TAX, COLLECTED_IN_ANNUAL, PREMIUM_STAMP, REMITTED_FROM_PAYMENT, REMITTANCE,
                         REMITTANCE_SHIFTED, STAMP_DUTY, STAMP_DUTY_ALONE, STAMP_DUTY_COUNTRY,
                         STAMP_DUTY_REMITTED, SURCHARGES, TAX_CURRENCY, TAXES, WITHHELD)
from dates import tax_office_holidays
from legacy import as_date, table
from money import RATE_UNIT, SHARE_UNIT, rounded
from payouts import EVENT, payouts
from taxpayer import blended_rates, rounds_half_up, tax_rates, with_policies, with_tax_currency

BOOKING = ["TB_POLNR", "TB_EVTNR", "TB_TAXTP", "TB_EFFDT"]  # the columns of a booking besides TB_AMOUNT
PAYOUT_AMOUNTS = {"withholding": WITHHELD, "surcharges": SURCHARGES, "stamp_duty": STAMP_DUTY}  # name -> types
ANNUAL_AMOUNTS = {f"{TAXES[tax].lower()}_{tax.lower()}": tax for tax in ANNUAL_TAXES}  # ch_stp -> STP, ...
COLLECTED = {"BOL": STAMP_DUTY}  # accrued tax type -> the types that collect it at a payout


def half_up(tax_type: pl.Expr) -> pl.Expr:
    """True where Neuron rounds the tax `tax_type` half up, false where it truncates (`taxpayer.rounds_half_up`)."""
    return rounds_half_up(tax_type.replace_strict(TAXES, default=None))


def premium_stamp_duty(legacy_dir, bookings: pl.DataFrame) -> pl.DataFrame:
    """The STP `bookings` with TB_AMOUNT: the premium of their event, in francs, x the rate.

    NRPREM has one item per receipt event, so the join neither copies nor, being a left join, drops a booking.
    """
    premiums = table(legacy_dir, "NRPREM").select(TB_POLNR="PR_POLNR", TB_EVTNR="PR_EVTNR",
                                                  PREMIUM=pl.coalesce("PR_AMTRC", "PR_AMTDU"))
    rows = with_policies(legacy_dir, bookings.join(premiums, on=EVENT, how="left"))
    currency = pl.col("TB_TAXTP").replace_strict(TAXES).replace_strict(TAX_CURRENCY)
    rated = tax_rates(legacy_dir, with_tax_currency(legacy_dir, rows, currency), pl.col("TB_TAXTP"), "RATE")
    taxed = pl.col("PREMIUM").cast(pl.Int128).mul(pl.col("RP")).mul(pl.col("RATE"))
    whole = pl.col("RT").cast(pl.Int128).mul(RATE_UNIT)
    return rated.with_columns(TB_AMOUNT=rounded(taxed, whole, half_up(pl.col("TB_TAXTP"))))


def capital_gains_tax() -> pl.Expr:
    """The KST of the payout: base x KST_RATE, with a KIS booking / (1 + KST_RATE x KIS_RATE).

    The KIS booking is the label that Neuron withheld church tax; the address may say otherwise.
    """
    reduced = pl.col("KIS_BOOKED").and_(pl.lit(CHURCH_REDUCES_KST))
    church = pl.when(reduced).then(pl.col("KIS_RATE").fill_null(0)).otherwise(0)
    taxed = pl.col("TAXABLE_BASE").cast(pl.Int128).mul(pl.col("KST_RATE")).mul(RATE_UNIT)
    whole = pl.lit(SHARE_UNIT, pl.Int128).add(pl.col("KST_RATE").mul(church))
    return rounded(taxed, whole, half_up(pl.lit(CHURCH_REDUCED)))


def payout_taxes(legacy_dir, bookings: pl.DataFrame) -> pl.DataFrame:
    """The withholding taxes and surcharges of the payouts in `bookings` with TB_AMOUNT.

    VST and SOS are the base x their rate, SOL and KIS the KST x their rate; the rate of the types in
    `conventions.BLENDED_RATES` is averaged over the life of the policy (`taxpayer.blended_rates`). A booking of no
    reported payout keeps a null amount.
    """
    residents = payouts(legacy_dir).select(*EVENT, "TAXABLE_BASE", "AD_REGIO", "PH_BEGDT")
    church_tax = bookings.group_by(EVENT).agg(KIS_BOOKED=pl.col("TB_TAXTP").eq(CHURCH_TAX).any())
    booked = bookings.join(residents, on=EVENT, how="left").join(church_tax, on=EVENT, how="left")
    dated = tax_rates(legacy_dir, booked, pl.col("TB_TAXTP"), "DAY_RATE", region="AD_REGIO")
    blended = blended_rates(legacy_dir, dated, pl.col("TB_TAXTP"), "LIFE_RATE")
    rows = blended.with_columns(RATE=pl.when(pl.col("TB_TAXTP").is_in(BLENDED_RATES)).then("LIFE_RATE").otherwise(
        "DAY_RATE")).drop("DAY_RATE", "LIFE_RATE")
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


def shifted(day: pl.Expr, country: pl.Expr) -> pl.Expr:
    """`day`, moved to the next business day of the tax office for the countries of REMITTANCE_SHIFTED."""
    moved = day
    for name in REMITTANCE_SHIFTED:
        business_day = day.dt.add_business_days(0, holidays=tax_office_holidays(name), roll="forward")
        moved = pl.when(country.eq(name)).then(business_day).otherwise(moved)
    return moved


def due_day(paid: pl.Expr, rule: pl.Expr) -> pl.Expr:
    """The day the taxes of a payout paid on `paid` are due under the `rule` of REMITTANCE: its anchor plus its days.

    The anchors: "month", the last day of the month of `paid`; "month_end", the last day of the month after;
    "quarter", the last day of the quarter; "day", `paid` itself.
    """
    anchor = rule.replace_strict({name: anchored[0] for name, anchored in REMITTANCE.items()}, default=None)
    days = rule.replace_strict({name: anchored[1] for name, anchored in REMITTANCE.items()}, default=None,
                               return_dtype=pl.Int64)
    month_end = paid.dt.month_end()
    quarter_end = paid.dt.truncate("1q").dt.offset_by("1q").dt.offset_by("-1d")
    anchored = pl.when(anchor.eq("month")).then(month_end).when(anchor.eq("month_end")).then(
        month_end.dt.offset_by("1d").dt.month_end()).when(anchor.eq("quarter")).then(quarter_end).otherwise(paid)
    return anchored.add(pl.duration(days=days))


def remittance() -> pl.Expr:
    """The day Neuron paid the taxes of a payout to the tax office, null without tax.

    The country of the withholding decides the calendar, Italy for stamp duty alone, and the rule of REMITTANCE is
    the country's, or STAMP_DUTY_ALONE's for stamp duty alone; the day is the `due_day` of the payout day,
    the day of the payment PAID with REMITTED_FROM_PAYMENT or else the effective date, moved to a business day for
    the countries of REMITTANCE_SHIFTED. A payout with stamp duty alone has a day with STAMP_DUTY_REMITTED.
    """
    withheld = pl.col("withholding").add(pl.col("surcharges"))
    country = pl.when(withheld.ne(0)).then("COUNTRY").otherwise(pl.lit(STAMP_DUTY_COUNTRY))
    rule = pl.when(withheld.ne(0)).then("COUNTRY").otherwise(pl.lit(STAMP_DUTY_ALONE))
    paid = pl.when(pl.lit(REMITTED_FROM_PAYMENT)).then(pl.col("PAID")).otherwise(as_date("TB_EFFDT"))
    remitted = pl.when(pl.lit(STAMP_DUTY_REMITTED)).then(withheld.add(pl.col("stamp_duty"))).otherwise(withheld)
    return pl.when(remitted.ne(0)).then(shifted(due_day(paid, rule), country))


def withheld_amounts(legacy_dir) -> pl.DataFrame:
    """EVENT and the PAYOUT_AMOUNTS (cents) withheld from every payout with a tax booking.

    Every VST booked was withheld: NRTAXB books it only for holders who objected to the reporting (AD_TAXST E).
    """
    tax_type, amount = pl.col("TB_TAXTP"), pl.col("TB_AMOUNT")
    return tax_bookings(legacy_dir).group_by(EVENT).agg(
        **{name: amount.filter(tax_type.is_in(types)).sum() for name, types in PAYOUT_AMOUNTS.items()})


def payout_table(legacy_dir) -> pl.DataFrame:
    """policy_id, event_nr, country, taxable_base and the PAYOUT_AMOUNTS (cents), remittance_date of every payout.

    A payout without withholding reports the base 0 (`conventions.BASE_WITHOUT_TAX`).
    """
    amounts = withheld_amounts(legacy_dir)
    rows = payouts(legacy_dir).join(amounts, on=EVENT, how="left").with_columns(pl.col(*PAYOUT_AMOUNTS).fill_null(0))
    base = pl.when(pl.lit(BASE_WITHOUT_TAX).or_(pl.col("withholding").ne(0))).then("TAXABLE_BASE").otherwise(0)
    return rows.select(pl.col("TB_POLNR").alias("policy_id"), pl.col("TB_EVTNR").alias("event_nr"),
                       pl.col("COUNTRY").fill_null("").alias("country"), base.alias("taxable_base"),
                       *PAYOUT_AMOUNTS, remittance().alias("remittance_date"))


def annual_types(tax: str) -> pl.Expr:
    """True for the bookings that the annual column of `tax` adds up: that type, and for the Bollo accrued also the
    Bollo collected with `conventions.COLLECTED_IN_ANNUAL`."""
    collected = pl.lit(COLLECTED_IN_ANNUAL).and_(pl.col("TB_TAXTP").is_in(COLLECTED.get(tax, [])))
    return pl.col("TB_TAXTP").eq(tax).or_(collected)


def annual_table(legacy_dir) -> pl.DataFrame:
    """policy_id, year and the ANNUAL_AMOUNTS (cents) of the bookings effective in the year, if any is not 0."""
    amount = pl.col("TB_AMOUNT")
    booked = tax_bookings(legacy_dir).with_columns(year=as_date("TB_EFFDT").dt.year())
    years = booked.group_by(policy_id="TB_POLNR", year="year").agg(
        **{name: amount.filter(annual_types(tax)).sum() for name, tax in ANNUAL_AMOUNTS.items()})
    return years.filter(pl.any_horizontal(pl.col(*ANNUAL_AMOUNTS).ne(0)))
