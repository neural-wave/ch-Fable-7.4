"""Valuation of the unit account on a date, and the surrender value (t3).

- `unit_account`: every counted booking with its units, the calculated ones included (`bookings`, `charge_run`)
- holdings on a day: the units of the bookings traded on or before that day, per fund and pot
- policy value: every position at the bid price of its last price date and the exchange rates of the day,
  rounded to the cent position by position (half up from the conversion on, truncated before)
- surrender value: the policy value less the surrender penalty NRSURR of the product's scale for the policy
  years completed on that day; no penalty in the waiver periods NRWAIV or after the last year of the scale
"""
import datetime as dt
import functools

import polars as pl

from bookings import POSITION, counted_bookings, moved_bookings, premium_bookings
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
    """Every counted booking with the columns ACCOUNT: moved units, premiums and the charges of the runs."""
    bookings = counted_bookings(legacy_dir)
    investments = pl.concat([moved_bookings(bookings).select(ACCOUNT),
                             premium_bookings(legacy_dir, bookings).select(ACCOUNT)])
    return pl.concat([investments, charge_bookings(legacy_dir, investments).select(ACCOUNT)])


def holdings(legacy_dir, day: dt.date) -> pl.DataFrame:
    """The positions with units on `day`: POSITION and BK_UNITS, from the bookings traded on or before `day`."""
    traded = unit_account(legacy_dir).filter(pl.col("BK_TRDDT").le(as_cyymmdd(day)))
    positions = traded.group_by(POSITION).agg(pl.col("BK_UNITS").sum())
    return positions.filter(pl.col("BK_UNITS").ne(0))


def policy_values(legacy_dir, day: dt.date) -> pl.DataFrame:
    """PH_POLNR and VALUE (cents) of every policy on `day`: 0 without units."""
    policies = signed_policies(legacy_dir).select("PH_POLNR", "PH_CCY")
    positions = holdings(legacy_dir, day).join(policies, left_on="BK_POLNR", right_on="PH_POLNR").join(
        table(legacy_dir, "NRFUND"), left_on="BK_FNDID", right_on="FD_FNDID").with_columns(DAY=as_cyymmdd(day))
    priced = with_exchange_rates(legacy_dir, with_prices(legacy_dir, positions, "DAY"), "DAY", same_day=True)
    valued = priced.with_columns(VALUE=value_of(pl.col("BK_UNITS"), pl.col("FP_BIDPR"), pl.lit(day).ge(CONVERSION)))
    values = valued.group_by("BK_POLNR").agg(pl.col("VALUE").sum())
    return policies.join(values, left_on="PH_POLNR", right_on="BK_POLNR", how="left").select(
        "PH_POLNR", pl.col("VALUE").fill_null(0))


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
