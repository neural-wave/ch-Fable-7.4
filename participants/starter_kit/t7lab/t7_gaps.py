"""The gap ledger of t7: for every payout, the missing inputs and the untested assumptions its row rests on.

The submission turns a missing input into a value that looks valid (a gross of 0, the first EUR rate, an empty
country), so a gap never fails, it only gives a wrong row. This tool tests the raw conditions instead of trusting
those fills, and names each one with a flag:

- gap flags: an input is missing and a fallback stands in (FLAGS, kind "gap");
- assumption flags: the row rests on a rule that no target row has tested yet (kind "assumption").

A payout without any flag is decided by rules that the targets verified. It prints the number of rows per flag
and writes the ledger (policy_id, event_nr, country, flags; no tax value) to `--out`. With `--targets`, a target
file of t7_tax_payout, it scores the rows of each flag with the official scoring: errors that gather under one
flag point at the rule or the gap behind them.

    NEURON_DATA=<participants> PYTHONPATH="$PWD:$PWD/tools:$PWD/.." python -B -m t7lab.t7_gaps [--targets FILE]

Run it from `my_solution`, like the other tools of the lab. `t7_check` prints the same counts before an upload.
"""
import argparse
import pathlib

import polars as pl

import submission
from conventions import DEATH_CLAIM, PAID_OUT, PERIOD_RATES, TAX_CURRENCY
from legacy import table, valid_on
from market import exchange_rates
from neuron.load import CACHE, EXTRACT_DATE, LEGACY
from payouts import EVENT, payouts
from periods import bounds
from tariff import signed_policies
from taxes import payout_table
from valuation import values_on

FLAGS = {  # name -> (kind, what it means and what the submission does then)
    "NO_PAYOUT_BOOKING": ("gap", "no WDR, SUR or DTH booking for the event: the gross is 0"),
    "RESIDENCE_UNKNOWN": ("gap", "no holder or address known at processing: no country"),
    "RESIDENCE_LATE": ("gap", "the residence known at processing differs from today's view: the first one counts"),
    "REGION_MISSING": ("gap", "a German holder without region: the church tax of all regions"),
    "RATE_STAND_IN": ("gap", "no rate of the tax currency on the payout day (before the euro): the first rate"),
    "PREMIUM_RATE_STAND_IN": ("gap", "a premium from before the first rate of the tax currency: the first rate"),
    "SUMIN_MISSING": ("gap", "a death claim without a sum insured: 0"),
    "VALUE_MISSING": ("gap", "no policy value at the end of a rate period of SOS: 0"),
    "UNKNOWN_COUNTRY": ("gap", "a residence outside the tax countries: no currency, base 0"),
    "AFTER_EXTRACT": ("gap", "remitted after the extract date: the date is reported all the same"),
    "UNTAXED_DEATH_BASE": ("assumption", "a DE or IT death claim without withholding reports its gain as base"),
    "DE_EXEMPT_BASE": ("assumption", "a German payout without KST but with a base reports that base"),
    "DEATH_OPTION_B_C": ("assumption", "a death claim of option B or C pays its benefit (2 sample rows so far)"),
}
RESIDENCE = ["AD_CNTRY", "AD_TAXST", "AD_REGIO", "AD_CHURCH"]


def payout_rows(legacy_dir: str) -> pl.DataFrame:
    """Every payout of the submission with its event type, its output row and the columns the flags read."""
    events = table(legacy_dir, "NREVNT").select(TB_POLNR="EV_POLNR", TB_EVTNR="EV_EVTNR", EVENT_TYPE="EV_EVTTP")
    output = payout_table(legacy_dir).select(TB_POLNR="policy_id", TB_EVTNR="event_nr", WITHHOLDING="withholding",
                                             REMITTED="remittance_date")
    policies = signed_policies(legacy_dir).select(TB_POLNR="PH_POLNR", OPTION="OPTION", RK_SUMIN="RK_SUMIN")
    return payouts(legacy_dir).join(events, on=EVENT, how="left").join(output, on=EVENT, how="left").join(
        policies, on="TB_POLNR", how="left")


def today(legacy_dir: str, rows: pl.DataFrame) -> pl.DataFrame:
    """EVENT and the RESIDENCE of today's view (TODAY_*): the versions valid on the payout day, whenever entered."""
    numbered = rows.select(*EVENT, "TB_EFFDT").with_row_index("ROW")
    holders = valid_on(numbered, table(legacy_dir, "NRHOLD"), {"TB_POLNR": "HD_POLNR"}, "TB_EFFDT", "HD")
    addresses = valid_on(holders, table(legacy_dir, "NRADDR"), {"HD_PERNR": "AD_PERNR"}, "TB_EFFDT", "AD")
    return numbered.join(addresses.select("ROW", *[pl.col(c).alias(f"TODAY_{c}") for c in RESIDENCE]), on="ROW",
                         how="left").drop("ROW", "TB_EFFDT")


