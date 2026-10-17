"""Premium instalments of an offer: in which months of the term a premium falls due.

A single premium (frequency E) is paid in the first month only; a regular premium in the
first month and then every 1, 3, 6 or 12 months (M, Q, H, J).
"""
import conventions as c


def due(frequency, month):
    """Whether a premium falls due in `month` of the term, 0 being the first month."""
    if frequency == c.SINGLE_PREMIUM:
        return month == 0
    return month % c.MONTHS_PER_PERIOD[frequency] == 0
