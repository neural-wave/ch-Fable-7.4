"""The two reports of the ledger, surrender values (t3) and statements (t4), in one pass.

Rebuilding the bookings of every policy month by month is the costliest step of the
migration, and both reports read the same bookings. The pass that values the policies
for t3 sums their statements as well and keeps them, so that t4 after t3 in the same
process costs nothing; t4 on its own makes a pass of its own.
"""
from accounting import ledger
from reports import statement, valuation

STATEMENTS = {}  # {export: {(policy_id, year): row}}, kept by the passes made so far


def rows(export, contract, bookings):
    """{(policy_id, year): row} of the statements of one policy."""
    return {(contract.policy_id, year): row for year, row in statement.statement(export, contract, bookings).items()}


def surrender_values(export, days):
    """{(policy_id, day): surrender value} on the valuation `days`; keeps the statements."""
    values, statements_made = {}, {}
    for contract, bookings in ledger.ledgers(export):
        values.update({(contract.policy_id, day): value
                       for day, value in valuation.surrender_values(export, contract, bookings, days).items()})
        statements_made.update(rows(export, contract, bookings))
    STATEMENTS[export] = statements_made
    return values


def own_pass(export):
    """{(policy_id, year): row} of every policy, from a pass of its own."""
    return {key: row for contract, bookings in ledger.ledgers(export) for key, row in rows(export, contract, bookings).items()}


def statements(export):
    """{(policy_id, year): row} of every policy, kept from the pass of t3 if there was one."""
    kept = STATEMENTS.get(export)
    return kept if kept else own_pass(export)
