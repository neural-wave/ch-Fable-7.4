"""Collection of the premiums: the day the money is taken from or sent by the customer.

Direct debit (LS, Lastschrift): NeuralWave Life takes the money itself on the next Ticino
business day. Bank transfer (UB, Ueberweisung): the customer pays on the due date itself,
weekends and holidays included.
"""
import conventions as c
from billing import business_days


def collection_day(due, payment):
    """Collection day of a premium due on `due` and paid with `payment` (LS or UB)."""
    return business_days.next_business_day(due) if payment == c.DIRECT_DEBIT else due
