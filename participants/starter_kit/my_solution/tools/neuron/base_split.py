"""Which definition of the taxable base separates the payouts Neuron taxed from those it did not (t7).

NRTAXB has no amounts, but it says which payouts got a withholding: VST in Switzerland, SOS in Italy, KST in
Germany. A withholding is due only when its base is positive (above TX_THRSH for VST), so the right definition of
the base splits the taxed payouts from the others without error, and every wrong one misplaces the payouts where
it disagrees: those near a zero gain, partial withdrawals, policies in a foreign currency. Thousands of labels test
the definitions that the two examples of the PDF cannot tell apart.

Candidates, per country of the payout (`payouts.payouts`: the booked country, else the residence):

- IT, DE, the gain: `model` is the base of the submission (pro rata, every premium converted at the rate of its
  money date). The others count the gain in the policy currency, so the exchange rate of the payout day converts
  it whole: `pro rata` takes the share PART / WHOLE of the premiums left, `premiums first` takes them up to the
  gross. `any payout` (every payout taxed) is the baseline. In Germany a payout whose taxed share is 0
  (`payouts.german_factor`: old contracts held 12 years) counts as untaxed in every candidate.
- CH, the gross in francs on the payout day against TX_THRSH of VST, with or without the objection to reporting
  (AD_TAXST of the address Neuron knew, `conventions` and NRCODE: E).

It prints counts only, never an amount: per candidate the taxed payouts with a positive base (hit), the taxed with
none (missed), the untaxed with one (extra) and the untaxed without (rest). Like `t7_check`, it is meant to be
run on the tax tables by a person or an open-weights model (the team's rule, README).

    NEURON_DATA=<participants> PYTHONPATH="$PWD:$PWD/tools" python -B -m neuron.base_split [--by FULL]
"""
import argparse

import polars as pl

from bookings import received_premiums
from conventions import TAXES, WITHHELD
from legacy import table, valid_on
from neuron.load import LEGACY
from payouts import BASIS_UNIT, EVENT, german_factor, in_turn, payouts, premiums_used

WITHHOLDING = {TAXES[tax]: tax for tax in WITHHELD}  # country -> its withholding tax: CH VST, IT SOS, DE KST
OBJECTION = "E"  # AD_TAXST: objection to reporting (NRCODE TAXST); M: reported to the tax office
BY = ["FULL", "EVENT_TYPE", "PH_CCY", "AD_TAXST"]  # columns that `--by` can split the counts by


def premiums_first(turn: pl.DataFrame) -> pl.DataFrame:
    """The payouts of one turn with USED: the premiums the EARLIER payouts left, up to the gross PAID."""
    left_over = pl.col("RECEIVED").cast(pl.Int128).mul(BASIS_UNIT).sub(pl.col("EARLIER"))
    return turn.with_columns(USED=pl.min_horizontal(left_over, pl.col("PAID")))


def policy_currency_gain(rows: pl.DataFrame, premiums: pl.DataFrame, step, name: str) -> pl.DataFrame:
    """`rows` with the column `name`: the gross less the premiums USED by `step`, in millionths of a cent of the
    policy currency. The payouts of a policy use the premiums one after another, in processing order."""
    chains = rows.select(*EVENT, "TB_EFFDT", "TB_CHGTS", "PART", "WHOLE",
                         PAID=pl.col("GROSS").cast(pl.Int128).mul(BASIS_UNIT))
    paid = chains.select(*EVENT, "TB_EFFDT").join(premiums, on="TB_POLNR").filter(
        pl.col("PR_RCVDT").le(pl.col("TB_EFFDT")))
    received = chains.join(paid.group_by(EVENT).agg(RECEIVED=pl.col("PR_AMTRC").sum()), on=EVENT, how="left")
    turns = received.with_columns(pl.col("RECEIVED").fill_null(0)).sort("TB_CHGTS", "TB_EVTNR")
    used = in_turn(turns, "TB_POLNR", step, "USED")
    return rows.join(used.select(*EVENT, pl.col("PAID").sub(pl.col("USED")).alias(name)), on=EVENT, how="left")


def objections(legacy_dir, rows: pl.DataFrame) -> pl.DataFrame:
    """`rows` with AD_TAXST of the holder's address valid on TB_EFFDT, as Neuron knew it at TB_CHGTS."""
    keys = rows.select(*EVENT, "HD_PERNR", "TB_EFFDT", "TB_CHGTS")
    found = valid_on(keys, table(legacy_dir, "NRADDR"), {"HD_PERNR": "AD_PERNR"}, "TB_EFFDT", "AD",
                     known_at="TB_CHGTS")
    return rows.join(found.select(*EVENT, "AD_TAXST"), on=EVENT, how="left")


