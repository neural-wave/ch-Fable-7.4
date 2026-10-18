"""The tax bookings of NRTAXB against what may decide them, to find the rules of t7: counts only.

NRTAXB has no amounts, but every booking is a label: Neuron booked that tax on that payout. These counts show which
rule explains the labels. They come from the tax tables, so run this with an open-weights model only.

    NEURON_DATA=<participants> PYTHONPATH="$PWD:$PWD/tools:$PWD/.." python -B -m t7lab.t7_labels

- payouts by country and by tax withheld: which rows each open choice of `conventions` touches;
- CH: VST booked by reporting status AD_TAXST (M reported, E objection) and by gross above the threshold TX_THRSH;
- DE: KST booked by old contract held 12 years, by single premium, by base above 0 and by event type (500 is a
  death claim);
- IT: SOS booked by base above 0;
- BOC booked by the country of the payout, KIS booked by church membership AD_CHURCH;
- the bookings by tax type and job user TB_USRID (online users grouped): a job of its own may mark a remittance
  run.
"""
import polars as pl

from conventions import HELD_YEARS, OLD_CONTRACT, SINGLE_PREMIUM
from legacy import as_date, table
from neuron.load import LEGACY
from payouts import EVENT, payouts


def booked(rows: pl.DataFrame, tax_types: list[str], name: str) -> pl.DataFrame:
    """`rows` (payouts) with the column `name`: true where NRTAXB has a booking of one of `tax_types` for it."""
    bookings = table(LEGACY, "NRTAXB").filter(pl.col("TB_TAXTP").is_in(tax_types)).select(*EVENT).unique()
    return rows.join(bookings.with_columns(pl.lit(True).alias(name)), on=EVENT, how="left").with_columns(
        pl.col(name).fill_null(False))


def thresholds(rows: pl.DataFrame) -> pl.DataFrame:
    """`rows` with THRESHOLD: the highest TX_THRSH of a VST rate valid on the payout day (CHF cents)."""
    rates = table(LEGACY, "NRTAXR").filter(pl.col("TX_TAXTP").eq("VST")).select("TX_VLDFR", "TX_VLDTO", "TX_THRSH")
    valid = rows.select(*EVENT, "TB_EFFDT").join(rates, how="cross").filter(
        pl.col("TB_EFFDT").is_between(pl.col("TX_VLDFR"), pl.col("TX_VLDTO")))
    return rows.join(valid.group_by(EVENT).agg(THRESHOLD=pl.col("TX_THRSH").max()), on=EVENT, how="left")


def labelled_payouts() -> pl.DataFrame:
    """Every payout of t7 with its event type, the labels of NRTAXB and the features that may decide them."""
    types = table(LEGACY, "NREVNT").select(TB_POLNR="EV_POLNR", TB_EVTNR="EV_EVTNR", EV_EVTTP="EV_EVTTP")
    rows = payouts(str(LEGACY)).join(types, on=EVENT, how="left")
    for name, tax_types in {"WITHHELD": ["VST", "SOS", "KST"], "VST": ["VST"], "KST": ["KST"], "SOS": ["SOS"],
                            "BOC": ["BOC"], "KIS": ["KIS"]}.items():
        rows = booked(rows, tax_types, name)
    start, day = as_date("PH_BEGDT"), as_date("TB_EFFDT")
    old_and_held = start.lt(OLD_CONTRACT).and_(day.ge(start.dt.offset_by(f"{HELD_YEARS}y")))
    single = pl.col("PH_FREQ").eq(SINGLE_PREMIUM)
    return thresholds(rows).with_columns(OLD_AND_HELD=old_and_held, SINGLE=single,
                                         BASE_ABOVE_0=pl.col("TAXABLE_BASE").gt(0),
                                         ABOVE_THRESHOLD=pl.col("TAXABLE_BASE").gt(pl.col("THRESHOLD").fill_null(0)))


def show(title: str, rows: pl.DataFrame, *by: str, counted: str = "payouts"):
    """Print the number of rows of `rows` (`counted`) per combination of the columns `by`."""
    print(f"\n{title}")
    print(rows.group_by(*by).agg(pl.len().alias(counted)).sort(*by))


def job_users() -> pl.DataFrame:
    """The bookings of NRTAXB with JOB: their TB_USRID, or "online" for the users U<number> of the online system."""
    online = pl.col("TB_USRID").str.contains(r"^U\d+$")
    return table(LEGACY, "NRTAXB").with_columns(JOB=pl.when(online).then(pl.lit("online")).otherwise("TB_USRID"))


def main():
    rows = labelled_payouts()
    with pl.Config(tbl_rows=-1, tbl_hide_dataframe_shape=True, tbl_hide_column_data_types=True):
        show("Payouts by country and tax withheld (VST, SOS, KST)", rows, "COUNTRY", "WITHHELD")
        show("CH: VST booked by reporting status and gross above the VST threshold",
             rows.filter(pl.col("COUNTRY").eq("CH")), "AD_TAXST", "ABOVE_THRESHOLD", "VST")
        show("DE: KST booked by old contract held 12 years, single premium, base above 0 and event type",
             rows.filter(pl.col("COUNTRY").eq("DE")), "OLD_AND_HELD", "SINGLE", "BASE_ABOVE_0", "EV_EVTTP", "KST")
        show("IT: SOS booked by base above 0", rows.filter(pl.col("COUNTRY").eq("IT")), "BASE_ABOVE_0", "SOS")
        show("BOC booked by country", rows, "COUNTRY", "BOC")
        show("DE: KIS booked by church membership", rows.filter(pl.col("COUNTRY").eq("DE")), "AD_CHURCH", "KIS")
        show("Bookings by tax type and job user", job_users(), "TB_TAXTP", "JOB", counted="bookings")


if __name__ == "__main__":
    main()
