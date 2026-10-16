"""Annual statement (task t4): what a policy paid and was charged, calendar year by year.

    premiums       paid items, by year of their money date
    entry charges  premium share less invested amount of each PRM booking, by trade year
    admin, management, risk charges   the charges of the runs of the year
    total charges  entry + admin + management + risk

There is a row for every year of runs.statement_years, also when nothing happened in it.
The entry charges of a year are rounded half up to the cent: Neuron NG writes statements.
"""
import collections
import operator
from decimal import Decimal

import conventions as c
import lookup
import runs


def by_year(bookings, amount):
    """Counter {year: sum of `amount(booking)`} of `bookings`."""
    years = collections.Counter()
    for booking in bookings:
        years.update({booking.day.year: amount(booking)})
    return years


def sums(export, contract, bookings):
    """{column: Counter {year: amount}} of a policy, unrounded."""
    kinds = lookup.group_by(bookings, operator.attrgetter("kind"))
    columns = {kind: by_year(kinds.get(kind, []), operator.attrgetter("amount")) for kind in (c.ADMIN, c.MANAGEMENT, c.RISK)}
    entry = by_year(kinds.get(c.PREMIUM, []), operator.attrgetter("gross"))
    entry.subtract(by_year(kinds.get(c.PREMIUM, []), operator.attrgetter("amount")))
    paid = collections.Counter()
    for item in export.premiums.get(contract.policy_id, []):
        paid.update({item["PR_RCVDT"].year: item["PR_AMTRC"]})
    return {"premiums": paid, "entry": entry, **columns}


def statement(export, contract, bookings):
    """{year: (premiums, entry, admin, management, risk, total charges)} of a policy."""
    columns, rows = sums(export, contract, bookings), {}
    for year in runs.statement_years(contract, bookings):
        entry = Decimal(columns["entry"][year]).quantize(c.CENT, rounding=c.ROUNDING_JAVA)
        charged = (entry, columns[c.ADMIN][year], columns[c.MANAGEMENT][year], columns[c.RISK][year])
        rows[year] = (columns["premiums"][year], *charged, sum(charged))
    return rows
