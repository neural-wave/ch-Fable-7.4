"""Ledger checks: the bookings of the submission against what Neuron wrote, for every policy of the export.

1. Skeleton, all policies (train and public). NRBOOK keeps type, fund, pot and dates of every PRM, ADM, AMC
   and RSK booking, with the amounts left blank. Per policy, the multiset (type, fund, pot, trade date, price
   date) of the ledger must equal the one of NRBOOK without the bookings of reversed events and technical
   corrections. It is the only check of the t3/t4 rules on the public policies, whose targets are hidden:
   it found the tie rule of accounting/sharing.py on BL10002262.
2. Amounts, train policies. Every booking of t3_booking, amount and units, against the ledger.

Usage (from the repository root, Python 3.14):
    python -B tools/ledger_checks.py --data /path/to/LifewareChallenge/participants [--submission my_solution]
"""
import argparse
import bisect
import collections
import pathlib
import sys
import time
from decimal import Decimal

import polars as pl

KINDS = ("PRM", "ADM", "AMC", "RSK")
TEXT = ("BK_POLNR", "BK_FNDID", "BK_POTCD", "BK_BKTYP")


def cyymmdd(column):
    """A CYYMMDD column as a date (0 is no date)."""
    n = pl.col(column).str.strip_chars().cast(pl.Int64)
    return pl.when(n == 0).then(None).otherwise(pl.date(1900 + n // 10000, n // 100 % 100, n % 100)).alias(column)


def neuron_bookings(legacy):
    """The PRM/ADM/AMC/RSK rows of NRBOOK: ids, event, position and dates."""
    return (pl.scan_csv(legacy / "NRBOOK.csv", separator=";", infer_schema_length=0)
            .select("BK_BOOKID", "BK_EVTNR", *TEXT, "BK_TRDDT", "BK_PRCDT")
            .with_columns(*(pl.col(c).str.strip_chars() for c in TEXT))
            .filter(pl.col("BK_BKTYP").is_in(KINDS))
            .with_columns(pl.col("BK_BOOKID").str.strip_chars(), pl.col("BK_EVTNR").str.strip_chars().cast(pl.Int64),
                          cyymmdd("BK_TRDDT"), cyymmdd("BK_PRCDT"))
            .collect())


def by_policy(frame, columns):
    """{policy: Counter of the rows of `columns`}."""
    return {key[0]: collections.Counter(part.select(columns).iter_rows())
            for key, part in frame.partition_by("BK_POLNR", as_dict=True).items()}


def report(name, diffs, policies):
    """Print the policies with a difference, with a few of their rows."""
    print(f"{name}: {len(policies) - len(diffs):,} / {len(policies):,} policies identical")
    for policy in sorted(diffs)[:10]:
        extra, missing = diffs[policy]
        print(f"  {policy}: {sum(extra.values())} rows only in the ledger, {sum(missing.values())} only in Neuron")
        for row in sorted(extra)[:3]:
            print("      ledger", row)
        for row in sorted(missing)[:3]:
            print("      neuron", row)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data", type=pathlib.Path, required=True, help="participants/ folder (with legacy/ and targets/)")
    parser.add_argument("--submission", type=pathlib.Path, default=pathlib.Path("my_solution"))
    args = parser.parse_args()
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(args.submission.resolve()))
    import export
    from accounting import ledger, orders

    started, legacy, targets = time.time(), args.data / "legacy", args.data / "targets"
    book = neuron_bookings(legacy)
    cancelled = pl.DataFrame(sorted(orders.cancelled(str(legacy))), schema={"BK_POLNR": pl.Utf8, "BK_EVTNR": pl.Int64}, orient="row")
    standing = book.join(cancelled, on=["BK_POLNR", "BK_EVTNR"], how="anti")
    skeleton = by_policy(standing, ["BK_BKTYP", "BK_FNDID", "BK_POTCD", "BK_TRDDT", "BK_PRCDT"])
    counted = pl.read_csv(targets / "t3_booking.csv", infer_schema_length=0).join(book, left_on="booking_id", right_on="BK_BOOKID")
    amounts = by_policy(counted.with_columns(pl.col("amount_pc").map_elements(Decimal, return_dtype=pl.Object),
                                             pl.col("units").map_elements(Decimal, return_dtype=pl.Object)),
                        ["BK_BKTYP", "BK_FNDID", "BK_POTCD", "BK_TRDDT", "amount_pc", "units"])
    print(f"NRBOOK and t3_booking read in {time.time() - started:.0f}s")

    data = export.load(str(legacy))
    price_days = {fund: days for fund, (days, _) in data.market.prices.items()}
    shape, value = {}, {}
    for contract, bookings in ledger.ledgers(data):
        mine = [b for b in bookings if b.kind in KINDS]
        days = collections.Counter((b.kind, *b.position, b.day, price_days[b.position[0]][bisect.bisect_right(price_days[b.position[0]], b.day) - 1]) for b in mine)
        theirs = skeleton.get(contract.policy_id, collections.Counter())
        if days != theirs:
            shape[contract.policy_id] = (days - theirs, theirs - days)
        if contract.policy_id in amounts:
            booked = collections.Counter((b.kind, *b.position, b.day, b.amount, b.units) for b in mine)
            if booked != amounts[contract.policy_id]:
                value[contract.policy_id] = (booked - amounts[contract.policy_id], amounts[contract.policy_id] - booked)
    report("1. skeleton against NRBOOK, all policies", shape, data.versions)
    report("2. amounts and units against t3_booking, train policies", value, amounts)
    print(f"done in {time.time() - started:.0f}s")


if __name__ == "__main__":
    main()
