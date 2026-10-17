"""The unit bookings of the policies (NRBOOK) that do not depend on the charges: premiums and moved units.

NRBOOK has a row for every booking with its fund BK_FNDID, pot BK_POTCD and dates. Switches, withdrawals,
surrenders and death claims carry their units BK_UNITS; the premiums (PRM) and the charges (ADM, AMC, RSK) are
empty, as the nightly job that calculated them is not in the extract. A booking counts unless its event was
reversed (event 900) or is a manual correction (`conventions.MANUAL_CORRECTION`).

A premium (event 110) buys units in every fund of the allocation:

- amount = received premium PR_AMTRC x (1 - entry charge rate) x share AL_PCTG of the fund, rounded once
- the entry charge rate: an individual agreement (NRAGRE) or the rate of the broker tier (NRENTC); the
  allocation and the rates are those valid on the money date BK_RCVDT, the broker that of the policy version
- units = amount at the ask price of the trade date BK_TRDDT, with the exchange rates of the day before
- entry charge = the fund's share of the premium less the amount invested in it

Neuron NG rounds half up and COBOL truncated, by the trade date of the booking (column HALF_UP).
"""
import math

import polars as pl

from conventions import AGREED_ENTRY, CALCULATED, CONVERSION, MANUAL_CORRECTION, PREMIUM_RECEIPT, REVERSAL
from legacy import as_date, table, valid_on
from market import with_exchange_rates, with_prices
from money import RATE_UNIT, rounded, share, units_for

POSITION = ["BK_POLNR", "BK_FNDID", "BK_POTCD"]  # a position: the units of a policy in one fund and pot
SHARE_OF_SHARE = math.prod([RATE_UNIT, RATE_UNIT])  # two rates in millionths multiplied


def received_premiums(legacy_dir) -> pl.DataFrame:
    """Premium items whose money was received and whose receipt was not reversed.

    The money date PR_RCVDT is 0 while nothing was received. A later event 900 can reverse the receipt event
    PR_EVTNR: then the money counts as not received.
    """
    events = table(legacy_dir, "NREVNT")
    reversals = events.filter(pl.col("EV_EVTTP").eq(REVERSAL)).select("EV_POLNR", "EV_REVNR")
    items = table(legacy_dir, "NRPREM").filter(pl.col("PR_RCVDT").gt(0))
    return items.join(reversals, left_on=["PR_POLNR", "PR_EVTNR"], right_on=["EV_POLNR", "EV_REVNR"], how="anti")


def counted_events(legacy_dir) -> pl.DataFrame:
    """The events of NREVNT whose bookings count: not reversed by an event 900 and no manual correction."""
    events = table(legacy_dir, "NREVNT")
    reversed_events = events.filter(pl.col("EV_EVTTP").eq(REVERSAL)).select("EV_POLNR", EV_EVTNR="EV_REVNR")
    corrections = pl.col("EV_EVTTP").eq(MANUAL_CORRECTION)
    return events.filter(corrections.not_()).join(reversed_events, on=["EV_POLNR", "EV_EVTNR"], how="anti")


def counted_bookings(legacy_dir) -> pl.DataFrame:
    """The bookings of NRBOOK that count, with the type EV_EVTTP of their event and HALF_UP (`conventions`)."""
    events = counted_events(legacy_dir).select("EV_POLNR", "EV_EVTNR", "EV_EVTTP")
    bookings = table(legacy_dir, "NRBOOK").join(events, left_on=["BK_POLNR", "BK_EVTNR"],
                                                right_on=["EV_POLNR", "EV_EVTNR"])
    return bookings.with_columns(HALF_UP=as_date("BK_TRDDT").ge(CONVERSION))


