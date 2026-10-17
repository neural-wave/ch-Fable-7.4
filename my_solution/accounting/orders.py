"""Customer orders: fund switches, partial withdrawals, surrender and death.

NRBOOK books them with their units (SWO and SWI, WDR, SUR, DTH), so the migration takes them
as they are. The bookings of events that were reversed later (a reversal, event 900, names
the event it cancels in EV_REVNR) and of technical corrections (event 990) never happened for
the customer and are left out.
"""
import conventions as c
from accounting import account
from core import lookup
from legacy import tables


def cancelled(legacy_dir):
    """{(policy_id, event_nr)} of the reversed events and of the technical corrections."""
    reversals = tables.table(legacy_dir, "NREVNT", "EV_EVTTP", (c.REVERSAL,))
    corrections = tables.table(legacy_dir, "NREVNT", "EV_EVTTP", (c.TECHNICAL_CORRECTION,))
    reversed_events = {(event["EV_POLNR"], event["EV_REVNR"]) for event in reversals}
    return reversed_events.union((event["EV_POLNR"], event["EV_EVTNR"]) for event in corrections)


def booking(row):
    """The booking of one NRBOOK row of a customer order."""
    return account.Booking(row["BK_TRDDT"], row["BK_BKTYP"], (row["BK_FNDID"], row["BK_POTCD"]), row["BK_AMTPC"], row["BK_UNITS"])


def customer_orders(legacy_dir):
    """{policy_id: [Booking]} of the orders that stand."""
    events = lookup.group(tables.table(legacy_dir, "NRBOOK", "BK_BKTYP", c.ORDERS), "BK_POLNR", "BK_EVTNR")
    standing = set(events).difference(cancelled(legacy_dir))
    orders = {}
    for policy_id, event in sorted(standing):
        orders.setdefault(policy_id, []).extend(map(booking, events[policy_id, event]))
    return orders
