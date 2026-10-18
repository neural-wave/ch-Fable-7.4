"""The premiums of the whole extract received by a day, as the annual KST reads them from NRPREM."""
import functools
from decimal import Decimal

from .amounts import ZERO
from .days import stored_day
from .raw import raw_table


@functools.cache
def premiums_received_by(legacy_dir, end):
    """The sum of the raw PR_AMTRC of the paid NRPREM items received by `end`.

    The sum runs over all the policies of the extract, not over one policy.
    """
    return sum((Decimal(row["PR_AMTRC"]) for row in raw_table(legacy_dir, "PREM")
                if row["PR_STATE"] == "P" and received_by(row["PR_RCVDT"], end)), ZERO)


def received_by(stored, end):
    """True when the stored day the money was received is on or before `end`."""
    day_ = stored_day(stored)
    return day_ is not None and day_ <= end
