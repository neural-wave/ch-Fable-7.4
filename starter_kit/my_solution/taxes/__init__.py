"""The tax module of such.pdf (t7): the taxes that NRTAXB books on the payouts and per calendar year.

The tax tables are read as raw CSV rows with the dates as Neuron stores them (`raw`); the fund values come
from the unit accounting of `funds` (`fund_value`).
"""
from .annual import annual_taxes
from .payout import payout_taxes

__all__ = ["annual_taxes", "payout_taxes"]
