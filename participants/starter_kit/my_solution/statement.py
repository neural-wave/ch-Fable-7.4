"""The annual statement (t4): per policy and calendar year the premiums paid and the charges taken.

- premiums: the received premiums PR_AMTRC that were not reversed, in the year of their money date PR_RCVDT
- entry charges: per premium booking the part of the fund's share that was not invested, in the year of its
  trade date. The funds of one premium can trade on different days: 31 December for one fund, 2 January for
  another, so its entry charge falls into two years
- admin fees, management fees and risk charges: the ADM, AMC and RSK bookings of the charge runs, in the year
  of their trade date
- total charges: the entry charges plus the three charges

The amounts are those of the unit account (`valuation.unit_account`). A policy has a statement for every year
from the year of its start date to the last year of the account, with zeros in the years without bookings.
"""
import polars as pl

from bookings import received_premiums
from conventions import CHARGES
from legacy import as_date
from tariff import signed_policies
from valuation import unit_account

STATEMENT = ["PREMIUMS", "ENTRY_CHARGE", *CHARGES, "TOTAL"]  # the amounts of a statement, in the order of t4


def yearly_premiums(legacy_dir) -> pl.DataFrame:
    """BK_POLNR, YEAR and PREMIUMS: the premiums received per policy and year of the money date."""
    premiums = received_premiums(legacy_dir).with_columns(BK_POLNR="PR_POLNR", YEAR=as_date("PR_RCVDT").dt.year())
    return premiums.group_by("BK_POLNR", "YEAR").agg(PREMIUMS=pl.col("PR_AMTRC").sum())


def yearly_charges(legacy_dir) -> pl.DataFrame:
    """BK_POLNR, YEAR, ENTRY_CHARGE and the charges ADM, AMC and RSK per policy and year of the trade date."""
    account = unit_account(legacy_dir).with_columns(YEAR=as_date("BK_TRDDT").dt.year())
    taken = {kind: pl.col("BK_AMTPC").filter(pl.col("BK_BKTYP").eq(kind)).sum() for kind in CHARGES}
    return account.group_by("BK_POLNR", "YEAR").agg(pl.col("ENTRY_CHARGE").sum(), **taken)


def statement_years(legacy_dir) -> pl.DataFrame:
    """BK_POLNR and YEAR: every policy with the years from the year of its start date to the last year of the
    account (both included)."""
    last = unit_account(legacy_dir).select(as_date("BK_TRDDT").dt.year().max()).item()
    policies = signed_policies(legacy_dir).select(BK_POLNR="PH_POLNR", FIRST=as_date("PH_BEGDT").dt.year())
    years = policies.with_columns(YEAR=pl.int_ranges("FIRST", pl.lit(last).add(1)))
    return years.explode("YEAR").drop("FIRST")


def annual_statements(legacy_dir) -> pl.DataFrame:
    """BK_POLNR, YEAR and the amounts of STATEMENT in cents, for every policy and year of `statement_years`."""
    years = statement_years(legacy_dir).join(yearly_premiums(legacy_dir), on=["BK_POLNR", "YEAR"], how="left")
    amounts = years.join(yearly_charges(legacy_dir), on=["BK_POLNR", "YEAR"], how="left").fill_null(0)
    return amounts.with_columns(TOTAL=pl.sum_horizontal("ENTRY_CHARGE", *CHARGES)).select("BK_POLNR", "YEAR",
                                                                                           *STATEMENT)
