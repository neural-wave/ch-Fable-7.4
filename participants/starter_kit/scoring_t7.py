"""Official scoring of the secret task t7 (tax module). Put this file next to scoring.py in the starter kit.

A row counts only if every column is exact: the country, the amounts to the cent and the remittance date.
"""
import pathlib

import scoring


def optional_date(v):
    return None if v in ("", None) else scoring.date(v)


def country(v):
    return str(v).strip().upper()


TASKS = {
    "t7_tax_payout": scoring.Task((scoring.policy, int), (country,) + (scoring.amount,) * 4 + (optional_date,)),
    "t7_tax_annual": scoring.Task((scoring.policy, int), (scoring.amount,) * 7),
}


def read_targets(folder, task):
    return TASKS[task].read(pathlib.Path(folder) / f"{task}.csv")


def normalize(task, predictions):
    out = {}
    for key, value in (predictions or {}).items():
        try:
            out[TASKS[task].make_key(key)] = TASKS[task].make_value(value)
        except (TypeError, ValueError, ArithmeticError):
            continue
    return out


def accuracy(task, predictions, targets):
    """(correct rows, scored rows)"""
    predictions = normalize(task, predictions)
    return sum(1 for k in targets if predictions.get(k) == targets[k]), len(targets)
