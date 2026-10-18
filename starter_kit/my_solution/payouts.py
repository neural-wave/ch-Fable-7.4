"""The payouts of the policies and their taxable base (t7).

A payout is an event 400 (partial withdrawal), 410 (full surrender) or 500 (death claim) that has a tax booking or
was not reversed. Every one is reported, also without any tax (residents of Luxembourg, Swiss holders who accept
the reporting, old German contracts, ...). The rows have the columns of NRTAXB: TB_EFFDT and TB_CHGTS are the
effective date and the processing timestamp of the event, the same as those of its tax bookings.

- country: the country of the taxes withheld from the payout, a label of NRTAXB; without them the residence of the
  holder as Neuron knew it (`taxpayer`)
- units sold: the negative BK_AMTPC of the WDR, SUR and DTH bookings (policy currency), the units at their value
- gross: the money paid out, the units sold less the surrender penalty of the day for a withdrawal or a surrender
  (`conventions.PENALIZED`, `valuation.penalties_on`), the death benefit of the tariff option on the units sold for a
  death claim (`conventions.DEATH_CLAIM`), rounded once as the surrender value of t3
- value before: the units sold plus the policy value left at the end of the day (`valuation.values_on`)
- share PART / WHOLE: what the payout takes of the policy, units sold / value before; all of it when it ends the
  policy
- premiums used: the share of the premiums received up to the payout day that no earlier payout used. Each premium
  is converted to the tax currency at the rates of its money date and rounded to the cent by the system (COBOL
  truncates, Neuron NG rounds half up: `taxpayer.rounds_half_up`; truncated in Germany without
  `conventions.ROUNDED_BY_SYSTEM`). The payouts of a policy use them
  one after another (`in_turn`), each payout its share rounded to the cent (kept in BASIS_UNIT)
- gain: the gross, converted on the payout day, less the premiums used

PDF example 1 (BL10000086 #121, a USD policy of a German holder) gives its base 5628.16 only so: rounding every
premium half up gives 5628.01, not rounding them 5628.02, converting the whole gain on the payout day 539.30.

The taxable base is in the currency of the country (`taxpayer`), rounded once (as the premiums): in
Switzerland the gross, the withholding tax VST takes the whole benefit; in Italy and Germany the gain, at least 0;
elsewhere none. In Germany a contract with regular premiums started before 2005 and held 12 years is tax free,
one with a single premium is not (NRTAXB books KST on all of them with a gain). The partial exemption of fund
policies from 2018 (TFS) and the half-income rule (HEV: a later contract held 12 years, from the age of 60, or 62
for contracts started from 2012) reduce the base only with `conventions.PARTIAL_EXEMPTION_WITHHELD` and
`conventions.HALF_INCOME_WITHHELD`; Neuron left both to the assessment.
"""
import functools
from collections.abc import Callable

import polars as pl

from bookings import counted_events, received_premiums, uncharged_bookings
from charges import death_benefit_factors
from conventions import (CONVERSION, DEATH_CLAIM, HALF_INCOME_2012, HALF_INCOME_AGE, HALF_INCOME_WITHHELD, HELD_YEARS,
                         OLD_CONTRACT, PAID_OUT, PARTIAL_EXEMPTION_WITHHELD, PARTLY_TAXED, PAYOUTS, PENALIZED,
                         ROUNDED_BY_SYSTEM, SINGLE_PREMIUM, TAX_CURRENCY, TAXED_ON_GAIN, TAXED_ON_GROSS, TAXES,
                         TERMINATING, TRUNCATED_CONVERSION, WITHHELD)
from dates import public_holidays
from legacy import as_cyymmdd, as_date, as_lenient_date, table
from money import RATE_UNIT, SHARE_UNIT, rounded
from tariff import signed_policies
from taxpayer import residences, rounds_half_up, tax_rates, with_policies, with_tax_currency
from valuation import penalties_on, values_on

