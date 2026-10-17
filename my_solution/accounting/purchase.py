"""Arithmetic of a premium purchase (PRM): pot, premium share and invested amount.

Pot 1 holds the premiums received in the first PD_INIMON months of the policy, pot 2 all
later ones. Each fund of the allocation gets its share of the premium (the gross); the
entry charge is taken from it, and the rest, rounded the way of the trade date, buys units.
"""
import conventions as c
from core import money


def pot(contract, received):
    """Pot of a premium received on `received`."""
    return c.FIRST_POT if received < contract.pot_limit else c.LATER_POT


def invested(premium, share, entry, trade):
    """(gross, net) of a premium share: before and after the entry charge."""
    gross = premium * share
    return gross, money.cents(gross * (1 - entry), trade)
