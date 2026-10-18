"""The annual KIS: the one annual tax that also depends on where the holder lives on the day of the booking.

A KIS booking is taxed for a holder in LU on 1 January and on the booking day, at the KIS rate of that day,
and for a holder in DE on either day, at the booked SOL rate of the year (the booked KST rate when the year
books no SOL). The tax is the rate on the fund growth on the booking day; the last taxed booking counts.
"""
from neuron import cents

from .amounts import ZERO, fund_growth
from .raw import booking_days


def annual_kis(year, country):
    """KIS of a `TaxYear` for a holder in `country` on 1 January, rounded to the cent; 0 without a taxed booking."""
    amount = ZERO
    for day_ in booking_days(year.bookings, "KIS"):
        rate = kis_rate(year, country, year.residence.country(year.policy_id, day_), day_)
        amount = amount if rate is None else cents(rate * fund_growth(year.fund_value(day_)))
    return amount


def kis_rate(year, country, resident_in, day_):
    """The rate of a KIS booking of a `TaxYear` on `day_`, or None when the booking is not taxed."""
    if country == resident_in == "LU":
        return year.rates.rate("KIS", day_)
    if "DE" not in (country, resident_in):
        return None
    return year.booked_rate("SOL" if "SOL" in year.tax_types else "KST")