BASIS_UNIT = RATE_UNIT  # the premiums used are kept in millionths of a cent, so a share loses nothing in the cents
FACTOR_UNIT = SHARE_UNIT  # the German factor: two rates in millionths multiplied
EVENT = ["TB_POLNR", "TB_EVTNR"]  # the key of an event, e.g. of a payout
SCHEME = ["TAX_CCY", "CONVERTED_HALF_UP"]  # how the premiums of a payout are converted: currency and rounding


def in_turn(rows: pl.DataFrame, key: str, step: Callable[[pl.DataFrame], pl.DataFrame], carried: str) -> pl.DataFrame:
    """`rows`, sorted in processing order, handled one after another per `key` (e.g. per policy).

    `step` gets the rows of one turn with EARLIER: the sum of the column `carried` that `step` added to the rows
    of the same `key` in the turns before (0 in the first). The turns are the first row of every key at once,
    then the second, and so on, like the charge runs. No rows give no rows, with the column `carried`.
    """
    if rows.is_empty():
        return step(rows.with_columns(EARLIER=pl.lit(0, pl.Int128))).drop("EARLIER")
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
    """EVENT, TB_EFFDT, TB_CHGTS, FULL (the payout ends the policy), PENALIZED (it pays the units less the
    surrender penalty), DEATH (it pays the death benefit), PAID and the death benefit columns of every payout event
    that is reported.

    PAID is the day the money is paid: the effective date plus the payout business days PD_PAYDAY of the product
    (NRPROD), in Neuron's calendar (`dates.public_holidays`).
    """
    events = table(legacy_dir, "NREVNT").filter(pl.col("EV_EVTTP").is_in(PAYOUTS))
    booked = table(legacy_dir, "NRTAXB").select(EV_POLNR="TB_POLNR", EV_EVTNR="TB_EVTNR")
    reported = pl.concat([booked, counted_events(legacy_dir).select("EV_POLNR", "EV_EVTNR")]).unique()
    products = signed_policies(legacy_dir).join(table(legacy_dir, "NRPROD"), left_on="PH_PRDCD", right_on="PD_PRDCD")
    paydays = products.select(EV_POLNR="PH_POLNR", PAYDAY="PD_PAYDAY", RK_SUMIN="RK_SUMIN",
                              **death_benefit_factors())
    paid = as_date("EV_EFFDT").dt.add_business_days(pl.col("PAYDAY"), holidays=public_holidays(), roll="forward")
    return events.join(reported, on=["EV_POLNR", "EV_EVTNR"]).join(paydays, on="EV_POLNR", how="left").select(
        TB_POLNR="EV_POLNR", TB_EVTNR="EV_EVTNR", TB_EFFDT="EV_EFFDT", TB_CHGTS="EV_CHGTS",
        FULL=pl.col("EV_EVTTP").is_in(TERMINATING), PENALIZED=pl.col("EV_EVTTP").is_in(PENALIZED),
        DEATH=pl.col("EV_EVTTP").eq(DEATH_CLAIM), PAID=paid, RK_SUMIN="RK_SUMIN", DB_INSURED="DB_INSURED",
        DB_VALUE="DB_VALUE", DB_PLUS="DB_PLUS")


def money_paid() -> pl.Expr:
    """The money paid: the units SOLD less the surrender penalty SR_RATE of the day for a PENALIZED payout, the death
    benefit of the tariff option on the units SOLD for a death claim (the higher of DB_INSURED x sum insured and
    DB_VALUE x SOLD, plus DB_PLUS x sum insured), each rounded once as the surrender value
    (`valuation.surrender_values`)."""
    kept = pl.col("SOLD").mul(pl.lit(RATE_UNIT).sub(pl.col("SR_RATE")))
    insured = pl.col("RK_SUMIN").fill_null(0)
    benefit = pl.max_horizontal(insured.mul(pl.col("DB_INSURED")), pl.col("SOLD").mul(pl.col("DB_VALUE"))).add(
        insured.mul(pl.col("DB_PLUS")))
    half_up = as_date("TB_EFFDT").ge(CONVERSION)
    return pl.when(pl.col("PENALIZED")).then(rounded(kept, RATE_UNIT, half_up)).when(pl.col("DEATH")).then(
        rounded(benefit, RATE_UNIT, half_up)).otherwise("SOLD")


