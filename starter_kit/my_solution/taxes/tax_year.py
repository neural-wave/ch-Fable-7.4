"""The taxes of one policy in one calendar year, by the country the holder lives in on 1 January.

A booked rate is the rate valid on the day of the last booking of its tax type in the year.
"""
import datetime as dt

from neuron import cents

from .amounts import ZERO, levy, taxable_gain
from .fund_value import fund_value
from .kis import annual_kis
from .premiums import premiums_received_by


class TaxYear:
    """The NRTAXB bookings of one policy in one calendar year."""

    def __init__(self, legacy_dir, policy_id, year, bookings, rates, residence):
        self.legacy_dir, self.policy_id, self.year_end = legacy_dir, policy_id, dt.date(year, 12, 31)
        self.bookings, self.rates, self.residence = bookings, rates, residence
        self.tax_types = {booking["TB_TAXTP"] for booking in bookings}

    def taxes(self, country):
        """(ch_stp, ch_vst, it_sos, it_bol, de_kst, de_sol, de_kis), each rounded half up to the cent.

        CH VST is not calculated (always 0); KIS also depends on the country of the booking day (see `kis`).
        """
        ch_stp = self.swiss_stamp_duty() if country == "CH" else ZERO
        it_sos, it_bol = self.italian() if country == "IT" else (ZERO, ZERO)
        de_kst, de_sol = self.german() if country == "DE" else (ZERO, ZERO)
        return ch_stp, ZERO, it_sos, it_bol, de_kst, de_sol, annual_kis(self, country)

    def fund_value(self, day_):
        """(fund value, paid premiums / 100) of the policy on `day_`."""
        return fund_value(self.legacy_dir, self.policy_id, day_)

    def booked_rate(self, tax_type):
        """The booked rate of `tax_type`, or None."""
        return self.rates.booked_rate(self.bookings, tax_type)

    def on_year_end_value(self, rate):
        """`rate` x the fund value at the year end, rounded to the cent; 0 without a rate.

        Without a rate the fund value is not calculated.
        """
        return ZERO if rate is None else cents(rate * self.fund_value(self.year_end)[0])

    def swiss_stamp_duty(self):
        """STP valid at the year end on the fund value at the year end, when the year books STP."""
        stp = self.rates.rate("STP", self.year_end) if "STP" in self.tax_types else None
        return self.on_year_end_value(stp)

    def italian(self):
        """(SOS, BOL): the booked rates on the fund value at the year end."""
        return self.on_year_end_value(self.booked_rate("SOS")), self.on_year_end_value(self.booked_rate("BOL"))

    def german(self):
        """(KST, SOL): the booked KST on the gain of the year end, the booked SOL on KST.

        The gain is the `taxable_gain` with the premiums that the whole extract received by the year end as both
        the payout and the premiums.
        """
        kst_rate = self.booked_rate("KST")
        kst = ZERO if kst_rate is None else cents(kst_rate * self.year_end_gain())
        return kst, cents(levy(self.booked_rate("SOL"), kst))

    def year_end_gain(self):
        """The gain that KST is levied on (see `german`)."""
        premiums = premiums_received_by(self.legacy_dir, self.year_end)
        return taxable_gain(premiums, self.fund_value(self.year_end)[0], premiums)
