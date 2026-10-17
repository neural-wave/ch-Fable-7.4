"""The payouts of the policies and their taxable base (t7).

A payout is an event 400 (partial withdrawal), 410 (full surrender) or 500 (death claim) that has a tax booking or
was not reversed. Every one is reported, also without any tax (residents of Luxembourg, Swiss holders who accept
the reporting, old German contracts, ...). The rows have the columns of NRTAXB: TB_EFFDT and TB_CHGTS are the
effective date and the processing timestamp of the event, the same as those of its tax bookings.

- gross: the money paid out, the negative BK_AMTPC of the WDR, SUR and DTH bookings (policy currency)
- value before: the gross plus the policy value left at the end of the day (`valuation.values_on`)
- share PART / WHOLE: what the payout takes of the policy, gross / value before; all of it when it ends the policy
- premiums used: the share of the premiums received up to the payout day that no earlier payout used. The
  payouts of a policy use them one after another (`in_turn`), kept in millionths of a cent (BASIS_UNIT)
- gain: the gross less the premiums used

The taxable base is in the currency of the country of residence (`taxpayer`), rounded once (truncated in
Germany): in Switzerland the gross, the withholding tax VST takes the whole benefit; in Italy and Germany the gain,
at least 0; elsewhere none. In Germany the base is the gain x (1 - TFS), the partial exemption of fund policies
from 2018. A contract started before 2005 and held 12 years is tax free; a later one held 12 years counts half
(HEV) from the age of 60, or 62 for contracts started from 2012.
"""
import functools
import math
from collections.abc import Callable

import polars as pl

from bookings import counted_events, received_premiums, uncharged_bookings
from conventions import (HALF_INCOME_2012, HALF_INCOME_AGE, HELD_YEARS, OLD_CONTRACT, PAID_OUT, PARTLY_TAXED,
                         PAYOUTS, TAX_CURRENCY, TAXED_ON_GAIN, TAXED_ON_GROSS, TERMINATING, TRUNCATED)
from legacy import as_date, as_lenient_date, table
from money import RATE_UNIT, rounded
from taxpayer import residences, tax_rates, with_policies, with_tax_currency
from valuation import values_on

BASIS_UNIT = RATE_UNIT  # the premiums used are kept in millionths of a cent, so a share loses nothing in the cents
FACTOR_UNIT = math.prod([RATE_UNIT, RATE_UNIT])  # the German factor: two rates in millionths multiplied
EVENT = ["TB_POLNR", "TB_EVTNR"]  # the key of an event, e.g. of a payout


def in_turn(rows: pl.DataFrame, key: str, step: Callable[[pl.DataFrame], pl.DataFrame], carried: str) -> pl.DataFrame:
    """`rows`, sorted in processing order, handled one after another per `key` (e.g. per policy).

    `step` gets the rows of one turn with EARLIER: the sum of the column `carried` that `step` added to the rows
    of the same `key` in the turns before (0 in the first). The turns are the first row of every key at once,
    then the second, and so on, like the charge runs.
    """
    turns = rows.with_columns(TURN=pl.int_range(pl.len()).over(key)).partition_by("TURN", as_dict=True)
    earlier = pl.DataFrame(schema={key: rows.schema[key], "EARLIER": pl.Int128})
    done = []
    for turn in sorted(turns):
        current = step(turns[turn].join(earlier, on=key, how="left").with_columns(pl.col("EARLIER").fill_null(0)))
        done.append(current)
        earlier = pl.concat([earlier, current.select(key, EARLIER=pl.col(carried).cast(pl.Int128))]).group_by(
            key).agg(pl.col("EARLIER").sum())
    return pl.concat(done).drop("TURN", "EARLIER")


def payout_events(legacy_dir) -> pl.DataFrame:
    """EVENT, TB_EFFDT, TB_CHGTS and FULL (the payout ends the policy) of every payout event that is reported."""
    events = table(legacy_dir, "NREVNT").filter(pl.col("EV_EVTTP").is_in(PAYOUTS))
    booked = table(legacy_dir, "NRTAXB").select(EV_POLNR="TB_POLNR", EV_EVTNR="TB_EVTNR")
    reported = pl.concat([booked, counted_events(legacy_dir).select("EV_POLNR", "EV_EVTNR")]).unique()
    return events.join(reported, on=["EV_POLNR", "EV_EVTNR"]).select(
        TB_POLNR="EV_POLNR", TB_EVTNR="EV_EVTNR", TB_EFFDT="EV_EFFDT", TB_CHGTS="EV_CHGTS",
        FULL=pl.col("EV_EVTTP").is_in(TERMINATING))


def paid_out(legacy_dir, payouts: pl.DataFrame) -> pl.DataFrame:
    """`payouts` with GROSS and BEFORE (cents of the policy currency) and their share PART / WHOLE."""
    money = uncharged_bookings(legacy_dir).filter(pl.col("BK_BKTYP").is_in(PAID_OUT)).group_by(
        TB_POLNR="BK_POLNR", TB_EVTNR="BK_EVTNR").agg(GROSS=pl.col("BK_AMTPC").sum().neg())
    gross = payouts.join(money, on=EVENT, how="left").with_columns(pl.col("GROSS").fill_null(0))
    left = values_on(legacy_dir, gross.select(BK_POLNR="TB_POLNR", DAY="TB_EFFDT").unique()).select(
        TB_POLNR="BK_POLNR", TB_EFFDT="DAY", LEFT="VALUE")
    before = gross.join(left, on=["TB_POLNR", "TB_EFFDT"]).with_columns(BEFORE=pl.col("GROSS").add(pl.col("LEFT")))
    whole = pl.col("FULL").or_(pl.col("BEFORE").le(0))
    return before.with_columns(PART=pl.when(whole).then(1).otherwise(pl.min_horizontal("GROSS", "BEFORE")),
                               WHOLE=pl.when(whole).then(1).otherwise("BEFORE")).drop("LEFT")


