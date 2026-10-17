"""Where a rule changes: the conditions under which the current rule is wrong.

- `tree`: a decision tree learns from the features which rows the rule gets wrong. Every leaf where the rule is
  mostly wrong, or wrong LIFT times as often as overall when the wrong rows are few, becomes a condition such as `PH_APPDT@last <= 2007-08-06 and PH_FREQ = E`, with the rows it holds
  and how many of them are wrong, counted on all rows. A split on a date shows as a date.
- `change_points`: along every date and timestamp, the days where the share of wrong rows jumps (binary
  segmentation by least squares). A sudden jump points to a system change, a gentle slope to none.
"""
import datetime as dt

import numpy as np
import polars as pl
from sklearn.tree import DecisionTreeClassifier

from detective.features import numeric

SAMPLE = 200_000  # the most rows a tree is trained on: all wrong rows and a sample of the right ones
DEPTH = 3
MIN_LEAF = 20
MOSTLY = 0.5  # a leaf whose share of wrong rows is at least this becomes a condition
LIFT = 3  # ... or at least LIFT times the share of all rows
EPOCH = dt.date(1970, 1, 1)
CHANGES = 3  # change points per column
MIN_SEGMENT = 0.01  # the smallest segment of a change point, as a share of the rows


def training_rows(wrong: np.ndarray, seed: int = 0) -> np.ndarray:
    """The indices of all wrong rows and of a sample of the right ones, SAMPLE rows at most."""
    generator = np.random.default_rng(seed)
    bad, good = np.flatnonzero(wrong), np.flatnonzero(~wrong)
    room = max(SAMPLE - bad.size, 0)
    return np.sort(np.concatenate([bad, generator.choice(good, min(room, good.size), replace=False)]))


def shown(name: str, threshold: float, dtypes: dict) -> str:
    """A threshold as people read it: a date for a date column, a day and time for a timestamp."""
    base = dtypes.get(name)
    if base == pl.Date:
        return str(EPOCH + dt.timedelta(days=int(np.floor(threshold))))
    if isinstance(base, pl.Datetime):
        return str(dt.datetime(1970, 1, 1) + dt.timedelta(days=threshold))
    return f"{threshold:g}"


def condition(name: str, left: bool, threshold: float, dtypes: dict) -> str:
    """One step of a path in words: `X <= t`, `X > t`, `X = v` or `X != v` for one-hot texts, flags as names."""
    if "=" in name and name.split("=")[0] in dtypes and dtypes[name.split("=")[0]] == pl.String:
        column, value = name.split("=", 1)
        return f"{column} != {value}" if left else f"{column} = {value}"
    if dtypes.get(name) == pl.Boolean:
        return f"not {name}" if left else name
    return f"{name} {'<=' if left else '>'} {shown(name, threshold, dtypes)}"


def paths(model: DecisionTreeClassifier, names: list[str], dtypes: dict) -> dict[int, list[str]]:
    """{leaf: conditions on the way from the root to it}."""
    structure = model.tree_
    found, stack = {}, [(0, [])]
    while stack:
        node, steps = stack.pop()
        if structure.children_left[node] == -1:
            found[node] = steps
            continue
        name, threshold = names[structure.feature[node]], structure.threshold[node]
        stack.append((structure.children_left[node], [*steps, condition(name, True, threshold, dtypes)]))
        stack.append((structure.children_right[node], [*steps, condition(name, False, threshold, dtypes)]))
    return found


