"""One month of the projection of an offer: premium, charges and growth (see `Projection`)."""
from neuron import cents

from .risk import risk_charge


def next_month(projection, value, month):
    """The value at the end of a month of the projection.

    The premium net of the entry charge comes in on its due months, then the admin fee, the management charge
    (pot 2 rate) and the risk charge go out, and the value grows by a twelfth of the yearly rate. The risk
    charge uses the entry age plus the completed policy years.
    """
    tariff, rounding = projection.tariff, projection.rounding
    if is_due(projection.months_per_due, month):
        value += cents(projection.offer["PH_PREMI"] * (1 - projection.entry_rate), rounding)
    value -= tariff["CG_ADMFEE"]
    value -= cents(value * tariff["CG_AMCP2"] / 12, rounding)
    value -= risk_charge(projection.insured, tariff, value, projection.entry_age + month // 12, rounding)
    return cents(value * (1 + projection.yearly_rate / 12), rounding)


def is_due(months_per_due, month):
    """True for the months with a premium: every `months_per_due` months, or only month 0 for a single premium."""
    if months_per_due is None:
        return month == 0
    return month % months_per_due == 0
