"""Neuron migration challenge: the rules of Neuron as code, calculated from the export in `legacy_dir`.

Each function gets the folder `legacy_dir` with the NR*.csv files and returns the calculated values. Dates are
`datetime.date`, amounts are `decimal.Decimal`. The rules found for each task are in the docstrings and README.md.

Check the solution locally against the train targets with `python check.py`.
"""
import datetime as dt
from decimal import Decimal

import polars as pl

from conventions import CONVERSION, DIRECT_DEBIT, IN_FORCE, MONTHS, REVERSAL, SINGLE_PREMIUM
from dates import business_day, every_months
from legacy import as_date, table, valid_on, versions_on
from money import francs, share
from projection import projected_years
from valuation import surrender_values


def received_premiums(legacy_dir) -> pl.DataFrame:
    """Premium items whose money was received and whose receipt was not reversed.

    The money date PR_RCVDT is 0 while nothing was received. A later event 900 can reverse the receipt event
    PR_EVTNR: then the money counts as not received.
    """
    events = table(legacy_dir, "NREVNT")
    reversals = events.filter(pl.col("EV_EVTTP").eq(REVERSAL)).select("EV_POLNR", "EV_REVNR")
    items = table(legacy_dir, "NRPREM").filter(pl.col("PR_RCVDT").gt(0))
    return items.join(reversals, left_on=["PR_POLNR", "PR_EVTNR"], right_on=["EV_POLNR", "EV_REVNR"], how="anti")


def premium_type() -> pl.Expr:
    """Premium type PAYTP of the commission rates NRCOMR, from the payment frequency of the policy.

    E for single premium policies (frequency E), L for regular premiums.
    """
    single = pl.col("PH_FREQ").eq(SINGLE_PREMIUM)
    return pl.when(single).then(pl.lit("E")).otherwise(pl.lit("L")).alias("PAYTP")


def commission_rates(legacy_dir, items: pl.DataFrame) -> pl.DataFrame:
    """`items` with the commission rate CR_RATE that is valid on their money date PR_RCVDT.

    The rate depends on the tier of the broker of the policy version valid on that date and on the premium
    type. NRCOMR has no version numbers, so the newest start date wins there.
    """
    policies = valid_on(items, table(legacy_dir, "NRPOLH"), {"PR_POLNR": "PH_POLNR"}, "PR_RCVDT", "PH")
    brokers = policies.join(table(legacy_dir, "NRBROK"), left_on="PH_BRKNR", right_on="BR_BRKNR")
    return valid_on(brokers.with_columns(premium_type()), table(legacy_dir, "NRCOMR"),
                    {"BR_TIER": "CR_TIER", "PAYTP": "CR_PAYTP"}, "PR_RCVDT", "CR", newest="VLDFR")


def t0_commission(legacy_dir) -> dict[tuple[str, int], Decimal]:
    """{(policy_id, due_nr): commission} of every premium item received and not reversed.

    Commission = received amount PR_AMTRC x rate, rounded half up to the cent. The rate comes from NRCOMR by
    - the tier of the broker of the policy version valid on the money date PR_RCVDT (a broker change counts from
      its validity date, also when it was entered later), and
    - the premium type: E for single premium policies (frequency E), L for regular premiums.
    """
    rated = commission_rates(legacy_dir, received_premiums(legacy_dir))
    commissions = rated.select("PR_POLNR", "PR_DUENR", francs(share(pl.col("PR_AMTRC"), pl.col("CR_RATE"))))
    return {(policy, due_nr): commission for policy, due_nr, commission in commissions.iter_rows()}


def paying_policies(legacy_dir, day: dt.date) -> pl.DataFrame:
    """The policies that pay regular premiums on `day`: state 10 and not single premium, in the version valid then.

    A policy without a version valid on that day (e.g. one that ended earlier) is left out.
    """
    policies = versions_on(table(legacy_dir, "NRPOLH"), day, "PH_POLNR", "PH")
    return policies.filter(pl.col("PH_STATE").eq(IN_FORCE), pl.col("PH_FREQ").ne(SINGLE_PREMIUM))


def schedule_anchors(legacy_dir) -> pl.DataFrame:
    """PR_POLNR and ANCHOR: the first due date of every policy from the conversion to Neuron NG on.

    COBOL computed every due date from the previous one, so a day 29 to 31 sank in a short month and stayed there
    (31 -> 28 -> 28). Neuron NG took over the schedule at the conversion: it adds whole periods to its first due
    date, which the past due dates PR_DUEDT show.
    """
    dues = table(legacy_dir, "NRPREM").select("PR_POLNR", ANCHOR=as_date("PR_DUEDT"))
    return dues.filter(pl.col("ANCHOR").ge(CONVERSION)).group_by("PR_POLNR").agg(pl.col("ANCHOR").min())