def premium_stand_ins(legacy_dir: str, rows: pl.DataFrame, firsts: pl.DataFrame) -> pl.DataFrame:
    """EVENT of the payouts that count a premium received before the first rate of their tax currency."""
    premiums = table(legacy_dir, "NRPREM").filter(pl.col("PR_RCVDT").gt(0)).select(TB_POLNR="PR_POLNR",
                                                                                   PR_RCVDT="PR_RCVDT")
    counted = rows.select(*EVENT, "TB_EFFDT", "TAX_CCY").join(firsts, on="TAX_CCY").join(premiums, on="TB_POLNR")
    early = counted.filter(pl.col("PR_RCVDT").le(pl.col("TB_EFFDT")), pl.col("PR_RCVDT").lt(pl.col("FIRST_RATE")))
    return early.select(EVENT).unique()


def missing_values(legacy_dir: str, rows: pl.DataFrame) -> pl.DataFrame:
    """EVENT of the payouts with SOS whose policy has no value at the end of a rate period before the payout."""
    sos = table(legacy_dir, "NRTAXB").filter(pl.col("TB_TAXTP").is_in(PERIOD_RATES)).select(EVENT).unique()
    spans = rows.join(sos, on=EVENT).select(*EVENT, "TB_EFFDT", "PH_BEGDT").join(
        bounds(legacy_dir).select("BOUND").unique(), how="cross").filter(
        pl.col("BOUND").ge(pl.col("PH_BEGDT")), pl.col("BOUND").lt(pl.col("TB_EFFDT")))
    if spans.is_empty():
        return spans.select(EVENT)
    days = spans.select(BK_POLNR="TB_POLNR", DAY="BOUND").unique()
    values = values_on(legacy_dir, days).select(TB_POLNR="BK_POLNR", BOUND="DAY", VALUE="VALUE")
    return spans.join(values, on=["TB_POLNR", "BOUND"], how="left").filter(pl.col("VALUE").is_null()).select(
        EVENT).unique()


def ledger(legacy_dir: str) -> pl.DataFrame:
    """policy_id, event_nr, country, one boolean column per flag of FLAGS and `flags`: the names that apply."""
    rows = payout_rows(legacy_dir)
    firsts = exchange_rates(legacy_dir).group_by(TAX_CCY="FX_CCY").agg(FIRST_RATE=pl.col("FX_RATDT").min())
    paid = table(legacy_dir, "NRBOOK").filter(pl.col("BK_BKTYP").is_in(PAID_OUT)).select(
        TB_POLNR="BK_POLNR", TB_EVTNR="BK_EVTNR").unique().with_columns(BOOKED=pl.lit(True))
    marked = lambda frame, name: frame.with_columns(pl.lit(True).alias(name))
    rows = (rows.join(today(legacy_dir, rows), on=EVENT, how="left").join(firsts, on="TAX_CCY", how="left")
            .join(paid, on=EVENT, how="left")
            .join(marked(premium_stand_ins(legacy_dir, rows, firsts), "EARLY_PREMIUM"), on=EVENT, how="left")
            .join(marked(missing_values(legacy_dir, rows), "NO_VALUE"), on=EVENT, how="left"))
    death, withheld = pl.col("EVENT_TYPE").eq(DEATH_CLAIM), pl.col("WITHHOLDING").fill_null(0).ne(0)
    changed = pl.any_horizontal(*[pl.col(c).ne_missing(pl.col(f"TODAY_{c}")) for c in RESIDENCE])
    conditions = {
        "NO_PAYOUT_BOOKING": pl.col("BOOKED").is_null(),
        "RESIDENCE_UNKNOWN": pl.col("COUNTRY").is_null() | pl.col("HD_PERNR").is_null(),
        "RESIDENCE_LATE": changed,
        "REGION_MISSING": pl.col("COUNTRY").eq("DE") & pl.col("AD_REGIO").is_null(),
        "RATE_STAND_IN": pl.col("TB_EFFDT").lt(pl.col("FIRST_RATE")),
        "PREMIUM_RATE_STAND_IN": pl.col("EARLY_PREMIUM").is_not_null(),
        "SUMIN_MISSING": death & pl.col("RK_SUMIN").is_null(),
        "VALUE_MISSING": pl.col("NO_VALUE").is_not_null(),
        "UNKNOWN_COUNTRY": pl.col("COUNTRY").is_not_null() & pl.col("COUNTRY").is_in(list(TAX_CURRENCY)).not_(),
        "AFTER_EXTRACT": pl.col("REMITTED").gt(EXTRACT_DATE),
        "UNTAXED_DEATH_BASE": death & pl.col("COUNTRY").is_in(["DE", "IT"]) & withheld.not_()
        & pl.col("TAXABLE_BASE").gt(0),
        "DE_EXEMPT_BASE": death.not_() & pl.col("COUNTRY").eq("DE") & withheld.not_() & pl.col("TAXABLE_BASE").gt(0),
        "DEATH_OPTION_B_C": death & pl.col("OPTION").is_in(["B", "C"]),
    }
    flagged = rows.with_columns(**{name: condition.fill_null(False) for name, condition in conditions.items()})
    names = pl.concat_list([pl.when(pl.col(name)).then(pl.lit(name)) for name in FLAGS]).list.drop_nulls()
    return flagged.select(policy_id="TB_POLNR", event_nr="TB_EVTNR", country=pl.col("COUNTRY").fill_null(""),
                          *FLAGS, flags=names.list.join(","))


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
