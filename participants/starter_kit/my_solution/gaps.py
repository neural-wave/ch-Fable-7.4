"""The gaps of t7: for every payout, the missing inputs and the untested assumptions its row rests on.

The rules turn a missing input into a value that looks valid (a gross of 0, the first EUR rate of all, an empty
country), so a gap never fails, it only gives a wrong row. `flagged_payouts` tests the raw conditions instead
and names each one with a flag of FLAGS:

- gap: an input is missing and a fallback stands in;
- assumption: the row rests on a rule that no target row has tested yet.

A payout without a flag is decided by rules that the targets verified. `t7lab/t7_gaps.py` prints the counts and
scores target files by flag; `conventions.PAYOUT_SCOPE` reports only the payouts with or without a flag, a
leaderboard probe that tells in which of the two the rows of a sample are right.
"""
import polars as pl

from conventions import DEATH_CLAIM, EXTRACT_DATE, PAID_OUT, PAYOUT_SCOPE, PERIOD_RATES, TAX_CURRENCY
from legacy import table, valid_on
from market import exchange_rates
from payouts import EVENT, payouts
from periods import bounds
from tariff import signed_policies
from taxes import payout_table
from valuation import values_on

FLAGS = {  # name -> (kind, what it means and what the rules do then)
    "NO_PAYOUT_BOOKING": ("gap", "no WDR, SUR or DTH booking for the event: the gross is 0"),
    "RESIDENCE_UNKNOWN": ("gap", "no holder or address known at processing: no country"),
    "RESIDENCE_LATE": ("gap", "the residence known at processing differs from today's view: the first one counts"),
    "REGION_MISSING": ("gap", "a German holder without region: the church tax of all regions"),
    "RATE_STAND_IN": ("gap", "no rate of the tax currency on the payout day (before the euro): the first rate"),
    "PREMIUM_RATE_STAND_IN": ("gap", "a premium from before the first rate of the tax currency: the first rate"),
    "SUMIN_MISSING": ("gap", "a death claim without a sum insured: 0"),
    "VALUE_MISSING": ("gap", "no policy value at the end of a rate period of SOS: 0"),
    "UNKNOWN_COUNTRY": ("gap", "a residence outside the tax countries: no currency, base 0"),
    "AFTER_EXTRACT": ("gap", "remitted after the extract date: the date is reported all the same"),
    "UNTAXED_DEATH_BASE": ("assumption", "a DE or IT death claim without withholding reports its gain as base"),
    "DE_EXEMPT_BASE": ("assumption", "a German payout without KST but with a base reports that base"),
    "DEATH_OPTION_B_C": ("assumption", "a death claim of option B or C pays its benefit (2 sample rows so far)"),
}
RESIDENCE = ["AD_CNTRY", "AD_TAXST", "AD_REGIO", "AD_CHURCH"]  # the address columns a payout reads


def payout_rows(legacy_dir) -> pl.DataFrame:
    """Every payout with its event type, WITHHOLDING and REMITTED of its output row, OPTION and RK_SUMIN."""
    events = table(legacy_dir, "NREVNT").select(TB_POLNR="EV_POLNR", TB_EVTNR="EV_EVTNR", EVENT_TYPE="EV_EVTTP")
    output = payout_table(legacy_dir).select(TB_POLNR="policy_id", TB_EVTNR="event_nr", WITHHOLDING="withholding",
                                             REMITTED="remittance_date")
    policies = signed_policies(legacy_dir).select(TB_POLNR="PH_POLNR", OPTION="OPTION", RK_SUMIN="RK_SUMIN")
    return payouts(legacy_dir).join(events, on=EVENT, how="left").join(output, on=EVENT, how="left").join(
        policies, on="TB_POLNR", how="left")