def labelled(legacy_dir) -> pl.DataFrame:
    """The payouts of CH, IT and DE with TAXED (a withholding of their country is booked) and the candidate gains."""
    booked = table(legacy_dir, "NRTAXB").filter(pl.col("TB_TAXTP").is_in(WITHHELD)).select(
        *EVENT, TAX="TB_TAXTP").unique()
    rows = payouts(legacy_dir).filter(pl.col("COUNTRY").is_in(list(WITHHOLDING))).with_columns(
        TAX=pl.col("COUNTRY").replace_strict(WITHHOLDING))
    taxed = rows.join(booked.with_columns(TAXED=pl.lit(True)), on=[*EVENT, "TAX"], how="left").with_columns(
        pl.col("TAXED").fill_null(False))
    premiums = received_premiums(legacy_dir).select(TB_POLNR="PR_POLNR", PR_RCVDT="PR_RCVDT", PR_AMTRC="PR_AMTRC")
    pro_rata = policy_currency_gain(taxed, premiums, premiums_used, "PRO_RATA")
    events = table(legacy_dir, "NREVNT").select(TB_POLNR="EV_POLNR", TB_EVTNR="EV_EVTNR", EVENT_TYPE="EV_EVTTP")
    gained = policy_currency_gain(pro_rata, premiums, premiums_first, "PREMIUMS_FIRST")
    return objections(legacy_dir, gained.join(events, on=EVENT, how="left"))


def gain_candidates() -> dict[str, pl.Expr]:
    """{name: positive base} of the gain in Italy and Germany; the German taxed share 0 counts as no base."""
    share = pl.when(pl.col("COUNTRY").eq("DE")).then(german_factor().gt(0)).otherwise(True)
    return {"model": pl.col("TAXABLE_BASE").gt(0),
            "pro rata, FX on the payout day": pl.col("PRO_RATA").gt(0).and_(share),
            "premiums first, FX on the payout day": pl.col("PREMIUMS_FIRST").gt(0).and_(share),
            "any payout": pl.col("GROSS").gt(0).and_(share)}


def gross_candidates(threshold: int) -> dict[str, pl.Expr]:
    """{name: positive base} of the Swiss withholding: the gross in francs against `threshold` (cents)."""
    francs, limit = pl.col("GROSS").cast(pl.Int128).mul(pl.col("RP")), pl.col("RT").cast(pl.Int128).mul(threshold)
    objected = pl.col("AD_TAXST").eq(OBJECTION).fill_null(False)
    return {"model": pl.col("TAXABLE_BASE").gt(0), "gross > threshold": francs.gt(limit),
            "gross >= threshold": francs.ge(limit), "objection": objected,
            "objection, gross > threshold": objected.and_(francs.gt(limit)),
            "objection, gross >= threshold": objected.and_(francs.ge(limit))}


def confusion(rows: pl.DataFrame, candidates: dict[str, pl.Expr], by: list[str]) -> pl.DataFrame:
    """Per candidate (and `by`): the counts of hit, missed, extra and rest, and ERRORS = missed + extra."""
    taxed, frames = pl.col("TAXED"), []
    for name, positive in candidates.items():
        flagged = rows.with_columns(POSITIVE=positive.fill_null(False), CANDIDATE=pl.lit(name))
        frames.append(flagged.group_by("COUNTRY", "CANDIDATE", *by).agg(
            hit=taxed.and_(pl.col("POSITIVE")).sum(), missed=taxed.and_(pl.col("POSITIVE").not_()).sum(),
            extra=taxed.not_().and_(pl.col("POSITIVE")).sum(),
            rest=taxed.not_().and_(pl.col("POSITIVE").not_()).sum()))
    counts = pl.concat(frames).with_columns(ERRORS=pl.col("missed").add(pl.col("extra")))
    return counts.sort("COUNTRY", *by, "ERRORS", "CANDIDATE")


def separations(legacy_dir, by: list[str]) -> pl.DataFrame:
    """The counts of `confusion` for the gain candidates in Italy and Germany and the gross candidates in CH."""
    rows = labelled(legacy_dir)
    thresholds = table(legacy_dir, "NRTAXR").filter(pl.col("TX_TAXTP").eq(WITHHOLDING["CH"]))["TX_THRSH"]
    gains = confusion(rows.filter(pl.col("COUNTRY").ne("CH")), gain_candidates(), by)
    gross = confusion(rows.filter(pl.col("COUNTRY").eq("CH")), gross_candidates(thresholds.max()), by)
    return pl.concat([gains, gross])


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--by", choices=BY, action="append", default=[], help="split the counts by this column")
    counts = separations(str(LEGACY), parser.parse_args().by)
    with pl.Config(tbl_rows=-1, tbl_cols=-1, tbl_width_chars=200, fmt_str_lengths=40,
                   tbl_formatting="ASCII_MARKDOWN"):  # ASCII: the Windows console is cp1252
        print(counts)


if __name__ == "__main__":
    main()
