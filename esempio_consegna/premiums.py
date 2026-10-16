"""Premium items: what the customer owed, when it was due and what actually arrived.

Only paid items count for commissions, statements and investments. Returned direct debits
(R), open items (O) and written-off items (W) never reach the funds.
"""
import conventions as c
import legacy


def paid_items(legacy_dir):
    """The paid premium items of NRPREM (state P), in the order of the export."""
    return [item for item in legacy.table(legacy_dir, "NRPREM") if item["PR_STATE"] == c.PAID]


def premium_types(legacy_dir):
    """{policy_id: E or L}: single or regular premiums, read from the tariff key (FXU03LB).

    The 6th character of RK_TARKEY is the premium type of the tariff.
    """
    return {risk["RK_POLNR"]: risk["RK_TARKEY"][c.PREMIUM_TYPE_POSITION]
            for risk in legacy.table(legacy_dir, "NRRISK")}
