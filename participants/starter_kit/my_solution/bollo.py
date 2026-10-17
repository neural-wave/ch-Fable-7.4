"""The Italian stamp duty on the policy value, the Bollo (t7): accrued every year, collected at the payouts.

- BOL accrued: on 31 December the batch accrues the Bollo of the policies of Italian residents: the policy value
  (less the penalty of the day, as `valuation.surrender_values`, with `conventions.BOLLO_ON_SURRENDER_VALUE`) x the
  rate valid on the day as Neuron knew it then (`taxpayer.tax_rates`) x the days of the year the policy ran (from
  1 January or from its start date) / the days of the year. A payout that ends the policy accrues the Bollo of the
  year so far on the value before it, taken the same way (a BOL with the event number of the payout).
- BOL re-priced: the rate of 2017 to June 2019 was restated in July 2019 (version 2 of NRTAXR). The fix
  (TB_USRID TAXFIX19) booked per policy the difference of every BOL before it at the new rate, rounded once on
  the total: BL10000044 has 421.57 + 194.54 = 616.11 in 2019, as in the example; rounding every year gives 194.53.
- BOC collected: every payout of a policy that accrued Bollo collects the outstanding Bollo, also after the holder
  left Italy: the BOL booked up to it less the BOC before it. A payout that ends the policy collects all of it, a
  partial withdrawal its share PART / WHOLE (`payouts`), so the BOC of a policy follow one another (`in_turn`).

Amounts in euro cents, rounded half up once, a negative difference like its positive twin (`money.rounded_signed`);
the value is converted from the policy currency on the day.
"""
import polars as pl

from conventions import BOLLO_FIX, BOLLO_ON_SURRENDER_VALUE, CONVERSION, STAMP_DUTY, TAX_CURRENCY, TAXES
from dates import days_between
from legacy import as_date
from money import RATE_UNIT, rounded, rounded_signed
from payouts import EVENT, in_turn, payouts
from taxpayer import tax_rates, with_policies, with_tax_currency
from valuation import penalties_on, values_on

BOLLO = "BOL"  # TB_TAXTP of the Bollo accrued; its rate in NRTAXR has the same type


def is_fix() -> pl.Expr:
    """True for a BOL of the re-pricing after the rate restatement of July 2019."""
    return pl.col("TB_USRID").str.starts_with(BOLLO_FIX)


def year_share() -> dict[str, pl.Expr]:
    """RUN_DAYS, the days of the year up to TB_EFFDT that the policy ran, and YEAR_DAYS, the days of the year."""
    day = as_date("TB_EFFDT")
    first = day.dt.truncate("1y")
    start = pl.max_horizontal(first, as_date("PH_BEGDT"))
    return {"RUN_DAYS": days_between(start, day).add(1), "YEAR_DAYS": days_between(first, first.dt.offset_by("1y"))}


def bollo(rate: pl.Expr, parts: int = 1) -> pl.Expr:
    """The Bollo at `rate` of the policy VALUE of the row, for its share of the year, in 1 / `parts` euro cents."""
    taxed = pl.col("VALUE").cast(pl.Int128).mul(pl.col("RP")).mul(pl.col("RUN_DAYS")).mul(rate).mul(parts)
    whole = pl.col("RT").cast(pl.Int128).mul(RATE_UNIT).mul(pl.col("YEAR_DAYS"))
    return rounded_signed(taxed, whole, pl.lit(True))


def penalties(legacy_dir, bookings: pl.DataFrame) -> pl.DataFrame:
    """TB_POLNR, TB_EFFDT and SR_RATE: the surrender penalty of the policy on the day of each of `bookings`."""
    days = bookings.select(BK_POLNR="TB_POLNR", DAY="TB_EFFDT").unique()
    return penalties_on(legacy_dir, days).select(TB_POLNR="BK_POLNR", TB_EFFDT="DAY", SR_RATE="SR_RATE")


def taxed_value() -> pl.Expr:
    """The VALUE of a row less the surrender penalty SR_RATE of its day, rounded once and at least 0, as
    `valuation.surrender_values`; the VALUE itself without `conventions.BOLLO_ON_SURRENDER_VALUE`."""
    kept = pl.col("VALUE").mul(pl.lit(RATE_UNIT).sub(pl.col("SR_RATE")))
    surrender = rounded(kept, RATE_UNIT, as_date("TB_EFFDT").ge(CONVERSION)).clip(0)
    return pl.when(pl.lit(BOLLO_ON_SURRENDER_VALUE)).then(surrender).otherwise("VALUE")