def todays_residences(legacy_dir, rows: pl.DataFrame) -> pl.DataFrame:
    """EVENT and TODAY_ + RESIDENCE: the address valid on the payout day in today's view, whenever entered."""
    numbered = rows.select(*EVENT, "TB_EFFDT").with_row_index("ROW")
    holders = valid_on(numbered, table(legacy_dir, "NRHOLD"), {"TB_POLNR": "HD_POLNR"}, "TB_EFFDT", "HD")
    addresses = valid_on(holders, table(legacy_dir, "NRADDR"), {"HD_PERNR": "AD_PERNR"}, "TB_EFFDT", "AD")
    today = addresses.select("ROW", *[pl.col(column).alias(f"TODAY_{column}") for column in RESIDENCE])
    return numbered.join(today, on="ROW", how="left").drop("ROW", "TB_EFFDT")


def early_premiums(legacy_dir, rows: pl.DataFrame, firsts: pl.DataFrame) -> pl.DataFrame:
    """EVENT and EARLY_PREMIUM of the payouts that count a premium received before the first rate of their tax
    currency."""
    premiums = table(legacy_dir, "NRPREM").filter(pl.col("PR_RCVDT").gt(0)).select(TB_POLNR="PR_POLNR",
                                                                                   PR_RCVDT="PR_RCVDT")
    counted = rows.select(*EVENT, "TB_EFFDT", "TAX_CCY").join(firsts, on="TAX_CCY").join(premiums, on="TB_POLNR")
    early = counted.filter(pl.col("PR_RCVDT").le(pl.col("TB_EFFDT")), pl.col("PR_RCVDT").lt(pl.col("FIRST_RATE")))
    return early.select(EVENT).unique().with_columns(EARLY_PREMIUM=pl.lit(True))


def missing_values(legacy_dir, rows: pl.DataFrame) -> pl.DataFrame:
    """EVENT and NO_VALUE of the payouts of PERIOD_RATES whose policy has no value at the end of a rate period
    before the payout."""
    periodic = table(legacy_dir, "NRTAXB").filter(pl.col("TB_TAXTP").is_in(PERIOD_RATES)).select(EVENT).unique()
    spans = rows.join(periodic, on=EVENT).select(*EVENT, "TB_EFFDT", "PH_BEGDT").join(
        bounds(legacy_dir).select("BOUND").unique(), how="cross").filter(
        pl.col("BOUND").ge(pl.col("PH_BEGDT")), pl.col("BOUND").lt(pl.col("TB_EFFDT")))
    values = values_on(legacy_dir, spans.select(BK_POLNR="TB_POLNR", DAY="BOUND").unique()).select(
        TB_POLNR="BK_POLNR", BOUND="DAY", VALUE="VALUE")
    missing = spans.join(values, on=["TB_POLNR", "BOUND"], how="left").filter(pl.col("VALUE").is_null())
    return missing.select(EVENT).unique().with_columns(NO_VALUE=pl.lit(True))


def booked_payouts(legacy_dir) -> pl.DataFrame:
    """EVENT and BOOKED of the payout events with a WDR, SUR or DTH booking."""
    paid = table(legacy_dir, "NRBOOK").filter(pl.col("BK_BKTYP").is_in(PAID_OUT))
    return paid.select(TB_POLNR="BK_POLNR", TB_EVTNR="BK_EVTNR").unique().with_columns(BOOKED=pl.lit(True))