def received_until(legacy_dir, payouts: pl.DataFrame) -> pl.DataFrame:
    """`payouts` with RECEIVED: the premiums received (and not reversed) up to the payout day, in cents."""
    premiums = received_premiums(legacy_dir).select(TB_POLNR="PR_POLNR", PR_RCVDT="PR_RCVDT", PR_AMTRC="PR_AMTRC")
    paid = payouts.select(*EVENT, "TB_EFFDT").join(premiums, on="TB_POLNR").filter(
        pl.col("PR_RCVDT").le(pl.col("TB_EFFDT")))
    received = paid.group_by(EVENT).agg(RECEIVED=pl.col("PR_AMTRC").sum())
    return payouts.join(received, on=EVENT, how="left").with_columns(pl.col("RECEIVED").fill_null(0))


def premiums_used(turn: pl.DataFrame) -> pl.DataFrame:
    """The payouts of one turn with USED: their share of the premiums that the EARLIER payouts left over."""
    left_over = pl.col("RECEIVED").cast(pl.Int128).mul(BASIS_UNIT).sub(pl.col("EARLIER"))
    return turn.with_columns(USED=rounded(left_over.mul(pl.col("PART")), pl.col("WHOLE"), pl.lit(True)))


def gains(legacy_dir, payouts: pl.DataFrame) -> pl.DataFrame:
    """`payouts` with USED and GAIN (millionths of a cent of the policy currency), in processing order."""
    ordered = received_until(legacy_dir, payouts).sort("TB_CHGTS", "TB_EVTNR")
    used = in_turn(ordered, "TB_POLNR", premiums_used, "USED")
    return used.with_columns(GAIN=pl.col("GROSS").cast(pl.Int128).mul(BASIS_UNIT).sub(pl.col("USED")))


def german_factor() -> pl.Expr:
    """The taxed share of a German gain (FACTOR_UNIT): 1 - TFS, half of it under HEV, 0 for old contracts."""
    start, day = as_date("PH_BEGDT"), as_date("TB_EFFDT")
    held = day.ge(start.dt.offset_by(f"{HELD_YEARS}y"))
    age = pl.when(start.ge(HALF_INCOME_2012)).then(HALF_INCOME_AGE[True]).otherwise(HALF_INCOME_AGE[False])
    aged = day.ge(as_lenient_date("PS_BIRTH").dt.offset_by(pl.format("{}y", age)))
    half_income = pl.all_horizontal(held, start.ge(OLD_CONTRACT), aged)
    taxed = pl.lit(RATE_UNIT).sub(pl.col("TFS").fill_null(0))
    counted = pl.when(half_income).then(pl.col("HEV").fill_null(RATE_UNIT)).otherwise(RATE_UNIT)
    return pl.when(held.and_(start.lt(OLD_CONTRACT))).then(0).otherwise(taxed.mul(counted))


def taxable_base() -> pl.Expr:
    """The taxable base in cents of the tax currency: the gross or the gain by country, converted, rounded once."""
    country = pl.col("AD_CNTRY")
    taxed = pl.when(country.is_in(TAXED_ON_GROSS)).then(pl.col("GROSS").cast(pl.Int128).mul(BASIS_UNIT)).when(
        country.is_in(TAXED_ON_GAIN)).then(pl.col("GAIN").clip(0)).otherwise(0)
    factor = pl.when(country.is_in(PARTLY_TAXED)).then(german_factor()).otherwise(FACTOR_UNIT)
    converted = taxed.mul(pl.col("RP")).mul(factor)
    whole = pl.col("RT").cast(pl.Int128).mul(BASIS_UNIT).mul(FACTOR_UNIT)
    return rounded(converted, whole, country.is_in(TRUNCATED).not_()).fill_null(0)


@functools.cache
def payouts(legacy_dir) -> pl.DataFrame:
    """Every reported payout: EVENT, the dates, GROSS, BEFORE, PART / WHOLE, GAIN, the residence (`taxpayer`)
    and TAXABLE_BASE."""
    gained = gains(legacy_dir, paid_out(legacy_dir, payout_events(legacy_dir)))
    resident = with_policies(legacy_dir, residences(legacy_dir, gained))
    converted = with_tax_currency(legacy_dir, resident, pl.col("AD_CNTRY").replace_strict(TAX_CURRENCY, default=None))
    exempt = tax_rates(legacy_dir, tax_rates(legacy_dir, converted, pl.lit("TFS"), "TFS"), pl.lit("HEV"), "HEV")
    births = table(legacy_dir, "NRPERS").select(HD_PERNR="PS_PERNR", PS_BIRTH="PS_BIRTH")
    return exempt.join(births, on="HD_PERNR", how="left").with_columns(TAXABLE_BASE=taxable_base())
