"""The unit account of t3 checked link by link against the diagnostic targets, and the statements of t4.

t3 is a chain: the calculated bookings (t3_booking) make the holdings (t3_holding), the holdings the policy
value, and the policy value the surrender value. Each link is compared with its diagnostic before the next one,
so a missing rule shows up in the first link it touches. That is how t3 was solved:

- the charges of a run on the units of the days before (the run is at 01:30), not on all the units of the day
- the admin fee split by value, its rounding cents to the largest position, counting the positions too small
  for a cent of fee
- the risk charge on the value after ADM and AMC, the entry age as counted by the system that issued the policy
- the anniversary of a start on 29 February on 28 February

The opposite pattern is a manual correction (t5): every link right and only the surrender value wrong. The
statements of t4 add up the same bookings by year, so a miss there is a manual correction too.
"""
import polars as pl

from bookings import POSITION, counted_bookings
from neuron.load import LEGACY
from neuron.targets import target
from statement import STATEMENT, annual_statements
from valuation import holdings, surrender_values, unit_account

CENTS, MILLIONTHS = 100, 1_000_000  # exact decimals of the targets -> the stored integers
STATEMENT_COLUMNS = ["premiums", "entry_charges", "admin_fees", "management_fees", "risk_charges", "total_charges"]


def stored(column: str, unit: int) -> pl.Expr:
    """The exact decimal `column` of a target as the integer the submission calculates (cents, millionths)."""
    return pl.col(column).mul(unit).cast(pl.Int64)


def differs(expected: str, predicted: str) -> pl.Expr:
    """True where `predicted` is not `expected`, also where it is missing."""
    return pl.col(expected).ne(pl.col(predicted)).fill_null(True)


def booking_mismatches() -> pl.DataFrame:
    """The bookings of t3_booking whose amount or units the unit account gets wrong (empty: all exact).

    The account has no booking IDs; NRBOOK gives them by policy, event, fund, pot and booking type.
    """
    expected = target("t3_booking", amounts=("amount_pc",), units=("units",)).select(
        BK_BOOKID="booking_id", AMOUNT=stored("amount_pc", CENTS), UNITS=stored("units", MILLIONTHS))
    key = [*POSITION, "BK_EVTNR", "BK_BKTYP"]
    account = counted_bookings(LEGACY).select("BK_BOOKID", *key).join(unit_account(LEGACY), on=key)
    both = expected.join(account, on="BK_BOOKID", how="left")
    return both.filter(pl.any_horizontal(differs("AMOUNT", "BK_AMTPC"), differs("UNITS", "BK_UNITS")))


def holding_mismatches() -> pl.DataFrame:
    """The positions of t3_holding with units whose units the account gets wrong (empty: all exact).

    The target also lists emptied positions with 0 units; `valuation.holdings` leaves them out.
    """
    expected = target("t3_holding", units=("units",)).select(
        BK_POLNR="policy_id", BK_FNDID="fund_id", BK_POTCD=pl.col("pot").cast(pl.String), DAY="valuation_date",
        UNITS=stored("units", MILLIONTHS)).filter(pl.col("UNITS").ne(0))
    days = expected["DAY"].unique().sort()
    predicted = pl.concat([holdings(LEGACY, day).with_columns(DAY=pl.lit(day)) for day in days])
    both = expected.join(predicted, on=[*POSITION, "DAY"], how="left")
    return both.filter(differs("UNITS", "BK_UNITS"))


def surrender_mismatches() -> pl.DataFrame:
    """The rows of t3_surrender_value that the submission misses, with both values and the differences.

    A right policy value (DIFFERENCE_VALUE 0) with a surrender value off by whole francs is a manual correction.
    """
    expected = target("t3_surrender_value", amounts=("surrender_value", "policy_value")).select(
        PH_POLNR="policy_id", DAY="valuation_date", VALUE_EXPECTED=stored("policy_value", CENTS),
        SURRENDER_EXPECTED=stored("surrender_value", CENTS))
    days = expected["DAY"].unique().sort()
    predicted = pl.concat([surrender_values(LEGACY, day).with_columns(DAY=pl.lit(day)) for day in days])
    both = expected.join(predicted, on=["PH_POLNR", "DAY"], how="left").with_columns(
        DIFFERENCE_VALUE=pl.col("VALUE_EXPECTED").sub(pl.col("VALUE")),
        DIFFERENCE_SURRENDER=pl.col("SURRENDER_EXPECTED").sub(pl.col("SURRENDER")))
    return both.filter(pl.any_horizontal(differs("VALUE_EXPECTED", "VALUE"),
                                         differs("SURRENDER_EXPECTED", "SURRENDER")))


def statement_mismatches() -> pl.DataFrame:
    """The rows of t4_annual_statement that the submission misses, with the difference of every amount (cents).

    The columns of the target follow STATEMENT; a difference in admin_fees alone (and so in total_charges), in
    whole francs, is a manual correction.
    """
    expected = target("t4_annual_statement", amounts=tuple(STATEMENT_COLUMNS))
    expected = expected.select(BK_POLNR="policy_id", YEAR="year", **{column: stored(column, CENTS)
                                                                     for column in STATEMENT_COLUMNS})
    both = expected.join(annual_statements(LEGACY), on=["BK_POLNR", "YEAR"], how="left")
    differences = {column: pl.col(column).sub(pl.col(amount)) for column, amount in zip(STATEMENT_COLUMNS,
                                                                                          STATEMENT, strict=True)}
    return both.select("BK_POLNR", "YEAR", **differences).filter(pl.any_horizontal(pl.all().exclude(
        "BK_POLNR", "YEAR").ne(0).fill_null(True)))