def accrued_bollo(legacy_dir, bookings: pl.DataFrame) -> pl.DataFrame:
    """The BOL `bookings` of the batches and of the payouts with VALUE (`taxed_value`), RATE and TB_AMOUNT."""
    values = values_on(legacy_dir, bookings.select(BK_POLNR="TB_POLNR", DAY="TB_EFFDT")).select(
        TB_POLNR="BK_POLNR", TB_EFFDT="DAY", YEAR_END="VALUE").unique()
    before = payouts(legacy_dir).select(*EVENT, "BEFORE")
    valued = bookings.join(values, on=["TB_POLNR", "TB_EFFDT"]).join(before, on=EVENT, how="left").join(
        penalties(legacy_dir, bookings), on=["TB_POLNR", "TB_EFFDT"], how="left").with_columns(
        VALUE=pl.coalesce("BEFORE", "YEAR_END")).with_columns(VALUE=taxed_value())
    euros = with_tax_currency(legacy_dir, with_policies(legacy_dir, valued), pl.lit(TAX_CURRENCY[TAXES[BOLLO]]))
    rated = tax_rates(legacy_dir, euros.with_columns(**year_share()), pl.lit(BOLLO), "RATE")
    return rated.with_columns(TB_AMOUNT=bollo(pl.col("RATE")))


def fixed_bollo(legacy_dir, fixes: pl.DataFrame, accrued: pl.DataFrame) -> pl.DataFrame:
    """The BOL `fixes` with TB_AMOUNT: the BOL `accrued` before each fix again at the rate known at the fix,
    less what they booked, rounded once."""
    earlier = fixes.select(FIX_BOOKID="TB_BOOKID", TB_POLNR="TB_POLNR", FIX_CHGTS="TB_CHGTS").join(
        accrued, on="TB_POLNR").filter(pl.col("TB_CHGTS").lt(pl.col("FIX_CHGTS")))
    restated = tax_rates(legacy_dir, earlier, pl.lit(BOLLO), "RESTATED", known_at="FIX_CHGTS")
    differences = restated.group_by("FIX_BOOKID").agg(
        DIFFERENCE=bollo(pl.col("RESTATED").sub(pl.col("RATE")), RATE_UNIT).sum())
    return fixes.join(differences, left_on="TB_BOOKID", right_on="FIX_BOOKID", how="left").with_columns(
        TB_AMOUNT=rounded_signed(pl.col("DIFFERENCE").fill_null(0), RATE_UNIT, pl.lit(True))).drop("DIFFERENCE")


def collected(turn: pl.DataFrame) -> pl.DataFrame:
    """The BOC of one turn with TB_AMOUNT: the share PART / WHOLE of the Bollo that the EARLIER BOC left over."""
    outstanding = pl.col("ACCRUED").cast(pl.Int128).sub(pl.col("EARLIER"))
    return turn.with_columns(TB_AMOUNT=rounded_signed(outstanding.mul(pl.col("PART")), pl.col("WHOLE"), pl.lit(True)))


def collected_bollo(legacy_dir, collections: pl.DataFrame, accrued: pl.DataFrame) -> pl.DataFrame:
    """The BOC `collections` with ACCRUED, the BOL `accrued` (fixes included) booked up to each, and TB_AMOUNT.

    A BOC of no reported payout has no share and keeps a null amount.
    """
    booked = collections.select("TB_BOOKID", "TB_POLNR", "TB_CHGTS").join(
        accrued.select("TB_POLNR", BOL_CHGTS="TB_CHGTS", BOL_AMOUNT="TB_AMOUNT"), on="TB_POLNR").filter(
        pl.col("BOL_CHGTS").le(pl.col("TB_CHGTS"))).group_by("TB_BOOKID").agg(ACCRUED=pl.col("BOL_AMOUNT").sum())
    shares = payouts(legacy_dir).select(*EVENT, "PART", "WHOLE")
    ordered = collections.join(booked, on="TB_BOOKID", how="left").join(shares, on=EVENT, how="left").with_columns(
        pl.col("ACCRUED").fill_null(0)).sort("TB_CHGTS", "TB_BOOKID")
    return in_turn(ordered, "TB_POLNR", collected, "TB_AMOUNT")


def bollo_bookings(legacy_dir, bookings: pl.DataFrame) -> pl.DataFrame:
    """The BOL and BOC of the tax `bookings` (NRTAXB) with TB_AMOUNT, in the columns of `bookings`."""
    stamp_duties = bookings.filter(pl.col("TB_TAXTP").eq(BOLLO))
    accrued = accrued_bollo(legacy_dir, stamp_duties.filter(is_fix().not_()))
    fixed = fixed_bollo(legacy_dir, stamp_duties.filter(is_fix()), accrued)
    all_accrued = pl.concat([accrued.select(fixed.columns), fixed])
    collections = bookings.filter(pl.col("TB_TAXTP").is_in(STAMP_DUTY))
    return pl.concat([all_accrued, collected_bollo(legacy_dir, collections, all_accrued).select(fixed.columns)])