def conditions() -> dict[str, pl.Expr]:
    """FLAG -> the condition on a row of `flagged_payouts` before the flags."""
    death, withheld = pl.col("EVENT_TYPE").eq(DEATH_CLAIM), pl.col("WITHHOLDING").fill_null(0).ne(0)
    country, base = pl.col("COUNTRY"), pl.col("TAXABLE_BASE").gt(0)
    untaxed = withheld.not_().and_(base)
    return {
        "NO_PAYOUT_BOOKING": pl.col("BOOKED").is_null(),
        "RESIDENCE_UNKNOWN": country.is_null().or_(pl.col("HD_PERNR").is_null()),
        "RESIDENCE_LATE": pl.any_horizontal(*[pl.col(column).ne_missing(pl.col(f"TODAY_{column}"))
                                              for column in RESIDENCE]),
        "REGION_MISSING": country.eq("DE").and_(pl.col("AD_REGIO").is_null()),
        "RATE_STAND_IN": pl.col("TB_EFFDT").lt(pl.col("FIRST_RATE")),
        "PREMIUM_RATE_STAND_IN": pl.col("EARLY_PREMIUM").is_not_null(),
        "SUMIN_MISSING": death.and_(pl.col("RK_SUMIN").is_null()),
        "VALUE_MISSING": pl.col("NO_VALUE").is_not_null(),
        "UNKNOWN_COUNTRY": country.is_in(list(TAX_CURRENCY)).not_(),
        "AFTER_EXTRACT": pl.col("REMITTED").gt(EXTRACT_DATE),
        "UNTAXED_DEATH_BASE": death.and_(country.is_in(["DE", "IT"])).and_(untaxed),
        "DE_EXEMPT_BASE": death.not_().and_(country.eq("DE")).and_(untaxed),
        "DEATH_OPTION_B_C": death.and_(pl.col("OPTION").is_in(["B", "C"])),
    }


def flagged_payouts(legacy_dir) -> pl.DataFrame:
    """EVENT, COUNTRY, one boolean column per flag of FLAGS and FLAGS_SET: the names that apply, comma separated."""
    rows = payout_rows(legacy_dir)
    firsts = exchange_rates(legacy_dir).group_by(TAX_CCY="FX_CCY").agg(FIRST_RATE=pl.col("FX_RATDT").min())
    joined = rows.join(todays_residences(legacy_dir, rows), on=EVENT, how="left").join(
        firsts, on="TAX_CCY", how="left").join(booked_payouts(legacy_dir), on=EVENT, how="left").join(
        early_premiums(legacy_dir, rows, firsts), on=EVENT, how="left").join(
        missing_values(legacy_dir, rows), on=EVENT, how="left")
    marked = joined.with_columns(**{name: condition.fill_null(False) for name, condition in conditions().items()})
    names = pl.concat_list([pl.when(pl.col(name)).then(pl.lit(name)) for name in FLAGS]).list.drop_nulls()
    return marked.select(*EVENT, "COUNTRY", *FLAGS, FLAGS_SET=names.list.join(","))


def flag_keys(legacy_dir, with_flag: bool) -> pl.DataFrame:
    """policy_id and event_nr of the payouts with a flag (`with_flag`) or without one."""
    keys = flagged_payouts(legacy_dir).filter(pl.col("FLAGS_SET").ne("").eq(with_flag))
    return keys.select(policy_id="TB_POLNR", event_nr="TB_EVTNR")


def every_payout(legacy_dir, rows: pl.DataFrame) -> pl.DataFrame:
    """`rows` as they are: the scope "all"."""
    return rows


def unflagged(legacy_dir, rows: pl.DataFrame) -> pl.DataFrame:
    """The `rows` of the payouts without a flag."""
    return rows.join(flag_keys(legacy_dir, False), on=["policy_id", "event_nr"], how="semi")


def flagged(legacy_dir, rows: pl.DataFrame) -> pl.DataFrame:
    """The `rows` of the payouts with a flag."""
    return rows.join(flag_keys(legacy_dir, True), on=["policy_id", "event_nr"], how="semi")


SCOPES = {"all": every_payout, "unflagged": unflagged, "flagged": flagged}  # conventions.PAYOUT_SCOPE -> rows


def in_scope(legacy_dir, rows: pl.DataFrame) -> pl.DataFrame:
    """The `rows` of the payout table (policy_id, event_nr, ...) in `conventions.PAYOUT_SCOPE`."""
    return SCOPES[PAYOUT_SCOPE](legacy_dir, rows)
