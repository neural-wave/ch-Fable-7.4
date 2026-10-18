"""t7 annual taxes: per policy and calendar year, the taxes of the tax types that NRTAXB books in that year."""
import datetime as dt

from .days import stored_day
from .rates import TaxRates
from .raw import grouped_bookings
from .residence import Residence
from .tax_year import TaxYear


def annual_taxes(legacy_dir):
    """{(policy_id, year): (ch_stp, ch_vst, it_sos, it_bol, de_kst, de_sol, de_kis)} of the years with a tax.

    The country is where the holder lives on 1 January of the year.
    """
    rates, residence = TaxRates(legacy_dir), Residence(legacy_dir)
    result = {}
    for (policy_id, year), bookings in grouped_bookings(legacy_dir, policy_year).items():
        country = residence.country(policy_id, dt.date(year, 1, 1))
        if country is None:
            continue
        taxes = TaxYear(legacy_dir, policy_id, year, bookings, rates, residence).taxes(country)
        if any(taxes):
            result[policy_id, year] = taxes
    return result


def policy_year(booking):
    """(policy_id, year) of an NRTAXB booking: the year of its day TB_EFFDT.

    None for a booking without a day: it belongs to no year.
    """
    day_ = stored_day(booking["TB_EFFDT"])
    return None if day_ is None else (booking["TB_POLNR"].strip(), day_.year)
