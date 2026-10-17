"""Every tax booking of NRTAXB joined with its policyholder (NRHOLD), the holder's address (NRADDR) and its rate
(NRTAXR).

Every booking keeps exactly one row. The dates stay the stored integers `CYYMMDD`, which compare like the dates.

- Holder: the version of NRHOLD with HD_POLNR = TB_POLNR valid on TB_EFFDT (HD_VLDFR to HD_VLDTO, both days
  included); of several valid versions the highest HD_VRSNR wins (`legacy.valid_on`).
- Address: the version of NRADDR with AD_PERNR = HD_PERNR valid on TB_EFFDT, chosen the same way.
- Rate: the rows of NRTAXR with TX_TAXTP = TB_TAXTP, narrowed only while several remain:
  1. a single rate of the type is taken as it is;
  2. else the rates valid on TB_EFFDT (TX_VLDFR to TX_VLDTO); none valid -> no rate;
  3. else the rates whose TX_CNTRY is AD_CNTRY and whose TX_REGIO, if any, is AD_REGIO; a rate of the region
     (KIS of BY and BW) wins over the rate for every region (TX_REGIO blank). If none matches, step 2's stay;
  4. else the highest TX_VRSNR (the BOL rate of 2017 to June 2019 restated in July 2019), then the latest TX_CHGTS.
  TX_RULE names the step that chose the rate: single, date, residence or version.

With `--known-at`, only the versions entered up to the booking's processing timestamp TB_CHGTS count (HD_CHGTS,
AD_CHGTS, TX_CHGTS), as Neuron knew them when it booked (`taxpayer.py`).

    NEURON_DATA=<participants> PYTHONPATH="$PWD:$PWD/tools:$PWD/.." python -B -m t7lab.tax_join --out joined.parquet
"""
import argparse
import pathlib

import polars as pl

from legacy import table, valid_on
from neuron.load import LEGACY

RULES = ["single", "date", "residence", "version"]  # TX_RULE: the step of the module docstring that chose the rate


def with_versions(rows: pl.DataFrame, versions: pl.DataFrame, on: dict[str, str], prefix: str,
                  known_at: str | None) -> pl.DataFrame:
    """`rows` (with ROW) and the columns of the version of `versions` valid on TB_EFFDT, nulls without one."""
    found = valid_on(rows.select("ROW", *on, "TB_EFFDT", "TB_CHGTS"), versions, on, "TB_EFFDT", prefix,
                     known_at=known_at)
    return rows.join(found.drop(*on, "TB_EFFDT", "TB_CHGTS"), on="ROW", how="left")


def rate_candidates(rows: pl.DataFrame, rates: pl.DataFrame, known_at: str | None) -> pl.DataFrame:
    """Every rate of NRTAXR with the type of a row, as ROW and the TX columns, with the counts of steps 1 and 2."""
    keys = rows.select("ROW", "TB_TAXTP", "TB_EFFDT", "TB_CHGTS", "AD_CNTRY", "AD_REGIO")
    candidates = keys.join(rates, left_on="TB_TAXTP", right_on="TX_TAXTP").with_columns(TX_TAXTP="TB_TAXTP")
    if known_at:
        candidates = candidates.filter(pl.col("TX_CHGTS").le(pl.col(known_at)))
    dated = pl.col("TB_EFFDT").is_between(pl.col("TX_VLDFR"), pl.col("TX_VLDTO"))
    return candidates.with_columns(MATCHES=pl.len().over("ROW"), DATED=dated, VALID=dated.sum().over("ROW"))


def residence_rank() -> pl.Expr:
    """Step 3: 2 for a rate of the holder's region, 1 for the holder's country and every region, else 0."""
    country = pl.col("TX_CNTRY").eq(pl.col("AD_CNTRY")).fill_null(False)
    region = pl.col("TX_REGIO").eq(pl.col("AD_REGIO")).fill_null(False)
    every_region = pl.col("TX_REGIO").is_null()
    return pl.when(country.and_(region)).then(2).when(country.and_(every_region)).then(1).otherwise(0)


def chosen_rates(candidates: pl.DataFrame) -> pl.DataFrame:
    """The one rate per ROW of steps 1 to 4, with TX_RULE; a row whose rates are none valid on TB_EFFDT is left out."""
    kept = candidates.filter(pl.col("MATCHES").eq(1).or_(pl.col("DATED"))).with_columns(RANK=residence_rank())
    best = pl.col("RANK").eq(pl.col("RANK").max().over("ROW")).sum().over("ROW")
    rule = (pl.when(pl.col("MATCHES").eq(1)).then(pl.lit("single")).when(pl.col("VALID").eq(1)).then(pl.lit("date"))
            .when(best.eq(1)).then(pl.lit("residence")).otherwise(pl.lit("version")))
    ranked = kept.with_columns(TX_RULE=rule).sort(["ROW", "RANK", "TX_VRSNR", "TX_CHGTS"],
                                                     descending=[False, True, True, True])
    columns = [col for col in ranked.columns if col.startswith("TX_")]
    return ranked.unique("ROW", keep="first", maintain_order=True).select("ROW", *columns)


def joined(legacy_dir, known_at: str | None = None) -> pl.DataFrame:
    """NRTAXB with the columns of its holder (HD_), address (AD_) and rate (TX_, TX_RULE), one row per booking."""
    rows = table(legacy_dir, "NRTAXB").with_row_index("ROW")
    holders = with_versions(rows, table(legacy_dir, "NRHOLD"), {"TB_POLNR": "HD_POLNR"}, "HD", known_at)
    addresses = with_versions(holders, table(legacy_dir, "NRADDR"), {"HD_PERNR": "AD_PERNR"}, "AD", known_at)
    rates = chosen_rates(rate_candidates(addresses, table(legacy_dir, "NRTAXR"), known_at))
    return addresses.join(rates, on="ROW", how="left").sort("ROW").drop("ROW")


def summary(frame: pl.DataFrame) -> pl.DataFrame:
    """Bookings per tax type and TX_RULE (null: no rate), and how many lack a holder or an address."""
    return frame.group_by("TB_TAXTP", "TX_RULE").agg(
        BOOKINGS=pl.len(), NO_HOLDER=pl.col("HD_PERNR").is_null().sum(),
        NO_ADDRESS=pl.col("AD_CNTRY").is_null().sum()).sort("TB_TAXTP", "TX_RULE")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=pathlib.Path, help="write the join to this .parquet or .csv file")
    parser.add_argument("--known-at", action="store_true", help="only the versions entered up to TB_CHGTS count")
    args = parser.parse_args()
    frame = joined(LEGACY, "TB_CHGTS" if args.known_at else None)
    with pl.Config(tbl_rows=-1, tbl_formatting="ASCII_MARKDOWN"):  # ASCII: the Windows console is cp1252
        print(summary(frame))
    if args.out:
        write = frame.write_csv if args.out.suffix.lower() == ".csv" else frame.write_parquet
        write(args.out)
        print(f"{frame.height} rows -> {args.out}")


if __name__ == "__main__":
    main()
