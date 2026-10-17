"""t0: the commission of every premium item that was received and not reversed later.

The commission is the received amount PR_AMTRC times the rate of NRCOMR for the broker tier and the premium type
(E single premium, L regular), rounded half up to the cent (story, tools/detective/llm/001-t0-story.md).

Found in the data (tools/detective/llm/002-t0-findings.md):
- the broker is the one of the policy version valid on the money date PR_RCVDT, not the last one: a broker
  change counts from its validity date (decision tree t0_commission/r1/T1, search r1-search/S2)
- the rate is the NRCOMR row valid on the money date too; no rate changed between a due date and its money date,
  so the data cannot tell the two apart, and one date for both lookups is the simpler rule (r1-search/S2)

The choices stay parameters, so the search (`detective.formulas.fill_holes`) can test them again on new data.
"""
import polars as pl

from legacy import table, version_on
from money import share

PAID = "P"  # PRSTAT: the premium item was paid
SINGLE_PREMIUM = "E"  # FREQ / PAYTP


def received_items(legacy_dir) -> pl.DataFrame:
    """The premium items that were paid."""
    return table(legacy_dir, "NRPREM").filter(pl.col("PR_STATE").eq(PAID))


def premium_type() -> pl.Expr:
    """PAYTP of the policy: E for single premium policies, L for regular premiums."""
    return pl.when(pl.col("PH_FREQ").eq(SINGLE_PREMIUM)).then(pl.lit("E")).otherwise(pl.lit("L"))


def commissions(legacy_dir, broker_day: str | None = "PR_RCVDT", rate_day: str | None = "PR_RCVDT",
                half_up: bool = True) -> pl.DataFrame:
    """policy_id, due_nr and amount (cents) of every received premium item."""
    items = received_items(legacy_dir)
    policies = version_on(items, table(legacy_dir, "NRPOLH"), {"PR_POLNR": "PH_POLNR"}, broker_day, "PH_VRSNR")
    brokers = policies.join(table(legacy_dir, "NRBROK"), left_on="PH_BRKNR", right_on="BR_BRKNR", how="left")
    typed = brokers.with_columns(PAYTP=premium_type())
    rated = version_on(typed, table(legacy_dir, "NRCOMR"), {"BR_TIER": "CR_TIER", "PAYTP": "CR_PAYTP"}, rate_day,
                       "CR_VLDFR")
    return rated.select(policy_id="PR_POLNR", due_nr="PR_DUENR",
                        amount=share(pl.col("PR_AMTRC"), pl.col("CR_RATE"), half_up))
