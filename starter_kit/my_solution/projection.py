"""Projection of the offer (t2): the value of a policy month by month, from the start date to maturity.

Before signing, the customer gets an offer that shows the value at maturity if the funds grew at the yearly rate
of NRILLU. It is a simplified accounting in one amount: no fund prices, no currencies and no individual agreements,
on the policy as signed and with the parameters of the application date (`tariff`). Every month the value goes
through the steps of `MONTH`, in this order:

1. the premium due in that month comes in, less the entry charge
2. the admin fee goes out
3. the management charge goes out, at the rate of pot 2: one amount has no initial units
4. the risk charge goes out, for the sum at risk after the other charges
5. the value grows by a twelfth of the yearly rate

Amounts are integers in cents. Neuron NG (Java) rounds the charges and the growth half up to the cent; COBOL,
which projected the offers signed before the conversion, truncated them (column HALF_UP).
"""
import polars as pl

from charges import death_benefit_factors, entry_age, net_premium, risk_charge, risk_rates
from conventions import CONVERSION, MONTHS
from legacy import as_date
from money import monthly_growth, monthly_share
from tariff import signed_policies, tariffs


def premium(value: pl.Expr) -> pl.Expr:
    """`value` plus the net premium, in the months with a due premium (column DUE)."""
    return value.add(pl.when(pl.col("DUE")).then(pl.col("NET_PREMIUM")).otherwise(0))


def admin_fee(value: pl.Expr) -> pl.Expr:
    """`value` less the admin fee of the month."""
    return value.sub(pl.col("CG_ADMFEE"))


def management_charge(value: pl.Expr) -> pl.Expr:
    """`value` less the management charge of the month."""
    return value.sub(monthly_share(value, pl.col("CG_AMCP2"), pl.col("HALF_UP")))


def risk(value: pl.Expr) -> pl.Expr:
    """`value` less the risk charge of the month, at the risk rate of the policy year (column RISK_RATE)."""
    return value.sub(risk_charge(value, pl.col("RISK_RATE"), pl.col("HALF_UP")))


def growth(value: pl.Expr) -> pl.Expr:
    """`value` after the growth of the month at the illustration rate IL_RATE."""
    return monthly_growth(value, pl.col("IL_RATE"), pl.col("HALF_UP"))


MONTH = [premium, admin_fee, management_charge, risk, growth]  # the steps of every month, in Neuron's order


def offers(legacy_dir) -> pl.DataFrame:
    """Every signed policy with what its projection needs, besides the tariff columns.

    - YEARS: the policy years from the start date to the maturity date (always whole years)
    - EVERY: the months between two premiums; a single premium is paid once, so its period is the whole term
    - HALF_UP: whether Neuron NG made the offer (application date from the conversion on), else COBOL did
    - AGE, NET_PREMIUM, the death benefit factors and RISK_RATES (`charges`)
    """
    policies = tariffs(legacy_dir, signed_policies(legacy_dir)).with_columns(
        YEARS=as_date("PH_ENDDT").dt.year().sub(as_date("PH_BEGDT").dt.year()),
        HALF_UP=as_date("PH_APPDT").ge(CONVERSION))
    policies = policies.with_columns(EVERY=pl.col("PH_FREQ").replace_strict(MONTHS, default=pl.col("YEARS").mul(12)),
                                     AGE=entry_age(pl.col("HALF_UP")), NET_PREMIUM=net_premium(),
                                     **death_benefit_factors())
    return policies.join(risk_rates(legacy_dir, policies), on="PH_POLNR")


def projected_years(legacy_dir) -> pl.DataFrame:
    """PH_POLNR, YEAR (1, 2, ...) and VALUE (cents): the projected value of every offer at the end of each policy year.

    The value starts at 0 on the start date. Every month runs the steps of `MONTH`, and a policy leaves the
    projection after its last policy year: the value at its end is the projected maturity value.
    """
    policies, year_ends = offers(legacy_dir).with_columns(VALUE=pl.lit(0)), []
    for year in range(policies["YEARS"].max()):
        policies = policies.filter(pl.col("YEARS").gt(year)).with_columns(RISK_RATE=pl.col("RISK_RATES").list.get(year))
        for month in range(12):
            policies = policies.with_columns(DUE=pl.lit(year).mul(12).add(month).mod(pl.col("EVERY")).eq(0))
            for step in MONTH:
                policies = policies.with_columns(VALUE=step(pl.col("VALUE")))
        year_ends.append(policies.select("PH_POLNR", "VALUE", YEAR=pl.lit(year).add(1)))
    return pl.concat(year_ends)