def due_dates(policies: pl.DataFrame) -> pl.DataFrame:
    """One row per policy and due date: from the anchor every period of the frequency, before the maturity date.

    `policies` needs the columns ANCHOR and END (the maturity date); there is no due date on or after maturity.
    """
    schedules = [policies.filter(pl.col("PH_FREQ").eq(frequency)).with_columns(
        DUE=every_months("ANCHOR", "END", months)) for frequency, months in MONTHS.items()]
    return pl.concat(schedules).explode("DUE")


def collection_date(due: pl.Expr) -> pl.Expr:
    """The day the money is taken: by direct debit (LS) the due date or the next business day, else the due date."""
    return pl.when(pl.col("PH_PAYMT").is_in(DIRECT_DEBIT)).then(business_day(due)).otherwise(due)


def t1_next_due_dates(legacy_dir, extract_date: dt.date) -> dict[tuple[str, int], tuple[dt.date, dt.date]]:
    """{(policy_id, n): (due_date, collection_date)} for the due dates after `extract_date`, n = 1, 2, ...

    For every policy that pays regular premiums on `extract_date`, the due dates of the following year (after
    `extract_date`, up to and including the same day a year later). The schedule continues from the first due
    date of Neuron NG in whole periods (`schedule_anchors`). Direct debits are collected on a business day of
    canton Ticino, bank transfers on the due date.
    """
    policies = paying_policies(legacy_dir, extract_date).join(schedule_anchors(legacy_dir), left_on="PH_POLNR",
                                                              right_on="PR_POLNR")
    dues = due_dates(policies.with_columns(END=as_date("PH_ENDDT")))
    year = dues.filter(pl.col("DUE").gt(extract_date), pl.col("DUE").le(pl.lit(extract_date).dt.offset_by("1y")))
    rows = year.select("PH_POLNR", N=pl.col("DUE").rank("ordinal").over("PH_POLNR"), DUE="DUE",
                       COLLECTION=collection_date(pl.col("DUE")))
    return {(policy, n): (due, collection) for policy, n, due, collection in rows.iter_rows()}


def t2_projected_maturity_value(legacy_dir) -> dict[str, Decimal]:
    """{policy_id: maturity_value}: the value at maturity that the offer projected for every policy.

    The offer simulates the policy as signed month by month, with the parameters valid on the application date
    and growth at the illustration rate NRILLU (`projection`). The maturity value is the value at the end of the
    last policy year.
    """
    years = projected_years(legacy_dir)
    maturity = years.group_by("PH_POLNR").agg(pl.col("VALUE").sort_by("YEAR").last())
    return dict(maturity.select("PH_POLNR", francs(pl.col("VALUE"))).iter_rows())


def t3_surrender_value(legacy_dir, valuation_dates: list[dt.date]) -> dict[tuple[str, dt.date], Decimal]:
    """{(policy_id, valuation_date): surrender_value} of every policy on every valuation date.

    The unit account rebuilds the bookings that the nightly job calculated (`valuation.unit_account`):
    - premiums: the received premium less the entry charge, split by the allocation and bought at the ask price
    - monthly charge runs: admin fee, management charge and risk charge, sold at the bid price (`charge_run`)
    The policy value adds up the positions at the bid price of the valuation date, and the surrender value is
    the policy value less the surrender penalty of the policy year (`valuation`).
    """
    values = {}
    for day in valuation_dates:
        surrender = surrender_values(legacy_dir, day).select("PH_POLNR", francs(pl.col("SURRENDER")))
        values.update({(policy, day): value for policy, value in surrender.iter_rows()})
    return values


def t4_annual_statement(legacy_dir) -> dict[tuple[str, int], tuple[Decimal, ...]]:
    """{(policy_id, year): (premiums, entry_charges, admin_fees, management_fees, risk_charges, total_charges)}"""
    return {}


def t5_outlier_detection(legacy_dir, targets_dir) -> set[tuple[str, object]]:
    """{(task, key)} of the values that were changed by hand.

    `targets_dir` holds the target files (t0 to t4) of the policies to check, in the format of `targets/`. This is
    the only function that may read target files. Example keys: ("t2_projected_maturity_value", "BL10000042"),
    ("t4_annual_statement", ("BL10000042", 2021)).
    """
    return set()
