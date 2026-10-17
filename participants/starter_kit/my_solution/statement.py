"""t4: the annual statement of a policy and calendar year (tools/detective/llm/012-t4-story.md).

From the task text: one row per policy and calendar year, from the start year to the year the policy ends by
surrender or death, at the latest LAST_YEAR, with six amounts: the premiums received in the year (money date),
the entry charges on the premiums invested in the year (trade date), the admin fees, the management and the risk
charges deducted in the year (the bookings of `accounting`), and their total.

The entry charge of a premium is the premium less the amounts its premium bookings invested. The choices stay
parameters of `statements`:
- `invested`: the trade date that puts an entry charge in a year: of its first ("first") or last ("last") premium
  booking, or of each premium booking with its share of the charge by the amount it invested ("share")
- `first_year`: the date whose year is the first statement: PH_BEGDT or PH_APPDT
"""
import polars as pl

from commission import received_items
from legacy import table, version_on
from money import rounded
from runs import ends

LAST_YEAR = 2025
CHARGES = {"ADM": "ADMIN", "AMC": "MANAGEMENT", "RSK": "RISK"}
AMOUNTS = ["PREMIUMS", "ENTRY", "ADMIN", "MANAGEMENT", "RISK"]


def years(legacy_dir, first_year: str) -> pl.DataFrame:
    """BK_POLNR and YEAR of every statement: from the year of `first_year` to the year the policy ends."""
    policies = version_on(table(legacy_dir, "NRPOLH").select("PH_POLNR").unique(), table(legacy_dir, "NRPOLH"),
                          {"PH_POLNR": "PH_POLNR"}, None, "PH_VRSNR")
    ended = policies.join(ends(legacy_dir), on="PH_POLNR", how="left")
    last = pl.min_horizontal(pl.col("ENDED").dt.year().fill_null(LAST_YEAR), pl.lit(LAST_YEAR))
    spans = ended.select(BK_POLNR="PH_POLNR", YEAR=pl.int_ranges(pl.col(first_year).dt.year(), last.add(1)))
    return spans.explode("YEAR").drop_nulls("YEAR").with_columns(pl.col("YEAR").cast(pl.Int32))


def entry_charges(legacy_dir, bookings: pl.DataFrame, invested: str) -> pl.DataFrame:
    """BK_POLNR, YEAR and ENTRY: the entry charges of the premiums invested in the year."""
    premium = ["BK_POLNR", "BK_EVTNR"]
    funds = bookings.filter(pl.col("BK_BKTYP").eq("PRM")).with_columns(
        INVESTED=pl.col("BK_AMTPC").sum().over(premium), FIRST=pl.col("BK_TRDDT").min().over(premium),
        LAST=pl.col("BK_TRDDT").max().over(premium), SHARE=pl.col("BK_TRDDT"))
    items = received_items(legacy_dir).select(BK_POLNR="PR_POLNR", BK_EVTNR="PR_EVTNR", AMOUNT="PR_AMTRC")
    charged = funds.join(items, on=premium).with_columns(ENTRY=pl.col("AMOUNT").sub(pl.col("INVESTED")),
                                                         YEAR=pl.col(invested.upper()).dt.year())
    parts = charged.group_by(*premium, "YEAR").agg(pl.col("ENTRY", "INVESTED").first(), PART=pl.col("BK_AMTPC").sum())
    shares = parts.with_columns(ENTRY=rounded(pl.col("ENTRY").mul(pl.col("PART")), pl.col("INVESTED"), True))
    return shares.group_by("BK_POLNR", "YEAR").agg(pl.col("ENTRY").sum())


def statements(legacy_dir, bookings: pl.DataFrame, invested: str = "share",
               first_year: str = "PH_BEGDT") -> pl.DataFrame:
    """BK_POLNR, YEAR, PREMIUMS, ENTRY, ADMIN, MANAGEMENT, RISK and TOTAL (cents) of every statement, from the
    bookings of `accounting.accounting` (with BK_EVTNR)."""
    received = received_items(legacy_dir).group_by(BK_POLNR="PR_POLNR", YEAR=pl.col("PR_RCVDT").dt.year()).agg(
        PREMIUMS=pl.col("PR_AMTRC").sum())
    charges = bookings.filter(pl.col("BK_BKTYP").is_in(list(CHARGES))).with_columns(
        YEAR=pl.col("BK_TRDDT").dt.year(), KIND=pl.col("BK_BKTYP").replace_strict(CHARGES))
    deducted = charges.pivot("KIND", index=["BK_POLNR", "YEAR"], values="BK_AMTPC", aggregate_function="sum")
    parts = [received, entry_charges(legacy_dir, bookings, invested), deducted]
    rows = years(legacy_dir, first_year)
    for part in parts:
        rows = rows.join(part.with_columns(pl.col("YEAR").cast(pl.Int32)), on=["BK_POLNR", "YEAR"], how="left")
    filled = rows.with_columns(pl.col(AMOUNTS).fill_null(0))
    return filled.select("BK_POLNR", "YEAR", *AMOUNTS, TOTAL=pl.sum_horizontal("ENTRY", "ADMIN", "MANAGEMENT", "RISK"))
