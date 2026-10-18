"""The tax rates of NRTAXR by tax type and day.

The country and the region of a row are not looked at: a tax type has one rate on a day.
"""
from decimal import Decimal

from neuron import grouped

from .days import is_valid_on, stored_day
from .raw import booking_days, raw_table


class TaxRates:
    """The rows of NRTAXR by tax type."""

    def __init__(self, legacy_dir):
        self.by_type = grouped(raw_table(legacy_dir, "TAXR"), "TX_TAXTP")

    def row(self, tax_type, day_):
        """The row of `tax_type` valid on `day_`, or None.

        When several rows are valid, the latest start wins, the first in the table on a tie.
        """
        rows = [row for row in self.by_type.get(tax_type, []) if is_valid_on(row, "TX", day_)]
        return max(rows, key=lambda row: stored_day(row["TX_VLDFR"]), default=None)

    def rate(self, tax_type, day_):
        """The rate (`rate_of`) of the row of `tax_type` valid on `day_`, or None."""
        return rate_of(self.row(tax_type, day_))

    def booked_row(self, bookings, tax_type):
        """The row valid on the day of the last booking of `tax_type` that has a valid row, or None."""
        rows = [self.row(tax_type, day_) for day_ in booking_days(bookings, tax_type)]
        return next(filter(None, reversed(rows)), None)

    def booked_rate(self, bookings, tax_type):
        """The rate (`rate_of`) of the `booked_row`, or None."""
        return rate_of(self.booked_row(bookings, tax_type))


def rate_of(row):
    """TX_RATE / 10 000 of a row, or None without a row.

    TX_RATE is stored as an integer: 250000 gives 25.
    """
    return None if row is None else Decimal(row["TX_RATE"].strip()) / Decimal(10000)


def threshold_of(row):
    """TX_THRSH / 100 of a row, or None without a row or a threshold.

    TX_THRSH is stored as an integer: 500000 gives 5000.
    """
    threshold = "" if row is None else row["TX_THRSH"].strip()
    return Decimal(threshold) / Decimal(100) if threshold else None
