"""Valuation of the unit account on a date, and the surrender value (t3).

- `unit_account`: every counted booking with its units, the calculated ones included (`bookings`, `charge_run`)
- holdings on a day: the units of the bookings traded on or before that day, per fund and pot
- policy value: every position at the bid price of its last price date and the exchange rates of the day,
  rounded to the cent position by position (half up from the conversion on, truncated before); `values_on`
  values any policy on any day, e.g. on the days of the payouts and of the Bollo (t7)
- surrender value: the policy value less the surrender penalty NRSURR of the product's scale for the policy
  years completed on that day; no penalty in the waiver periods NRWAIV or after the last year of the scale
"""
import datetime as dt
import functools

import polars as pl

from bookings import POSITION, investment_bookings, moved_bookings, premium_bookings
from charge_run import charge_bookings
from conventions import CONVERSION
from dates import completed_years
from legacy import as_cyymmdd, as_date, table
from market import with_exchange_rates, with_prices
from money import RATE_UNIT, rounded, value_of
from tariff import signed_policies

ACCOUNT = [*POSITION, "BK_EVTNR", "BK_BKTYP", "BK_TRDDT", "BK_AMTPC", "BK_UNITS"]  # the columns of a booking


@functools.cache
def unit_account(legacy_dir) -> pl.DataFrame:
    """Every counted booking with the columns ACCOUNT: moved units, premiums and the charges of the runs.

    The premiums also have their ENTRY_CHARGE (`bookings.premium_bookings`); the other bookings have null there.
    """
    bookings = investment_bookings(legacy_dir)
    investments = pl.concat([moved_bookings(bookings).select(ACCOUNT),
                             premium_bookings(legacy_dir, bookings).select(*ACCOUNT, "ENTRY_CHARGE")], how="diagonal")
    return pl.concat([investments, charge_bookings(legacy_dir, investments).select(ACCOUNT)], how="diagonal")


def holdings(legacy_dir, day: dt.date) -> pl.DataFrame:
    """The positions with units on `day`: POSITION and BK_UNITS, from the bookings traded on or before `day`."""
    traded = unit_account(legacy_dir).filter(pl.col("BK_TRDDT").le(as_cyymmdd(day)))
    positions = traded.group_by(POSITION).agg(pl.col("BK_UNITS").sum())
    return positions.filter(pl.col("BK_UNITS").ne(0))


def policy_values(legacy_dir, day: dt.date) -> pl.DataFrame:
    """PH_POLNR and VALUE (cents) of every policy on `day`: 0 without units."""
    policies = signed_policies(legacy_dir).select(BK_POLNR="PH_POLNR", DAY=as_cyymmdd(day))
    return values_on(legacy_dir, policies).select(PH_POLNR="BK_POLNR", VALUE="VALUE")


def values_on(legacy_dir, days: pl.DataFrame) -> pl.DataFrame:
    """`days` (BK_POLNR and DAY, a date `CYYMMDD`) with VALUE: the policy value (cents) at the end of DAY.

    The units traded on or before DAY, at the bid price and the exchange rates of DAY; 0 without units. The
    units of every position are added up per trade date once, and each DAY takes the sum of its last trade date
    (as `charge_run.run_positions`), so the account is never copied per day.
    """
    pairs = days.select("BK_POLNR", "DAY").unique()
    account = unit_account(legacy_dir).join(pairs.select("BK_POLNR").unique(), on="BK_POLNR", how="semi")
    daily = account.group_by(*POSITION, "BK_TRDDT").agg(pl.col("BK_UNITS").sum()).sort("BK_TRDDT")
    booked = daily.with_columns(pl.col("BK_UNITS").cum_sum().over(POSITION))
    wanted = pairs.join(daily.select(POSITION).unique(), on="BK_POLNR").sort("DAY")
    held = wanted.join_asof(booked, left_on="DAY", right_on="BK_TRDDT", by=POSITION,
                               check_sortedness=False).filter(pl.col("BK_UNITS").ne(0))
    currencies = signed_policies(legacy_dir).select(BK_POLNR="PH_POLNR", PH_CCY="PH_CCY")
    positions = held.join(currencies, on="BK_POLNR").join(table(legacy_dir, "NRFUND"), left_on="BK_FNDID",
                                                          right_on="FD_FNDID")
    priced = with_exchange_rates(legacy_dir, with_prices(legacy_dir, positions, "DAY"), "DAY", same_day=True)
    valued = priced.with_columns(VALUE=value_of(pl.col("BK_UNITS"), pl.col("FP_BIDPR"),
                                                as_date("DAY").ge(CONVERSION)))
    values = valued.group_by("BK_POLNR", "DAY").agg(pl.col("VALUE").sum())
    return days.join(values, on=["BK_POLNR", "DAY"], how="left").with_columns(pl.col("VALUE").fill_null(0))


def penalty_rates(legacy_dir, day: dt.date) -> pl.DataFrame:
    """PH_POLNR and SR_RATE: the surrender penalty (millionths) of every policy on `day`.

    The scale PD_SRPSCL of the product has a rate per completed policy year SR_YEAR; later years and the days
    of a waiver period have none.
    """
    waivers = table(legacy_dir, "NRWAIV").filter(as_cyymmdd(day).is_between(pl.col("WV_VLDFR"), pl.col("WV_VLDTO")))
    products = signed_policies(legacy_dir).join(table(legacy_dir, "NRPROD"), left_on="PH_PRDCD", right_on="PD_PRDCD")
    years = products.with_columns(SR_SCALE="PD_SRPSCL", SR_YEAR=completed_years(as_date("PH_BEGDT"), pl.lit(day)))
    scale = table(legacy_dir, "NRSURR").filter(pl.lit(waivers.is_empty()))
    rates = years.join(scale, on=["SR_SCALE", "SR_YEAR"], how="left")
    return rates.select("PH_POLNR", pl.col("SR_RATE").fill_null(0))


def surrender_values(legacy_dir, day: dt.date) -> pl.DataFrame:
    """PH_POLNR, VALUE and SURRENDER (cents) of every policy on `day`: the value less the penalty, rounded once.

    The surrender value is never below 0, though the value can be: when the value no longer covers the charges,
    the run takes all of it in ADM and the management charge of the same run goes below zero.
    """
    values = policy_values(legacy_dir, day).join(penalty_rates(legacy_dir, day), on="PH_POLNR")
    kept = pl.col("VALUE").mul(pl.lit(RATE_UNIT).sub(pl.col("SR_RATE")))
    return values.with_columns(SURRENDER=rounded(kept, RATE_UNIT, pl.lit(day).ge(CONVERSION)).clip(0))
