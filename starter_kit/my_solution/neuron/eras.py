"""The two versions of Neuron and how they round the amounts.

The COBOL batch (CBLBATCH) cut cents and units off; since the system change Neuron NG (NGBATCH) rounds half
up. For a booking its day decides the era, for an offer or an age the application date of the offer.
"""
import datetime as dt
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal

SYSTEM_CHANGE = dt.date(2007, 8, 11)  # the first run of NGBATCH
CENT = Decimal("0.01")


def cents(amount, rounding=ROUND_HALF_UP):
    """Amount rounded to the cent; Neuron NG rounds half up (0.925 -> 0.93)."""
    return Decimal(amount).quantize(CENT, rounding)


def is_cobol(day_):
    """True for a day before the system change, when the COBOL version did the calculation."""
    return day_ < SYSTEM_CHANGE


def era_rounding(day_):
    """The rounding of the era of `day_`: cut off (COBOL) or half up (Neuron NG)."""
    return ROUND_DOWN if is_cobol(day_) else ROUND_HALF_UP
