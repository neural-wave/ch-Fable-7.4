"""t7 payouts: the taxes on each payout event that NRTAXB books, by the country the holder lives in."""
from neuron import add_months

from .amounts import ZERO
from .book import payout_amounts
from .days import stored_day
from .payout_event import PayoutEvent
from .rates import TaxRates
from .raw import grouped_bookings
from .residence import Residence


def payout_taxes(legacy_dir):
    """{(policy_id, event_nr): (country, taxable_base, withholding, surcharges, stamp_duty, remittance_date)}

    One row per event of NRTAXB whose holder has a country on the event day, the day of the first booking of
    the event. The tax is remitted on the 10th of the next month.
    """
    rates, residence, payouts = TaxRates(legacy_dir), Residence(legacy_dir), payout_amounts(legacy_dir)
    result = {}
    for (policy_id, event_nr), bookings in grouped_bookings(legacy_dir, event_key).items():
        day_ = stored_day(bookings[0]["TB_EFFDT"])
        country = None if day_ is None else residence.country(policy_id, day_)
        if country is not None:
            event = PayoutEvent(legacy_dir, policy_id, day_, bookings, rates)
            taxes = event.taxes(country, payouts.get((policy_id, event_nr), ZERO))
            result[policy_id, int(event_nr)] = (country, *taxes, add_months(day_.replace(day=10), 1))
    return result


def event_key(booking):
    """(policy_id, event_nr) of an NRTAXB booking.

    The event number stays the stored string, as in NRBOOK; the result key converts it to int.
    """
    return booking["TB_POLNR"].strip(), booking["TB_EVTNR"]
