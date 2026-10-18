"""t5: the target values that the rules do not reproduce, the candidates for the manual corrections."""
import datetime as dt
from decimal import Decimal

from neuron import read_targets

EXTRACT_DATE = dt.date(2026, 6, 30)  # the extract date of t1_next_due_dates
DATE, AMOUNT = dt.date.fromisoformat, Decimal
COLUMNS = {  # task: (key converters, value converters) of its target file
    "t0_commission": ((str, int), (AMOUNT,)),
    "t1_next_due_dates": ((str, int), (DATE, DATE)),
    "t2_projected_maturity_value": ((str,), (AMOUNT,)),
    "t3_surrender_value": ((str, DATE), (AMOUNT,)),
    "t4_annual_statement": ((str, int), (AMOUNT, AMOUNT, AMOUNT, AMOUNT, AMOUNT, AMOUNT)),
}


def outliers(rules, legacy_dir, targets_dir):
    """{(task, key)} of the target values that differ from the value of the rule of their task.

    `rules` are the task functions. A key that the rule does not calculate is a rule not found yet, not a
    manual correction, so only the keys of both sides are compared.
    """
    found = set()
    for task, rule in rules.items():
        computed = rule(legacy_dir, *arguments(task, targets_dir))
        targets = read_targets(targets_dir, task, *COLUMNS[task])
        # the (key, value) pairs of the targets that the rule does not give, of the keys the rule calculates
        differing = {key for key, _ in set(targets.items()).difference(computed.items())}
        found.update((task, key) for key in differing.intersection(computed))
    return found


def arguments(task, targets_dir):
    """The arguments of a task function after `legacy_dir`: t1 gets the extract date, t3 the valuation dates."""
    return ARGUMENTS.get(task, lambda targets_dir: ())(targets_dir)


def valuation_dates(targets_dir):
    """The valuation dates of the t3 target file: t5 is the only task that may read the targets."""
    return sorted({day_ for _, day_ in read_targets(targets_dir, "t3_surrender_value", *COLUMNS["t3_surrender_value"])})


ARGUMENTS = {  # task: arguments(targets_dir) of its function after legacy_dir
    "t1_next_due_dates": lambda targets_dir: (EXTRACT_DATE,),
    "t3_surrender_value": lambda targets_dir: (valuation_dates(targets_dir),),
}
