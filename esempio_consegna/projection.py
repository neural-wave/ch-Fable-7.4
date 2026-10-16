"""Projected maturity value (task t2): the illustration of the offer, month by month.

Neuron projects the offer from a value of nothing, over every month of the term; one month
of the illustration is in illustration.py, the figures of the offer in offer.py. Evidence:
all 79,040 yearly values of the train policies are exact.
"""
import ages
import conventions as c
import illustration
import offer


def maturity_value(data, contract):
    """Projected value of a policy at the end of its term."""
    terms, value = offer.offer(data, contract), c.NOTHING
    for month in range(c.MONTHS_PER_YEAR * ages.policy_years(contract.start, contract.end)):
        value = illustration.month_end(data, contract, terms, value, month)
    return value
