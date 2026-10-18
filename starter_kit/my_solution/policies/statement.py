"""The annual statement of a policy: the years it covers and the premiums received in each of them."""
import datetime as dt
from collections import defaultdict

from neuron import calendar_years
from policies.codes import is_closed, is_paid

LAST_STATEMENT_DAY = dt.date(2025, 12, 31)  # the end of the last calendar year that is complete in the extract
CHARGES = ("entry", "admin", "management", "risk")  # the charge columns of the statement, in file order


def premiums_by_year(premiums):
    """{year: [amount, ...]} of the paid premium items, by the year the money was received."""
    years = defaultdict(list)
    for premium in filter(is_paid, premiums):
        years[premium["PR_RCVDT"].year].append(premium["PR_AMTRC"])
    return years


def statement_years(versions):
    """The calendar years from the begin date to the year the policy is closed, at most to LAST_STATEMENT_DAY.

    A closed policy still gets the statement of its closing year, the year its closed version is valid from.
    """
    closed = [version["PH_VLDFR"] for version in versions if is_closed(version)]
    return calendar_years(min(version["PH_BEGDT"] for version in versions), min([*closed, LAST_STATEMENT_DAY]))
