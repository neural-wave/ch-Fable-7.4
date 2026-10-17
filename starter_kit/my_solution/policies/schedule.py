"""The due dates of the regular premiums and the days they are collected."""
from neuron import SYSTEM_CHANGE, add_months, months_between

from .bank_calendar import next_working_day
from .codes import MONTHS_PER_DUE

DIRECT_DEBIT = "LS"  # NRCODE PAYMT; bank transfers (UB) are collected on the due date


def due_dates(policy, after, until):
    """The due dates of a policy after the day `after`, up to and including `until`.

    They are counted from the anchor date, so a day missing in a month (the 31st) is lost only in that month.
    """
    months = MONTHS_PER_DUE[policy["PH_FREQ"]]
    anchor = anchor_date(policy["PH_BEGDT"], months)
    k = max(months_between(anchor, after) // months - 1, 0)  # a due number before `after`, 0 = the anchor
    while (due_date := add_months(anchor, k * months)) <= until:
        if due_date > after:
            yield due_date
        k += 1


def anchor_date(begin, months):
    """The last due date before the system change, or the begin date.

    Before the change each due date was computed from the one before, so a day missing in a month stuck for
    good; Neuron NG counts the later due dates from the last one the COBOL version computed.
    """
    anchor = begin
    while add_months(anchor, months) < SYSTEM_CHANGE:
        anchor = add_months(anchor, months)
    return anchor


def collection_date(due_date, payment_method):
    """The day the premium of a due date is collected: direct debits on the next bank working day."""
    return next_working_day(due_date) if payment_method == DIRECT_DEBIT else due_date