def paid_out(legacy_dir, payouts: pl.DataFrame) -> pl.DataFrame:
    """`payouts` with GROSS (`money_paid`) and BEFORE (cents of the policy currency) and their share PART / WHOLE.

    BEFORE and the share count the units SOLD at their value, as the bookings do; only the money paid loses the
    penalty.
    """
    money = uncharged_bookings(legacy_dir).filter(pl.col("BK_BKTYP").is_in(PAID_OUT)).group_by(
        TB_POLNR="BK_POLNR", TB_EVTNR="BK_EVTNR").agg(SOLD=pl.col("BK_AMTPC").sum().neg())
    sold = payouts.join(money, on=EVENT, how="left").with_columns(pl.col("SOLD").fill_null(0))
    days = sold.select(BK_POLNR="TB_POLNR", DAY="TB_EFFDT").unique()
    left = values_on(legacy_dir, days).select(TB_POLNR="BK_POLNR", TB_EFFDT="DAY", LEFT="VALUE")
    penalties = penalties_on(legacy_dir, days).select(TB_POLNR="BK_POLNR", TB_EFFDT="DAY", SR_RATE="SR_RATE")
    before = sold.join(left, on=["TB_POLNR", "TB_EFFDT"]).join(penalties, on=["TB_POLNR", "TB_EFFDT"],
                                                               how="left").with_columns(
        BEFORE=pl.col("SOLD").add(pl.col("LEFT")))
    whole = pl.col("FULL").or_(pl.col("BEFORE").le(0))
    return before.with_columns(PART=pl.when(whole).then(1).otherwise(pl.min_horizontal("SOLD", "BEFORE")),
                               WHOLE=pl.when(whole).then(1).otherwise("BEFORE"), GROSS=money_paid()).drop(
        "LEFT", "SOLD", "SR_RATE", "RK_SUMIN", "DB_INSURED", "DB_VALUE", "DB_PLUS")


def booked_countries(legacy_dir) -> pl.DataFrame:
    """EVENT and BOOKED_CNTRY of the payouts with a tax withheld: the country of that tax (`conventions.TAXES`).

    The bookings are labels: they say for which country Neuron taxed the payout, whatever the address says.
    """
    withheld = table(legacy_dir, "NRTAXB").filter(pl.col("TB_TAXTP").is_in(WITHHELD))
    return withheld.group_by(EVENT).agg(BOOKED_CNTRY=pl.col("TB_TAXTP").replace_strict(TAXES).min())


def converted_premiums(legacy_dir, schemes: pl.DataFrame) -> pl.DataFrame:
    """TB_POLNR, SCHEME, PR_RCVDT and PREMIUM of the received premiums (not reversed) of the policies of `schemes`
    (TB_POLNR, PH_CCY and SCHEME), once per scheme: PR_AMTRC in cents of TAX_CCY at the rates of its money date,
    rounded to the cent by the system that received it (COBOL truncates, Neuron NG rounds half up), or as the scheme
    says without `conventions.ROUNDED_BY_SYSTEM` (public samples: the gains of the policies with premiums of both
    systems; a premium from before the euro too, with the first rate)."""
    premiums = received_premiums(legacy_dir).select(TB_POLNR="PR_POLNR", PR_RCVDT="PR_RCVDT", PR_AMTRC="PR_AMTRC")
    rated = with_tax_currency(legacy_dir, schemes.join(premiums, on="TB_POLNR"), pl.col("TAX_CCY"), "PR_RCVDT")
    amount = pl.col("PR_AMTRC").cast(pl.Int128).mul(pl.col("RP"))
    half_up = pl.when(pl.lit(ROUNDED_BY_SYSTEM)).then(pl.col("PR_RCVDT").ge(as_cyymmdd(CONVERSION))).otherwise(
        pl.col("CONVERTED_HALF_UP"))
    return rated.select("TB_POLNR", *SCHEME, "PR_RCVDT", PREMIUM=rounded(amount, pl.col("RT"), half_up))


