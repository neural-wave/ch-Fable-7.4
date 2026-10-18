"""The monthly charge run (event 300): admin fee, management charge and risk charge, taken in units.

The run starts at 01:30 of its trade date, before the other bookings of that day. It values every position
(fund and pot) with the units booked before that day, at the bid price and the exchange rates of the day
(`money.value_of`), and takes in this order:

1. ADM: the admin fee CG_ADMFEE valid on the trade date, at most the value of the policy
2. AMC: of every position a monthly share of its value, at the rate of its pot (CG_AMCP1, CG_AMCP2) or of an
   individual agreement. Neuron NG takes a twelfth of the yearly rate, COBOL took the days of the month in a
   year of 360 days.
3. RSK: the risk charge of a month on the value left after ADM and AMC (`charges.risk_charge`), at most that
   value. The age is the entry age at the start date, as the system that issued the policy counted it, plus the
   policy years completed on the trade date.

ADM and RSK are split over the positions (`money.allotted`): ADM by the value, RSK by the value left. Every
booking sells the units its amount is worth at the bid price. Neuron NG rounds half up, COBOL truncated.

A run values the units left by the runs before it, so `charge_bookings` takes the runs one after another: the
first run of every policy at once, then the second, and so on.
"""
import polars as pl

from bookings import POSITION, agreed_rate, counted_events
from charges import death_benefit_factors, entry_age, mortality_sex, risk_charge, yearly_risk_rate
from conventions import AGREED_MANAGEMENT, CHARGE_RUN, CHARGES, COBOL_MONTH, CONVERSION, INITIAL_POT, JAVA_MONTH
from dates import completed_years, month_days
from legacy import as_date, table, valid_on
from market import with_exchange_rates, with_prices
from money import RATE_UNIT, allotted, rounded, units_for, value_of
from tariff import signed_policies

RUN_RATES = ["BK_POLNR", "RUN", "BK_EVTNR", "BK_TRDDT", "HALF_UP", "CG_ADMFEE", "CG_AMCP1", "CG_AMCP2", "AG_RATE",
             "PERIOD", "PERIODS", "RISK_RATE", "RK_SUMIN", "DB_INSURED", "DB_VALUE", "DB_PLUS"]


def risk_ages(policies: pl.DataFrame) -> pl.DataFrame:
    """`policies` with the columns of the mortality table NRMORT for the age on the trade date BK_TRDDT."""
    issued_by_java = as_date("PH_APPDT").ge(CONVERSION)
    years = completed_years(as_date("PH_BEGDT"), as_date("BK_TRDDT"))
    return policies.with_columns(MO_TABID=pl.col("CG_MORTTB"), MO_SEX=mortality_sex(),
                                 MO_AGE=entry_age(issued_by_java).add(years))


def run_rates(legacy_dir) -> pl.DataFrame:
    """One row per charge run of a policy with the columns RUN_RATES and PH_CCY.

    - RUN: 0 for the first run of the policy, then 1, 2, ...
    - CG_*: the charges of the tariff valid on the trade date; AG_RATE: an agreed management charge or null
    - PERIOD / PERIODS: the part of the yearly management charge that a run takes
    - RISK_RATE: the yearly risk rate of the age on the trade date (`charges.yearly_risk_rate`)
    """
    events = counted_events(legacy_dir).filter(pl.col("EV_EVTTP").eq(CHARGE_RUN))
    runs = events.select(BK_POLNR="EV_POLNR", BK_EVTNR="EV_EVTNR", BK_TRDDT="EV_EFFDT").join(
        signed_policies(legacy_dir), left_on="BK_POLNR", right_on="PH_POLNR")
    tariff = valid_on(runs, table(legacy_dir, "NRCHRG"), {"TARFAM": "CG_TARFAM", "TARGEN": "CG_TARGEN"}, "BK_TRDDT",
                      "CG", newest="VLDFR")
    rates = agreed_rate(legacy_dir, tariff, AGREED_MANAGEMENT, "BK_TRDDT").with_columns(
        RUN=pl.col("BK_TRDDT").rank("ordinal").over("BK_POLNR").sub(1), HALF_UP=as_date("BK_TRDDT").ge(CONVERSION),
        **death_benefit_factors())
    months = rates.with_columns(
        PERIOD=pl.when("HALF_UP").then(1).otherwise(month_days(as_date("PH_BEGDT"), as_date("BK_TRDDT"))),
        PERIODS=pl.when("HALF_UP").then(JAVA_MONTH).otherwise(COBOL_MONTH))
    mortality = risk_ages(months).join(table(legacy_dir, "NRMORT"), on=["MO_TABID", "MO_SEX", "MO_AGE"], how="left")
    return mortality.with_columns(RISK_RATE=yearly_risk_rate()).select(*RUN_RATES, "PH_CCY")