def agreed_rate(legacy_dir, rows: pl.DataFrame, fee: str, date: str) -> pl.DataFrame:
    """`rows` with AG_RATE: the individual rate for `fee` of the policy BK_POLNR valid on `date`, else null."""
    agreements = table(legacy_dir, "NRAGRE").filter(pl.col("AG_FEETP").eq(fee))
    numbered = rows.with_row_index("ROW")
    agreed = valid_on(numbered, agreements, {"BK_POLNR": "AG_POLNR"}, date, "AG", newest="VLDFR")
    return numbered.join(agreed.select("ROW", "AG_RATE"), on="ROW", how="left").drop("ROW")


def entry_charge_rates(legacy_dir, rows: pl.DataFrame) -> pl.DataFrame:
    """`rows` with EC_RATE: the entry charge rate of the policy on the money date BK_RCVDT.

    An individual agreement wins; else the rate of the tier of the broker of the policy version valid then.
    """
    versions = valid_on(rows, table(legacy_dir, "NRPOLH"), {"BK_POLNR": "PH_POLNR"}, "BK_RCVDT", "PH")
    brokers = versions.join(table(legacy_dir, "NRBROK"), left_on="PH_BRKNR", right_on="BR_BRKNR")
    tiers = valid_on(brokers, table(legacy_dir, "NRENTC"), {"BR_TIER": "EC_TIER"}, "BK_RCVDT", "EC", newest="VLDFR")
    agreed = agreed_rate(legacy_dir, tiers, AGREED_ENTRY, "BK_RCVDT")
    return agreed.with_columns(EC_RATE=pl.coalesce("AG_RATE", "EC_RATE")).drop("AG_RATE")


def invested_amount() -> pl.Expr:
    """The amount of a premium invested in the fund: PR_AMTRC x (1 - EC_RATE) x AL_PCTG, rounded once."""
    net = pl.col("PR_AMTRC").cast(pl.Int128).mul(pl.lit(RATE_UNIT).sub(pl.col("EC_RATE")))
    return rounded(net.mul(pl.col("AL_PCTG")), SHARE_OF_SHARE, pl.col("HALF_UP")).cast(pl.Int64)


def premium_bookings(legacy_dir, bookings: pl.DataFrame) -> pl.DataFrame:
    """The PRM bookings of `bookings` (`counted_bookings`) with BK_AMTPC, BK_UNITS and ENTRY_CHARGE.

    ENTRY_CHARGE is the part of the fund's share of the premium (AL_PCTG) that is not invested.
    """
    receipts = bookings.filter(pl.col("EV_EVTTP").eq(PREMIUM_RECEIPT)).join(
        table(legacy_dir, "NRPREM").select("PR_POLNR", "PR_EVTNR", "PR_AMTRC"),
        left_on=["BK_POLNR", "BK_EVTNR"], right_on=["PR_POLNR", "PR_EVTNR"])
    rated = entry_charge_rates(legacy_dir, receipts.drop("BK_AMTPC", "BK_UNITS"))
    allocated = valid_on(rated, table(legacy_dir, "NRALLO"), {"BK_POLNR": "AL_POLNR", "BK_FNDID": "AL_FNDID"},
                         "BK_RCVDT", "AL")
    funds = allocated.join(table(legacy_dir, "NRFUND"), left_on="BK_FNDID", right_on="FD_FNDID")
    priced = with_exchange_rates(legacy_dir, with_prices(legacy_dir, funds, "BK_TRDDT"), "BK_TRDDT", same_day=False)
    invested = priced.with_columns(BK_AMTPC=invested_amount())
    return invested.with_columns(BK_UNITS=units_for(pl.col("BK_AMTPC"), pl.col("FP_ASKPR"), pl.col("HALF_UP")),
                                 ENTRY_CHARGE=share(pl.col("PR_AMTRC"), pl.col("AL_PCTG")).sub(pl.col("BK_AMTPC")))


def moved_bookings(bookings: pl.DataFrame) -> pl.DataFrame:
    """The bookings of `bookings` that carry their units: all but the types calculated by the nightly job."""
    return bookings.filter(pl.col("BK_BKTYP").is_in(CALCULATED).not_())
