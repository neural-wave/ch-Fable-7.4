"""t1: the next due dates of the premiums and the days they are collected."""
from neuron import add_months, grouped, table, valid
from policies.codes import has_due_dates
from policies.schedule import collection_date, due_dates


def t1_next_due_dates(legacy_dir, extract_date):
    """{(policy_id, n): (due_date, collection_date)} for the due dates in the year after `extract_date`, n = 1, 2, ...

    Policies in force and premium paying on the extract date. Direct debits are collected on the next bank
    working day, bank transfers on the due date.
    """
    year_end = add_months(extract_date, 12)
    result = {}
    for policy_id, versions in grouped(table(legacy_dir, "NRPOLH"), "PH_POLNR").items():
        policy = valid(versions, "PH", extract_date)
        if has_due_dates(policy):
            for n, due_date in enumerate(due_dates(policy, extract_date, year_end), start=1):
                result[policy_id, n] = due_date, collection_date(due_date, policy["PH_PAYMT"])
    return result
