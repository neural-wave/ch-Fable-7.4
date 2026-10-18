"""The charges of Neuron and the risk of the insured person, as polars expressions on amounts in cents.

- entry charge: a share EC_RATE of every premium, kept before the rest is invested
- admin fee: a fixed amount CG_ADMFEE per month
- management charge: a yearly share of the value, taken every month (`money.monthly_share`)
- risk charge: every month a twelfth of the yearly risk rate times the sum at risk

The yearly risk rate is the death probability MO_QX of the age of the insured person, times the smoker factor
CG_SMKFAC for smokers, times 1 + the medical loading RK_LOAD. The sum at risk carries the millionths of the death
benefit factors (`conventions.DEATH_BENEFIT`), so a risk charge multiplies four factors in millionths
(`RISK_UNIT`); polars keeps that product exact in 128-bit integers.
"""
import math

import polars as pl

from conventions import COBOL_AGE, DEATH_BENEFIT, JAVA_AGE, SEX_BASIS, SMOKER
from dates import completed_months, days_between
from legacy import as_date, as_lenient_date, table
from money import RATE_UNIT, rounded, share

RISK_UNIT = math.prod([12, RATE_UNIT, RATE_UNIT, RATE_UNIT, RATE_UNIT])  # 12 months x four factors in millionths


def net_premium() -> pl.Expr:
    """The premium PH_PREMI less the entry charge at the rate EC_RATE: the amount that is invested."""
    return pl.col("PH_PREMI").sub(share(pl.col("PH_PREMI"), pl.col("EC_RATE")))


def entry_age(java: pl.Expr) -> pl.Expr:
    """The age of the insured person on the start date PH_BEGDT, rounded half up.

    Neuron NG (`java`) counts completed months: 6 months after a birthday the age goes up. COBOL counted days and
    divided by 365, so every leap day since the birth moves its age up a day earlier.
    """
    birth, start = as_lenient_date("PS_BIRTH"), as_date("PH_BEGDT")
    in_months = rounded(completed_months(birth, start), JAVA_AGE, half_up=pl.lit(True))
    in_days = rounded(days_between(birth, start), COBOL_AGE, half_up=pl.lit(True))
    return pl.when(java).then(in_months).otherwise(in_days)


def mortality_sex() -> pl.Expr:
    """MO_SEX of the mortality table: the sex basis of the tariff, or the sex of the person for unisex tariffs."""
    return pl.col("SEXB").replace_strict(SEX_BASIS, default=pl.col("PS_SEX"))


def yearly_risk_rate() -> pl.Expr:
    """MO_QX times the smoker factor and the medical loading, in units of 1e-18 (three factors in millionths)."""
    smoker = pl.when(pl.col("PS_SMOKE").eq(SMOKER)).then(pl.col("CG_SMKFAC")).otherwise(RATE_UNIT)
    return pl.col("MO_QX").cast(pl.Int128).mul(smoker).mul(pl.col("RK_LOAD").add(RATE_UNIT))


def risk_rates(legacy_dir, policies: pl.DataFrame) -> pl.DataFrame:
    """PH_POLNR and RISK_RATES: the list of the yearly risk rates of every policy year, from the first one on.

    `policies` needs the entry age AGE, the number of policy years YEARS and the tariff columns. The age goes up by
    one every policy year, and the death probability comes from the mortality table CG_MORTTB of the tariff.
    """
    years = policies.with_columns(YEAR=pl.int_ranges(0, "YEARS")).explode("YEAR")
    ages = years.with_columns(MO_TABID=pl.col("CG_MORTTB"), MO_SEX=mortality_sex(),
                              MO_AGE=pl.col("AGE").add(pl.col("YEAR")))
    rates = ages.join(table(legacy_dir, "NRMORT"), on=["MO_TABID", "MO_SEX", "MO_AGE"])
    return rates.group_by("PH_POLNR").agg(RISK_RATES=yearly_risk_rate().sort_by("YEAR"))


def death_benefit_factor(place: int) -> pl.Expr:
    """The factor number `place` (millionths) of the death benefit option OPTION in `conventions.DEATH_BENEFIT`."""
    return pl.col("OPTION").replace_strict({option: factors[place] for option, factors in DEATH_BENEFIT.items()})


def death_benefit_factors() -> dict[str, pl.Expr]:
    """DB_INSURED, DB_VALUE and DB_PLUS: the death benefit is the higher of DB_INSURED x sum insured and
    DB_VALUE x value, plus DB_PLUS x sum insured."""
    return {"DB_INSURED": death_benefit_factor(0), "DB_VALUE": death_benefit_factor(1),
            "DB_PLUS": death_benefit_factor(2)}


def sum_at_risk(value: pl.Expr) -> pl.Expr:
    """The death benefit less `value`, in cents x millionths: what the insurer really risks.

    The factors of the death benefit are at least 100 % of the value, so the sum at risk is never negative.
    """
    insured = pl.col("RK_SUMIN")
    benefit = pl.max_horizontal(insured.mul(pl.col("DB_INSURED")), value.mul(pl.col("DB_VALUE")))
    return benefit.add(insured.mul(pl.col("DB_PLUS"))).sub(value.mul(RATE_UNIT))


def risk_charge(value: pl.Expr, yearly_rate: pl.Expr, half_up: pl.Expr) -> pl.Expr:
    """The risk charge of one month on `value`, in cents: rounded half up or truncated as `half_up` says."""
    charge = sum_at_risk(value).cast(pl.Int128).mul(yearly_rate)
    return rounded(charge, RISK_UNIT, half_up).cast(pl.Int64)
