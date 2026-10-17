"""Official scoring of the Neuron migration challenge. The organizers will use exactly this module.

A row counts only if it is exact: amounts to the cent, dates to the day, all six columns of a statement.
"""
import csv
import dataclasses
import datetime as dt
import pathlib
from decimal import Decimal, InvalidOperation

EXTRACT_DATE = dt.date(2026, 6, 30)


def amount(v):
    return Decimal(str(v))


def date(v):
    if isinstance(v, dt.datetime):
        return v.date()
    return v if isinstance(v, dt.date) else dt.date.fromisoformat(str(v))


def policy(v):
    return str(v).strip()


@dataclasses.dataclass(frozen=True)
class Task:
    key: tuple  # converters of the key columns, in file order
    value: tuple  # converters of the value columns, in file order

    def read(self, path):
        """Target file -> {key: value}, keys and values in the submission format."""
        with open(path, encoding="utf-8") as f:
            rows = list(csv.reader(f))[1:]
        n = len(self.key)
        return {self.make_key(r[:n]): self.make_value(r[n:n + len(self.value)]) for r in rows}

    def make_key(self, parts):
        parts = parts if isinstance(parts, (tuple, list)) else (parts,)
        key = tuple(convert(p) for convert, p in zip(self.key, parts, strict=True))
        return key[0] if len(key) == 1 else key

    def make_value(self, parts):
        parts = parts if isinstance(parts, (tuple, list)) else (parts,)
        value = tuple(convert(p) for convert, p in zip(self.value, parts, strict=True))
        return value[0] if len(value) == 1 else value


TASKS = {
    "t0_commission": Task((policy, int), (amount,)),
    "t1_next_due_dates": Task((policy, int), (date, date)),
    "t2_projected_maturity_value": Task((policy,), (amount,)),
    "t3_surrender_value": Task((policy, date), (amount,)),
    "t4_annual_statement": Task((policy, int), (amount,) * 6),
}
OUTLIER_TASK = "t5_outlier_detection"


def read_targets(folder, task):
    return TASKS[task].read(pathlib.Path(folder) / f"{task}.csv")


def arguments(task, targets):
    """Extra arguments of a task function besides `legacy_dir`."""
    if task == "t1_next_due_dates":
        return (EXTRACT_DATE,)
    if task == "t3_surrender_value":
        return (sorted({d for _, d in targets}),)
    return ()


def normalize(task, predictions):
    """Submission result -> {key: value} in the canonical types; malformed entries are dropped."""
    out = {}
    for key, value in (predictions or {}).items():
        try:
            out[TASKS[task].make_key(key)] = TASKS[task].make_value(value)
        except (TypeError, ValueError, InvalidOperation):
            continue
    return out


def normalize_outliers(items):
    out = set()
    for task, key in items or ():
        try:
            out.add((task, TASKS[task].make_key(key)))
        except (KeyError, TypeError, ValueError, InvalidOperation):
            continue
    return out


def accuracy(task, predictions, targets, excluded=frozenset()):
    """(correct rows, scored rows); `excluded` keys (manual corrections) are not scored."""
    predictions = normalize(task, predictions)
    keys = [k for k in targets if k not in excluded]
    return sum(1 for k in keys if predictions.get(k) == targets[k]), len(keys)


def f1(predicted, actual):
    true_positives = len(predicted & actual)
    if not true_positives:
        return 0.0
    precision, recall = true_positives / len(predicted), true_positives / len(actual)
    return 2 * precision * recall / (precision + recall)


def maintainability(folder):
    """Maintainability index of a submission (radon, 0 to 100, higher is better).

    Radon rates every Python file on its own; the index of the submission is the average of the files, weighted
    by their source lines of code. Returns {"index": ..., "files": {name: index}}, or None if radon is missing.
    """
    try:
        from radon.metrics import mi_visit
        from radon.raw import analyze
    except ImportError:
        return None
    folder = pathlib.Path(folder)
    files = {}
    for path in sorted(folder.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        files[path.relative_to(folder).as_posix()] = (mi_visit(source, multi=True), max(1, analyze(source).sloc))
    total = sum(sloc for _, sloc in files.values())
    return {"index": round(sum(mi * sloc for mi, sloc in files.values()) / total, 1) if files else None,
            "files": {name: round(mi, 1) for name, (mi, _) in files.items()}}


def print_maintainability(result):
    """Print the result of `maintainability`."""
    if result is None:
        print("maintainability index: not measured, radon is not installed (pip install radon)")
        return
    print(f"maintainability index: {result['index']} (per file, weighted by lines of code)")
    for name, index in result["files"].items():
        print(f"  {name:40s} {index:6.1f}")
