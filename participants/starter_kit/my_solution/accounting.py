"""t3: the fund accounting of the policies, run by run (tools/detective/llm/011-t3-runs-story.md).

The units of a fund and pot come from the premium bookings (`premiums`), the customer orders (switches,
withdrawals, surrenders and death claims, complete in NRBOOK) and the charges of the runs (`charges`), which take
a share of the units held before each run. A run therefore needs the units the earlier runs left, and the runs go
in turn: the first run of every policy, then the second, and so on. A run sees the bookings traded before its
day.
"""
import polars as pl

from charges import charges_of, run_rows
from events import ignored
from legacy import table
from premiums import premium_bookings
from runs import charge_dates

ORDERS = ["SWO", "SWI", "WDR", "SUR", "DTH"]  # BKTYP of the customer orders
POT = ["BK_POLNR", "BK_FNDID", "BK_POTCD"]
COLUMNS = ["BK_POLNR", "BK_EVTNR", "BK_FNDID", "BK_POTCD", "BK_BKTYP", "BK_TRDDT", "BK_PRCDT", "BK_AMTPC", "BK_FXRAT",
           "BK_PRICE", "BK_UNITS"]


def orders(legacy_dir) -> pl.DataFrame:
    """The bookings of the customer orders, without those of ignored events (`events`)."""
    bookings = table(legacy_dir, "NRBOOK").filter(pl.col("BK_BKTYP").is_in(ORDERS))
    return bookings.join(ignored(legacy_dir), left_on=["BK_POLNR", "BK_EVTNR"], right_on=["EV_POLNR", "EV_EVTNR"],
                         how="anti")


def booked_before(bookings: pl.DataFrame, rows: pl.DataFrame, day: str, exact: bool = False) -> pl.DataFrame:
    """`rows` (a fund and pot of a policy, POT, and the date column `day`) with BOOKED, the units of `bookings`
    traded before `day` (or on it too, when `exact`)."""
    daily = bookings.group_by(*POT, "BK_TRDDT").agg(pl.col("BK_UNITS").sum()).sort("BK_TRDDT")
    running = daily.with_columns(BOOKED=pl.col("BK_UNITS").cum_sum().over(POT)).drop("BK_UNITS")
    found = rows.sort(day).join_asof(running, left_on=day, right_on="BK_TRDDT", by=POT, strategy="backward",
                                     allow_exact_matches=exact)
    return found.drop("BK_TRDDT").with_columns(pl.col("BOOKED").fill_null(0))


def run_candidates(external: pl.DataFrame, dates: pl.DataFrame) -> pl.DataFrame:
    """BK_POLNR, RUN, BK_FNDID, BK_POTCD and BOOKED of every run and every fund and pot with a booking of
    `external` traded before it."""
    pots = external.group_by(POT).agg(FIRST=pl.col("BK_TRDDT").min())
    rows = dates.join(pots, on="BK_POLNR").filter(pl.col("FIRST").lt(pl.col("RUN"))).drop("FIRST")
    return booked_before(external, rows, "RUN")


def charged(rows: pl.DataFrame, **conventions) -> pl.DataFrame:
    """The charge bookings of every run of `rows` (`run_rows` with BOOKED), each run on the units that the bookings
    before it and the earlier runs left (the other `conventions` of `charges.charges_of`)."""
    turns = rows.with_columns(TURN=pl.col("RUN").rank("dense").over("BK_POLNR")).partition_by("TURN", as_dict=True)
    left = pl.DataFrame(schema={"BK_POLNR": pl.String, "BK_FNDID": pl.String, "BK_POTCD": pl.String,
                                "CHARGED": pl.Int64})
    made = []
    for turn in sorted(turns):
        held = turns[turn].join(left, on=POT, how="left").with_columns(
            UNITS=pl.col("BOOKED").add(pl.col("CHARGED").fill_null(0))).filter(pl.col("UNITS").gt(0))
        bookings = charges_of(held.drop("CHARGED", "TURN"), **conventions)
        made.append(bookings)
        taken = bookings.group_by(POT).agg(CHARGED=pl.col("BK_UNITS").sum())
        left = pl.concat([left, taken]).group_by(POT).agg(pl.col("CHARGED").sum())
    return pl.concat(made)


def accounting(legacy_dir, until, parameter_day: str = "RUN", rounding=("down", "half_up"),
               risk_age=("nearest_days365", "nearest"), age_basis: str = "policy", age_era_day: str = "PH_APPDT",
               **conventions) -> pl.DataFrame:
    """The bookings (COLUMNS) of every policy up to the date `until`: premiums, customer orders and the charges of
    the runs."""
    premiums = premium_bookings(legacy_dir).select(COLUMNS)
    external = pl.concat([premiums, orders(legacy_dir).select(COLUMNS)])
    candidates = run_candidates(external, charge_dates(legacy_dir, premiums, until))
    rows = run_rows(legacy_dir, candidates, parameter_day, rounding, risk_age, age_basis, age_era_day)
    runs = charged(rows, **conventions).with_columns(BK_EVTNR=pl.lit(None, pl.Int64))  # the runs are no events here
    return pl.concat([external, runs.select(COLUMNS)])


def holdings(bookings: pl.DataFrame, valuation_dates, exact: bool = True) -> pl.DataFrame:
    """BK_POLNR, BK_FNDID, BK_POTCD, VALUATION and BOOKED, the units of every fund and pot with a booking up to
    each valuation date (traded on it too, when `exact`)."""
    pots = bookings.group_by(POT).agg(FIRST=pl.col("BK_TRDDT").min())
    dates = pl.DataFrame({"VALUATION": valuation_dates}, schema={"VALUATION": pl.Date})
    rows = pots.join(dates, how="cross").filter(pl.col("FIRST").le(pl.col("VALUATION"))).drop("FIRST")
    return booked_before(bookings, rows, "VALUATION", exact)
