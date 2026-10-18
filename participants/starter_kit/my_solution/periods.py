"""The gain of a payout split by the periods of its tax rates (t7): the Italian SOS takes the gain accrued in each
period at the rate of the period (`conventions.PERIOD_RATES`).

The rates of SOS changed on 1.1.2012 (12.5 % -> 20 %) and on 1.7.2014 (20 % -> 26 %). The gain accrued up to the
end of a period, the BOUND (31.12.2011, 30.6.2014), is the policy value at the end of that day, converted to the tax
currency on it, less the premiums received up to then that no earlier payout used (`payouts.premium_chains`). A
payout takes its share PART / WHOLE of what the earlier payouts after the bound left of that gain, as it takes the
premiums; the later payouts take their share of the rest. With TAKEN, the gain up to the bound that the payout
takes, its tax is

    rate of the payout day x base - sum over the bounds (rate after the bound - rate up to it) x TAKEN

which is the gain of every period at the rate of the period. Targets: all five SOS payouts, among them BL10003541,
whose third payout (2023) follows a German one (2003) and an Italian one (2018).
"""
import polars as pl

from conventions import PERIOD_RATES
from legacy import CENTURY, as_date, table
from money import rounded_signed
from payouts import BASIS_UNIT, EVENT, SCHEME, converted_premiums, in_turn, premium_chains, payouts
from taxpayer import tax_rates, with_tax_currency
from valuation import values_on

POLICY_SCHEME = ["TB_POLNR", *SCHEME]  # a chain of `payouts.premium_chains`: the payouts of a policy in one scheme


def bounds(legacy_dir) -> pl.DataFrame:
    """TX_TAXTP and BOUND: the last day (CYYMMDD) of every closed period of the rates of PERIOD_RATES."""
    rates = table(legacy_dir, "NRTAXR").filter(pl.col("TX_TAXTP").is_in(PERIOD_RATES),
                                               as_date("TX_VLDTO").is_not_null())
    return rates.select("TX_TAXTP", BOUND="TX_VLDTO").unique()


def day_after(day: str) -> pl.Expr:
    """The day after the CYYMMDD column `day`, as CYYMMDD."""
    return as_date(day).dt.offset_by("1d").dt.strftime("%Y%m%d").cast(pl.Int64).sub(CENTURY)


def gains_to_bounds(legacy_dir, chains: pl.DataFrame, schemes: pl.DataFrame, ends: pl.DataFrame) -> pl.DataFrame:
    """CHAIN, BOUND and GAIN_TO: the gain of the policy up to the end of BOUND in the scheme of the chain, in
    millionths of a cent: the value of the day converted on it, less the premiums received up to it, plus what the
    payouts up to it used of them (`chains`, USED)."""
    starts = schemes.join(ends.select("BOUND").unique(), how="cross").filter(
        pl.col("BOUND").ge(pl.col("PH_BEGDT")))
    days = starts.select(BK_POLNR="TB_POLNR", DAY="BOUND").unique()
    values = values_on(legacy_dir, days).select(TB_POLNR="BK_POLNR", BOUND="DAY", VALUE="VALUE")
    valued = with_tax_currency(legacy_dir, starts.join(values, on=["TB_POLNR", "BOUND"], how="left"),
                               pl.col("TAX_CCY"), "BOUND")
    premiums = converted_premiums(legacy_dir, schemes.drop("PH_BEGDT")).join(starts.select(*POLICY_SCHEME, "BOUND"),
                                                                             on=POLICY_SCHEME)
    received = premiums.filter(pl.col("PR_RCVDT").le(pl.col("BOUND"))).group_by(*POLICY_SCHEME, "BOUND").agg(
        RECEIVED=pl.col("PREMIUM").sum())
    used = chains.join(starts.select(*POLICY_SCHEME, "BOUND"), on=POLICY_SCHEME).filter(
        pl.col("TB_EFFDT").le(pl.col("BOUND"))).group_by(*POLICY_SCHEME, "BOUND").agg(USED_BEFORE=pl.col("USED").sum())
    value = rounded_signed(pl.col("VALUE").fill_null(0).cast(pl.Int128).mul(pl.col("RP")).mul(BASIS_UNIT),
                           pl.col("RT"), pl.lit(True))
    paid_in = pl.col("RECEIVED").fill_null(0).cast(pl.Int128).mul(BASIS_UNIT)
    gained = valued.join(received, on=[*POLICY_SCHEME, "BOUND"], how="left").join(
        used, on=[*POLICY_SCHEME, "BOUND"], how="left")
    return gained.select(*POLICY_SCHEME, "BOUND", GAIN_TO=value.sub(paid_in).add(pl.col("USED_BEFORE").fill_null(0)))


def taken(turn: pl.DataFrame) -> pl.DataFrame:
    """The payouts of one turn with TAKEN: their share PART / WHOLE of the gain up to the bound that the EARLIER
    payouts after the bound left."""
    left_over = pl.col("GAIN_TO").sub(pl.col("EARLIER"))
    return turn.with_columns(TAKEN=rounded_signed(left_over.mul(pl.col("PART")), pl.col("WHOLE"), pl.lit(True)))


def taken_gains(legacy_dir, policies: pl.DataFrame) -> pl.DataFrame:
    """EVENT, SCHEME, BOUND and TAKEN of every payout of `policies` (TB_POLNR) after a bound, in every scheme of
    the payouts of its policy."""
    rows = payouts(legacy_dir).join(policies, on="TB_POLNR", how="semi")
    chains = premium_chains(legacy_dir, rows)
    schemes = rows.select(*POLICY_SCHEME, "PH_CCY", "PH_BEGDT").drop_nulls().unique()
    gains = gains_to_bounds(legacy_dir, chains, schemes, bounds(legacy_dir))
    after = chains.join(gains, on=POLICY_SCHEME).filter(pl.col("TB_EFFDT").gt(pl.col("BOUND"))).with_columns(
        KEY=pl.concat_str("CHAIN", pl.col("BOUND").cast(pl.String)))
    return in_turn(after.sort("TB_CHGTS", "TB_EVTNR"), "KEY", taken, "TAKEN").select(*EVENT, *SCHEME, "BOUND",
                                                                                     "TAKEN")


def period_reductions(legacy_dir, bookings: pl.DataFrame) -> pl.DataFrame:
    """The `bookings` of PERIOD_RATES (columns of NRTAXB) with REDUCTION: the sum over the bounds before their
    payout of (rate after the bound - rate up to it) x TAKEN, in millionths of a millionth of a cent; every other
    booking has none."""
    periodic = bookings.filter(pl.col("TB_TAXTP").is_in(PERIOD_RATES))
    own = payouts(legacy_dir).select(*EVENT, *SCHEME)
    takes = periodic.join(own, on=EVENT).join(taken_gains(legacy_dir, periodic.select("TB_POLNR").unique()),
                                             on=[*EVENT, *SCHEME])
    up_to = tax_rates(legacy_dir, takes.with_columns(TB_EFFDT="BOUND"), pl.col("TB_TAXTP"), "UP_TO")
    after = tax_rates(legacy_dir, up_to.with_columns(TB_EFFDT=day_after("BOUND")), pl.col("TB_TAXTP"), "AFTER")
    step = pl.col("AFTER").sub(pl.col("UP_TO")).cast(pl.Int128).mul(pl.col("TAKEN"))
    reductions = after.group_by(*EVENT, "TB_TAXTP").agg(REDUCTION=step.sum())
    return bookings.join(reductions, on=[*EVENT, "TB_TAXTP"], how="left").with_columns(
        pl.col("REDUCTION").fill_null(0).cast(pl.Int128))

