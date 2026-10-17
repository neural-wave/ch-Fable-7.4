"""Neuron migration: one function per task, each a composition of small rule modules.

Every value is calculated from the legacy export in `legacy_dir`. The conventions of Neuron
live in conventions.py, each rule in one small module of its business package with its
explanation (ARCHITECTURE.md is the map); this file only applies the rules to the portfolio
and returns them in the submission format. Dates are datetime.date, amounts decimal.Decimal.
"""
import export
from accounting import ledger
from billing import collection, commission, schedule
from core import months
from legacy import portfolio, premiums
from maturity import projection
from reports import statement, valuation


def t0_commission(legacy_dir):
    """{(policy_id, due_nr): amount}: the broker commission of every paid premium item.

    The rule is in billing/commission.py.
    """
    commission_of = commission.calculator(legacy_dir)
    return {(item["PR_POLNR"], item["PR_DUENR"]): commission_of(item) for item in premiums.paid_items(legacy_dir)}


def t1_next_due_dates(legacy_dir, extract_date):
    """{(policy_id, n): (due_date, collection_date)} of the year after the extract date.

    The policy version valid on the extract date decides state, frequency and payment;
    the rules are in billing/schedule.py and billing/collection.py.
    """
    until = months.add_months(extract_date, 12)
    scheduled = filter(portfolio.pays_premiums, portfolio.policies_on(legacy_dir, extract_date))
    return {
        (policy["PH_POLNR"], n): (due, collection.collection_day(due, policy["PH_PAYMT"]))
        for policy in scheduled
        for n, due in enumerate(schedule.due_dates(policy, extract_date, until), start=1)
    }


def t2_projected_maturity_value(legacy_dir):
    """{policy_id: maturity_value}: the projection of the offer of every policy.

    The month-by-month projection is in maturity/projection.py.
    """
    data = export.load(legacy_dir)
    return {policy_id: projection.maturity_value(data, data.contract(policy_id)) for policy_id in data.versions}


def t3_surrender_value(legacy_dir, valuation_dates):
    """{(policy_id, valuation_date): surrender_value} of every policy started by that day.

    The bookings of each policy come from accounting/ledger.py, the values from
    reports/valuation.py.
    """
    data = export.load(legacy_dir)
    return {
        (contract.policy_id, day): value
        for contract, bookings in ledger.ledgers(data)
        for day, value in valuation.surrender_values(data, contract, bookings, valuation_dates).items()
    }


def t4_annual_statement(legacy_dir):
    """{(policy_id, year): (premiums, entry, admin, management, risk, total charges)}.

    The yearly sums of the same bookings as t3, in reports/statement.py.
    """
    data = export.load(legacy_dir)
    return {
        (contract.policy_id, year): row
        for contract, bookings in ledger.ledgers(data)
        for year, row in statement.statement(data, contract, bookings).items()
    }


def t5_outlier_detection(legacy_dir, targets_dir):
    """{(task, key)} of the values changed by hand: still to be written.

    Recipe in PLAN.md, section 4.6: rule mismatches with a whole-unit delta, plus NREXCP.
    """
    return set()