def run_positions(legacy_dir, runs: pl.DataFrame, investments: pl.DataFrame) -> pl.DataFrame:
    """One row per run and position with units before it: BK_POLNR, RUN, the position, FP_BIDPR, RP and RF.

    BOOKED is the sum of the units of `investments` (all bookings but the charges) before the trade date.
    """
    daily = investments.group_by(*POSITION, "BK_TRDDT").agg(pl.col("BK_UNITS").sum()).sort("BK_TRDDT")
    booked = daily.with_columns(BOOKED=pl.col("BK_UNITS").cum_sum().over(POSITION)).drop("BK_UNITS")
    positions = runs.select("BK_POLNR", "RUN", "BK_TRDDT", "PH_CCY").join(daily.select(POSITION).unique(),
                                                                          on="BK_POLNR")
    held = positions.sort("BK_TRDDT").join_asof(booked, on="BK_TRDDT", by=POSITION, allow_exact_matches=False,
                                                check_sortedness=False)
    funds = held.drop_nulls("BOOKED").join(table(legacy_dir, "NRFUND"), left_on="BK_FNDID", right_on="FD_FNDID")
    priced = with_exchange_rates(legacy_dir, with_prices(legacy_dir, funds, "BK_TRDDT"), "BK_TRDDT", same_day=True)
    return priced.select("BK_POLNR", "RUN", *POSITION[1:], "BOOKED", "FP_BIDPR", "RP", "RF")


def admin_fee() -> pl.Expr:
    """The admin fee CG_ADMFEE of the run, at most the value of the policy."""
    return pl.min_horizontal("CG_ADMFEE", pl.col("VALUE").sum().over("BK_POLNR"))


def management_charge() -> pl.Expr:
    """The management charge of a position: PERIOD / PERIODS of the yearly rate of its pot on its VALUE."""
    pot_rate = pl.when(pl.col("BK_POTCD").eq(INITIAL_POT)).then("CG_AMCP1").otherwise("CG_AMCP2")
    yearly = pl.col("VALUE").mul(pl.coalesce("AG_RATE", pot_rate)).mul(pl.col("PERIOD"))
    return rounded(yearly, pl.col("PERIODS").mul(RATE_UNIT), pl.col("HALF_UP"))


def risk_total() -> pl.Expr:
    """The risk charge of the run on the value LEFT after ADM and AMC, at most that value."""
    left = pl.col("LEFT").sum().over("BK_POLNR")
    charge = risk_charge(left, pl.col("RISK_RATE").fill_null(0), pl.col("HALF_UP"))
    return pl.min_horizontal(charge, left).clip(0)


def run_charges(held: pl.DataFrame) -> pl.DataFrame:
    """The ADM, AMC and RSK bookings of the positions `held` (UNITS, prices and RUN_RATES) of one run."""
    half_up = pl.col("HALF_UP")
    valued = held.sort(POSITION).with_columns(VALUE=value_of(pl.col("UNITS"), pl.col("FP_BIDPR"), half_up))
    fees = allotted(valued.with_columns(ADM=admin_fee(), AMC=management_charge()), "ADM", "VALUE", "BK_POLNR",
                    half_up)
    left = fees.with_columns(LEFT=pl.col("VALUE").sub(pl.col("ADM")).sub(pl.col("AMC")))
    risks = allotted(left.with_columns(RSK=risk_total()), "RSK", "LEFT", "BK_POLNR", half_up)
    bookings = risks.unpivot(CHARGES, index=[*POSITION, "BK_EVTNR", "BK_TRDDT", "HALF_UP", "FP_BIDPR", "RP", "RF"],
                             variable_name="BK_BKTYP", value_name="BK_AMTPC").filter(pl.col("BK_AMTPC").gt(0))
    return bookings.with_columns(BK_UNITS=pl.lit(0).sub(units_for(pl.col("BK_AMTPC"), pl.col("FP_BIDPR"), half_up)))


def charge_bookings(legacy_dir, investments: pl.DataFrame) -> pl.DataFrame:
    """The ADM, AMC and RSK bookings of every charge run, with BK_AMTPC and BK_UNITS.

    `investments` are the bookings that do not depend on the charges (`bookings`). CHARGED holds the units that
    the runs so far took from every position.
    """
    runs = run_rates(legacy_dir)
    positions = run_positions(legacy_dir, runs, investments).partition_by("RUN", as_dict=True)
    rates = runs.drop("PH_CCY").partition_by("RUN", as_dict=True)
    charged = pl.DataFrame(schema={**dict.fromkeys(POSITION, pl.String), "CHARGED": pl.Int64})
    taken = []
    for run in sorted(positions):
        held = positions[run].join(charged, on=POSITION, how="left").with_columns(
            UNITS=pl.col("BOOKED").add(pl.col("CHARGED").fill_null(0)))
        bookings = run_charges(held.filter(pl.col("UNITS").gt(0)).join(rates[run], on=["BK_POLNR", "RUN"]))
        taken.append(bookings)
        charged = pl.concat([charged, bookings.group_by(POSITION).agg(CHARGED=pl.col("BK_UNITS").sum())]).group_by(
            POSITION).agg(pl.col("CHARGED").sum())
    return pl.concat(taken)
