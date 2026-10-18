"""The gap ledger of t7: for every payout, the missing inputs and the untested assumptions its row rests on.

The flags are those of the hand-in (`gaps.FLAGS`, the same that a probe of `conventions.PAYOUT_SCOPE` reads):
gaps, where an input is missing and a fallback stands in, and assumptions, rules that no target row has tested
yet. A payout without any flag is decided by rules that the targets verified. This tool prints the number of rows
per flag and writes the ledger (policy_id, event_nr, country, flags; no tax value) to `--out`. With `--targets`, a
target file of t7_tax_payout, it scores the rows of each flag with the official scoring: errors that gather under one
flag point at the rule or the gap behind them.

    NEURON_DATA=<participants> PYTHONPATH="$PWD:$PWD/tools:$PWD/.." python -B -m t7lab.t7_gaps [--targets FILE]

Run it from `my_solution`, like the other tools of the lab. `t7_check` prints the same counts before an upload.
"""
import argparse
import pathlib

import polars as pl

import submission
from gaps import FLAGS, flagged_payouts
from neuron.load import CACHE, LEGACY


def ledger(legacy_dir: str) -> pl.DataFrame:
    """policy_id, event_nr, country, one boolean column per flag of `gaps.FLAGS` and `flags`: the names that apply."""
    return flagged_payouts(legacy_dir).select(policy_id="TB_POLNR", event_nr="TB_EVTNR",
                                              country=pl.col("COUNTRY").fill_null(""), *FLAGS, flags="FLAGS_SET")


def counts(gaps: pl.DataFrame) -> dict[str, int]:
    """{flag: payouts with it}, and "none": the payouts without any flag."""
    found = {name: int(gaps[name].sum()) for name in FLAGS}
    return {**found, "none": gaps.filter(pl.col("flags").eq("")).height}


def scored_by_flag(gaps: pl.DataFrame, targets_file: pathlib.Path) -> pl.DataFrame:
    """flag, rows and correct: the target rows of each flag (and of "none") that the submission gets exact."""
    import scoring_t7
    targets = scoring_t7.TASKS["t7_tax_payout"].read(targets_file)
    predictions = scoring_t7.normalize("t7_tax_payout", submission.t7_tax_payout(str(LEGACY)))
    hits = pl.DataFrame([{"policy_id": key[0], "event_nr": key[1], "correct": predictions.get(key) == value,
                          "missing": key not in predictions} for key, value in targets.items()])
    joined = hits.join(gaps, on=["policy_id", "event_nr"], how="left").with_columns(pl.col("flags").fill_null("?"))
    groups = [(name, joined.filter(pl.col(name).fill_null(False))) for name in FLAGS]
    groups += [("none", joined.filter(pl.col("flags").eq(""))), ("not in our payouts", joined.filter("missing"))]
    return pl.DataFrame([{"flag": name, "rows": group.height, "correct": int(group["correct"].sum())}
                         for name, group in groups if group.height])


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=pathlib.Path, default=CACHE / "t7_gaps.csv", help="where to write the ledger")
    parser.add_argument("--targets", type=pathlib.Path, help="a t7_tax_payout target file to score by flag")
    args = parser.parse_args()
    gaps = ledger(str(LEGACY))
    print(f"{gaps.height} payouts")
    for name, count in counts(gaps).items():
        kind, meaning = FLAGS.get(name, ("", "decided by verified rules only"))
        print(f"  {name:22s} {kind:10s} {count:6d}  {meaning}")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    gaps.write_csv(args.out)
    print(f"ledger written to {args.out}")
    if args.targets:
        with pl.Config(tbl_rows=40):
            print(scored_by_flag(gaps, args.targets))


if __name__ == "__main__":
    main()
