"""The unit account of a policy: its bookings, and what its positions hold and are worth.

A position is one fund in one pot. Every booking moves units of one position on its trade
date: premiums buy units at the ask price, charges and customer orders take units out at the
bid price. Values are in the policy currency, rounded per position the way of the day; the
arithmetic is in conversion.py and trades.py.
"""
import collections
import typing
from decimal import Decimal

from accounting import conversion, trades
from core import money


class Booking(typing.NamedTuple):
    """One movement of units on a position.

    `amount` is in the policy currency; `gross` is the premium share before the entry
    charge, for premium bookings (PRM) only.
    """

    day: object
    kind: str
    position: tuple
    amount: Decimal
    units: Decimal
    gross: Decimal = Decimal(0)


class Account:
    """The units of each position of one policy, and their value on a day."""

    def __init__(self, market, currency, bookings=()):
        self.market, self.currency, self.units = market, currency, collections.Counter()
        self.book(bookings)

    def book(self, bookings):
        """Add the units of `bookings` to their positions."""
        trades.book(self.units, bookings)

    def worth(self, day):
        """{position: value} on `day` of every position that holds units."""
        held = {position: units for position, units in self.units.items() if units}
        return {position: conversion.worth(self.market, self.currency, position[0], units, day) for position, units in held.items()}

    def values(self, day):
        """{position: value} of the positions worth more than nothing on `day`."""
        return money.positive(self.worth(day))

    def total(self, day):
        """The policy value on `day`: all positions, also those below zero."""
        return sum(self.worth(day).values(), Decimal(0))

    def take(self, kind, split, day):
        """The bookings that take each amount of `split` {position: amount} out of its position on `day`."""
        return [Booking(day, kind, position, amount, trades.taken(self.market, self.currency, position[0], amount, day))
                for position, amount in split.items()]
