"""t4: the annual statement of each policy, the premiums and the charges per calendar year."""
import datetime as dt
from collections import defaultdict

from funds import FundAccounting
from neuron import calendar_years, cents
from policies.codes import is_closed, is_paid

LAST_STATEMENT_DAY = dt.date(2025, 12, 31)  # the end of the last calendar year that is complete in the extract
CHARGES = ("entry", "admin", "management", "risk")


def t4_annual_statement(legacy_dir):
    """{(policy_id, year): (premiums, entry_charges, admin_fees, management_fees, risk_charges, total_charges)}

    Premiums: the paid NRPREM items by PR_RCVDT; charges: the bookings of the fund accounting (t3) by booking
    day, the entry charge on the trade date of the premium, the monthly charges on the day of the charge run.
    """
    accounting = FundAccounting(legacy_dir)
    result = {}
    for policy_id, versions in accounting.policies.items():
        premiums = premiums_by_year(accounting.premiums.get(policy_id, []))
        charges = accounting.replay(policy_id, []).charges
        for year in statement_years(versions):
            amounts = [cents(sum(charges[year, charge])) for charge in CHARGES]
            result[policy_id, year] = (cents(sum(premiums[year])), *amounts, sum(amounts))
    return result


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