def received_until(legacy_dir, chains: pl.DataFrame, schemes: pl.DataFrame) -> pl.DataFrame:
    """`chains` (payouts with a SCHEME) with RECEIVED: the premiums received up to the payout day, converted in
    that scheme (`converted_premiums`), in cents of TAX_CCY."""
    premiums = converted_premiums(legacy_dir, schemes)
    paid = chains.select(*EVENT, "TB_EFFDT", *SCHEME).join(premiums, on=["TB_POLNR", *SCHEME]).filter(
        pl.col("PR_RCVDT").le(pl.col("TB_EFFDT")))
    received = paid.group_by(*EVENT, *SCHEME).agg(RECEIVED=pl.col("PREMIUM").sum())
    return chains.join(received, on=[*EVENT, *SCHEME], how="left").with_columns(pl.col("RECEIVED").fill_null(0))


def premiums_used(turn: pl.DataFrame) -> pl.DataFrame:
    """The payouts of one turn with USED: their share of the premiums that the EARLIER payouts left over, rounded to
    the cent as the scheme says (kept in BASIS_UNIT), so a later payout takes the rest of rounded amounts (public
    samples: 2 payouts, both after an earlier withdrawal)."""
    left_over = pl.col("RECEIVED").cast(pl.Int128).mul(BASIS_UNIT).sub(pl.col("EARLIER"))
    whole = pl.col("WHOLE").cast(pl.Int128).mul(BASIS_UNIT)
    return turn.with_columns(
        USED=rounded(left_over.mul(pl.col("PART")), whole, pl.col("CONVERTED_HALF_UP")).mul(BASIS_UNIT))


def premium_chains(legacy_dir, payouts: pl.DataFrame) -> pl.DataFrame:
    """Every payout of `payouts` once per SCHEME of the payouts of its policy, with TB_EFFDT, TB_CHGTS, PART,
    WHOLE, CHAIN (policy and scheme) and USED: the premiums it uses, in millionths of a cent of TAX_CCY.

    The payouts of a policy use the premiums one after another, in processing order. The chain runs once per
    SCHEME of the payouts of the policy, so a holder who moved (CH -> DE) has the earlier payouts counted in the
    currency and rounding of the later one.
    """
    schemes = payouts.select("TB_POLNR", "PH_CCY", *SCHEME).drop_nulls().unique()
    chains = payouts.select(*EVENT, "TB_EFFDT", "TB_CHGTS", "PART", "WHOLE").join(schemes.drop("PH_CCY"),
                                                                                    on="TB_POLNR")
    received = received_until(legacy_dir, chains, schemes).with_columns(
        CHAIN=pl.concat_str("TB_POLNR", "TAX_CCY", pl.col("CONVERTED_HALF_UP").cast(pl.String)))
    return in_turn(received.sort("TB_CHGTS", "TB_EVTNR"), "CHAIN", premiums_used, "USED")


def gains(legacy_dir, payouts: pl.DataFrame) -> pl.DataFrame:
    """`payouts` with USED: the premiums the payout uses in its own scheme (`premium_chains`)."""
    used = premium_chains(legacy_dir, payouts)
    return payouts.join(used.select(*EVENT, *SCHEME, "USED"), on=[*EVENT, *SCHEME], how="left")


