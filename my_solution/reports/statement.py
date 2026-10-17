"""Annual statement (task t4): what a policy paid and was charged, calendar year by year.

    premiums       paid items, by year of their money date
    entry charges  premium share less invested amount of each PRM booking, by trade year
    admin, management, risk charges   the charges of the runs of the year
    total charges  entry + admin + management + risk

There is a row for every year of periods.statement_years, also when nothing happened in it.
The entry charges of a year are rounded half up to the cent: Neuron NG writes statements.
"""
import operator
from decimal import Decimal

import conventions as c
from core import lookup, totals
from reports import periods

YEAR, AMOUNT, GROSS = operator.attrgetter("day.year"), operator.attrgetter("amount"), operator.attrgetter("gross")


def received_year(item):
    """Year of the money date of a premium item."""
    return item["PR_RCVDT"].year


def sums(export, contract, bookings):
    """{column: Counter {year: amount}} of a policy, unrounded."""
    kinds = lookup.group_by(bookings, operator.attrgetter("kind"))
    columns = {kind: totals.by_key(kinds.get(kind, []), YEAR, AMOUNT) for kind in (c.ADMIN, c.MANAGEMENT, c.RISK)}
    entry = totals.by_key(kinds.get(c.PREMIUM, []), YEAR, GROSS)
    entry.subtract(totals.by_key(kinds.get(c.PREMIUM, []), YEAR, AMOUNT))
    paid = totals.by_key(export.premiums.get(contract.policy_id, []), received_year, operator.itemgetter("PR_AMTRC"))
    return {"premiums": paid, "entry": entry, **columns}


def statement(export, contract, bookings):
    """{year: (premiums, entry, admin, management, risk, total charges)} of a policy."""
    columns, rows = sums(export, contract, bookings), {}
    for year in periods.statement_years(contract, bookings):
        entry = Decimal(columns["entry"][year]).quantize(c.CENT, rounding=c.ROUNDING_JAVA)
        charged = (entry, columns[c.ADMIN][year], columns[c.MANAGEMENT][year], columns[c.RISK][year])
        rows[year] = (columns["premiums"][year], *charged, sum(charged))
    return rows
