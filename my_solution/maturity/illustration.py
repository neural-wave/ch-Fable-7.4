"""One month of the illustration of an offer, each step rounded the way of its application date.

    premium due   value + premium after the entry charge
    ADM           value - monthly fee of the tariff
    AMC           value - value x pot-2 AMC rate / 12
    RSK           value - risk charge on the value after AMC, at the age of the month
    growth        value x (1 + illustration rate / 12)
"""
import conventions as c
from accounting import fees
from core import money
from insurance import risk
from maturity import instalments


def month_end(data, contract, terms, value, month):
    """The value at the end of `month` of the term, from the value before it."""
    value += terms.premium if instalments.due(terms.frequency, month) else 0
    value -= terms.tariff["CG_ADMFEE"]
    value -= fees.amc(value, terms.tariff["CG_AMCP2"], 1, c.MONTHS_PER_YEAR, terms.day)
    value -= risk.monthly_charge(data, contract, terms.tariff, value, terms.age + month // c.MONTHS_PER_YEAR, terms.day)
    return money.cents(value * (1 + terms.rate / c.MONTHS_PER_YEAR), terms.day)