def german_factor() -> pl.Expr:
    """The taxed share of a German gain (FACTOR_UNIT): 1 - TFS with `conventions.PARTIAL_EXEMPTION_WITHHELD`, half of
    it under HEV with `conventions.HALF_INCOME_WITHHELD`, 0 for old contracts with regular premiums."""
    start, day = as_date("PH_BEGDT"), as_date("TB_EFFDT")
    held = day.ge(start.dt.offset_by(f"{HELD_YEARS}y"))
    age = pl.when(start.ge(HALF_INCOME_2012)).then(HALF_INCOME_AGE[True]).otherwise(HALF_INCOME_AGE[False])
    aged = day.ge(as_lenient_date("PS_BIRTH").dt.offset_by(pl.format("{}y", age)))
    half_income = pl.all_horizontal(held, start.ge(OLD_CONTRACT), aged, pl.lit(HALF_INCOME_WITHHELD))
    exempt_share = pl.when(pl.lit(PARTIAL_EXEMPTION_WITHHELD)).then(pl.col("TFS").fill_null(0)).otherwise(0)
    taxed = pl.lit(RATE_UNIT).sub(exempt_share)
    counted = pl.when(half_income).then(pl.col("HEV").fill_null(RATE_UNIT)).otherwise(RATE_UNIT)
    exempt = pl.all_horizontal(held, start.lt(OLD_CONTRACT), pl.col("PH_FREQ").ne(SINGLE_PREMIUM))
    return pl.when(exempt).then(0).otherwise(taxed.mul(counted))


def taxable_base() -> pl.Expr:
    """The taxable base in cents of the tax currency: the gross or the gain by country.

    The gross converted on the payout day (RP / RT) and the premiums USED are each rounded to the cent by the system
    (public samples: a base of 2004 matches only with both truncated; the example fits it), so the gain is a difference
    of cents; only the German factor rounds it again.
    """
    country = pl.col("COUNTRY")
    half_up = rounds_half_up(country)
    gross = rounded(pl.col("GROSS").cast(pl.Int128).mul(pl.col("RP")), pl.col("RT"), half_up)
    gain = gross.sub(rounded(pl.col("USED"), BASIS_UNIT, half_up))
    taxed = pl.when(country.is_in(TAXED_ON_GROSS)).then(gross).when(country.is_in(TAXED_ON_GAIN)).then(
        gain.clip(0)).otherwise(0)
    factor = pl.when(country.is_in(PARTLY_TAXED)).then(german_factor()).otherwise(FACTOR_UNIT)
    return rounded(taxed.mul(factor), FACTOR_UNIT, half_up).fill_null(0)


@functools.cache
def payouts(legacy_dir) -> pl.DataFrame:
    """Every reported payout: EVENT, the dates, GROSS, BEFORE, PART / WHOLE, the residence (`taxpayer`), COUNTRY,
    the tax currency TAX_CCY with the rates RP / RT of the payout day, USED and TAXABLE_BASE."""
    paid = paid_out(legacy_dir, payout_events(legacy_dir))
    resident = with_policies(legacy_dir, residences(legacy_dir, paid)).join(booked_countries(legacy_dir), on=EVENT,
                                                                            how="left")
    country = pl.coalesce("BOOKED_CNTRY", "AD_CNTRY")
    schemed = resident.with_columns(COUNTRY=country, CONVERTED_HALF_UP=rounds_half_up(country, TRUNCATED_CONVERSION))
    converted = with_tax_currency(legacy_dir, schemed, pl.col("COUNTRY").replace_strict(TAX_CURRENCY, default=None))
    gained = gains(legacy_dir, converted)
    exempt = tax_rates(legacy_dir, tax_rates(legacy_dir, gained, pl.lit("TFS"), "TFS"), pl.lit("HEV"), "HEV")
    births = table(legacy_dir, "NRPERS").select(HD_PERNR="PS_PERNR", PS_BIRTH="PS_BIRTH")
    return exempt.join(births, on="HD_PERNR", how="left").with_columns(TAXABLE_BASE=taxable_base())
