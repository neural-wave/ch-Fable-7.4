"""Money arithmetic of Neuron.

Amounts and units stay Decimal end to end, with 50 digits for intermediate results. Each
system rounded its own way: COBOL Neuron truncated, Neuron NG (Java, from the switch day)
rounds half up. The day of the business event decides.
"""
import decimal

import conventions as c

decimal.getcontext().prec = c.PRECISION


def cents(amount, day):
    """`amount` rounded to the cent the way Neuron rounded it on `day`."""
    return amount.quantize(c.CENT, c.ROUNDING_COBOL if day < c.ERA_SWITCH else c.ROUNDING_JAVA)


def units(quantity, day):
    """`quantity` of fund units rounded to 6 decimals the way Neuron rounded it on `day`."""
    return quantity.quantize(c.UNIT, c.ROUNDING_COBOL if day < c.ERA_SWITCH else c.ROUNDING_JAVA)


def positive(amounts):
    """{key: amount} of the amounts above zero.

    A position worth nothing is not charged, and a charge of nothing is not booked.
    """
    return {key: amount for key, amount in amounts.items() if amount > 0}
