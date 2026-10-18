"""The taxes on one payout event, by the country the holder lives in on the event day.

A booked rate is the rate valid on the day of the last booking of its tax type in the event; an event rate
is the rate valid on the event day, for a tax type the event books.
"""
from neuron import cents

from .amounts import ZERO, above_allowance, fund_growth, levy, taxable_gain
from .fund_value import fund_value
from .rates import rate_of, threshold_of


class PayoutEvent:
    """The NRTAXB bookings of one payout event."""

    def __init__(self, legacy_dir, policy_id, day_, bookings, rates):
        self.legacy_dir, self.policy_id, self.day = legacy_dir, policy_id, day_
        self.bookings, self.rates = bookings, rates
        self.tax_types = {booking["TB_TAXTP"] for booking in bookings}

    def taxes(self, country, payout):
        """(taxable_base, withholding, surcharges, stamp_duty), each rounded half up to the cent.

        The taxable base is the payout in CH and the `taxable_gain` in the payout in every other country.
        """
        base = payout if country == "CH" else taxable_gain(payout, *self.fund_value())
        country_taxes = COUNTRY_TAXES.get(country, PayoutEvent.untaxed)
        return tuple(map(cents, (base, *country_taxes(self, base, payout))))

    def fund_value(self):
        """(fund value, paid premiums / 100) of the policy on the event day."""
        return fund_value(self.legacy_dir, self.policy_id, self.day)

    def booked_rate(self, tax_type):
        """The booked rate of `tax_type`, or None."""
        return self.rates.booked_rate(self.bookings, tax_type)

    def event_rate(self, tax_type):
        """The event rate of `tax_type`, or None when the event books no `tax_type`."""
        return self.rates.rate(tax_type, self.day) if tax_type in self.tax_types else None

    def german(self, base, _payout):
        """(withholding, surcharges, 0).

        Withholding: KST on the base, replaced by the KIS event rate on the fund growth. Surcharges: SOL on the
        KST withholding.
        """
        withholding = levy(self.booked_rate("KST"), base)
        surcharges = levy(self.booked_rate("SOL"), withholding)
        withholding = levy(self.event_rate("KIS"), fund_growth(self.fund_value()), withholding)
        return withholding, surcharges, ZERO

    def swiss(self, _base, payout):
        """(withholding, 0, stamp_duty).

        Withholding: VST on the payout above the allowance of the VST row. Stamp duty: STP on the payout.
        """
        vst = self.rates.booked_row(self.bookings, "VST")
        withholding = levy(rate_of(vst), above_allowance(payout, threshold_of(vst)))
        return withholding, ZERO, levy(self.booked_rate("STP"), payout)

    def italian(self, base, _payout):
        """(withholding, surcharges, 0): SOS on the base, the BOL event rate on the fund value."""
        surcharges = levy(self.event_rate("BOL"), self.fund_value()[0])
        return levy(self.booked_rate("SOS"), base), surcharges, ZERO

    def luxembourgish(self, base, _payout):
        """(withholding, 0, 0): KIS on the base."""
        return levy(self.booked_rate("KIS"), base), ZERO, ZERO

    def untaxed(self, _base, _payout):
        """(0, 0, 0): a country without payout taxes."""
        return ZERO, ZERO, ZERO


COUNTRY_TAXES = {"DE": PayoutEvent.german, "CH": PayoutEvent.swiss, "IT": PayoutEvent.italian,
                 "LU": PayoutEvent.luxembourgish}
