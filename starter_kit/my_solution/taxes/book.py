"""The payouts of NRBOOK: the amounts paid out on each event of a policy."""
from collections import defaultdict
from decimal import Decimal

from .raw import read_rows


def payout_amounts(legacy_dir):
    """{(policy_id, event_nr): payout} of the NRBOOK bookings with an amount.

    The payout of an event is the sum of |BK_AMTPC| / 100 of its bookings. The premium and charge bookings
    have no amount, so they are left out.
    """
    payouts = defaultdict(Decimal)
    for row in read_rows(legacy_dir, "BOOK"):
        amount = (row["BK_AMTPC"] or "").strip()
        if amount:
            payouts[row["BK_POLNR"].strip(), row["BK_EVTNR"]] += abs(Decimal(amount) / Decimal(100))
    return payouts