def tree(frame: pl.DataFrame, wrong: pl.Series, depth: int = DEPTH) -> list[dict]:
    """The leaves where the rule is mostly (or LIFT times more often) wrong: CONDITIONS, ROWS, WRONG, SHARE; most
    wrong rows first."""
    numbers = numeric(frame)
    matrix = numbers.to_numpy().astype(float)
    flags = wrong.to_numpy().astype(bool)
    chosen = training_rows(flags)
    model = DecisionTreeClassifier(max_depth=depth, min_samples_leaf=MIN_LEAF, class_weight="balanced",
                                   random_state=0).fit(matrix[chosen], flags[chosen])
    leaves = model.apply(matrix)
    counted = pl.DataFrame({"LEAF": leaves, "WRONG": flags}).group_by("LEAF").agg(
        ROWS=pl.len(), WRONG=pl.col("WRONG").sum())
    dtypes = dict(frame.schema)
    conditions = paths(model, numbers.columns, dtypes)
    enough = min(MOSTLY, LIFT * flags.mean())
    rows = [{"CONDITIONS": conditions[leaf], "ROWS": total, "WRONG": bad, "SHARE": bad / total}
            for leaf, total, bad in counted.iter_rows() if bad / total >= enough]
    return sorted(rows, key=lambda row: -row["WRONG"])


def best_split(counts: np.ndarray, wrongs: np.ndarray, smallest: int) -> tuple[int, float]:
    """(index, gain) of the split of a sorted series of (rows, wrong rows) that explains most of the variance."""
    total, bad = counts.sum(), wrongs.sum()
    left_rows, left_bad = np.cumsum(counts)[:-1], np.cumsum(wrongs)[:-1]
    right_rows, right_bad = total - left_rows, bad - left_bad
    with np.errstate(divide="ignore", invalid="ignore"):
        gap = left_bad / left_rows - right_bad / right_rows
        gain = gap * gap * left_rows * right_rows / total
    gain[(left_rows < smallest) | (right_rows < smallest)] = 0
    index = int(np.nanargmax(gain)) if gain.size else 0
    return index, float(np.nan_to_num(gain[index])) if gain.size else 0.0


def segments(values: np.ndarray, counts: np.ndarray, wrongs: np.ndarray, smallest: int, depth: int) -> list[tuple]:
    """(last value before, first value after, gain) of the change points of one sorted series, recursively."""
    if depth == 0 or values.size < 2:
        return []
    index, gain = best_split(counts, wrongs, smallest)
    if gain <= 0:
        return []
    left = segments(values[:index + 1], counts[:index + 1], wrongs[:index + 1], smallest, depth - 1)
    right = segments(values[index + 1:], counts[index + 1:], wrongs[index + 1:], smallest, depth - 1)
    return sorted([*left, (values[index], values[index + 1], gain), *right], key=lambda change: -change[2])[:CHANGES]


def change_points(frame: pl.DataFrame, wrong: pl.Series, top: int = 10) -> list[dict]:
    """The date and timestamp columns where the share of wrong rows jumps most: COLUMN, BEFORE, AFTER,
    RATE_BEFORE, RATE_AFTER and EXPLAINED (the share of the variance of the wrong flag the jump explains)."""
    found = []
    variance = float(wrong.cast(pl.Float64).var(ddof=0)) * len(wrong)
    for column, dtype in frame.schema.items():
        if dtype != pl.Date and not isinstance(dtype, pl.Datetime):
            continue
        series = pl.DataFrame({"X": frame[column], "W": wrong}).drop_nulls().group_by("X").agg(
            N=pl.len(), W=pl.col("W").sum()).sort("X")
        if series.height < 2:
            continue
        smallest = max(int(MIN_SEGMENT * series["N"].sum()), 1)
        changes = segments(series["X"].to_numpy(), series["N"].to_numpy(), series["W"].to_numpy(), smallest, 2)
        found.extend(described_change(column, series, before, after, gain / variance) for before, after, gain in
                     changes[:1])
    return sorted(found, key=lambda row: -row["EXPLAINED"])[:top]


def described_change(column: str, series: pl.DataFrame, before, after, explained: float) -> dict:
    """A change point in words: where it is, the share of wrong rows on both sides, how much it explains."""
    left, right = series.filter(pl.col("X").le(before)), series.filter(pl.col("X").ge(after))
    return {"COLUMN": column, "BEFORE": str(before), "AFTER": str(after),
            "RATE_BEFORE": left["W"].sum() / left["N"].sum(), "RATE_AFTER": right["W"].sum() / right["N"].sum(),
            "EXPLAINED": explained}
