"""The train targets and the official scoring, to compare a rule with the expected values while exploring.

Only the tools read the targets: the submission calculates everything from the legacy export.
"""
import functools
import importlib.util

import polars as pl

from neuron.load import DATA, HAND_IN

TARGETS = DATA.joinpath("targets")


def target(task: str, policy_id: str | None = None) -> pl.DataFrame:
    """Target file of a task (e.g. "t0_commission"), optionally of one policy only.

    Polars parses the dates; amounts are floats, so exact comparisons go through `score` and `mismatches`.
    """
    frame = pl.scan_csv(TARGETS.joinpath(f"{task}.csv"), try_parse_dates=True)
    if policy_id:
        frame = frame.filter(pl.col("policy_id").eq(policy_id))
    return frame.collect()


def target_tasks() -> list[str]:
    """Names of all target files.

    The scored ones (t0 to t4) and the diagnostic ones with intermediate values, like "t3_holding".
    """
    return sorted(path.stem for path in TARGETS.glob("t*.csv"))


@functools.cache
def scoring():
    """The official scoring module `scoring.py` of the starter kit, next to the hand-in folder.

    It has the exact converters of keys and values and the accuracy as the organizers count it.
    """
    spec = importlib.util.spec_from_file_location("scoring", HAND_IN.parent.joinpath("scoring.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def score(task: str, predictions: dict) -> tuple[int, int]:
    """(correct rows, total rows) of `predictions` against the train targets of `task`.

    The train targets still contain the manual corrections, so a perfect rule stays a little below 100 %.
    """
    official = scoring()
    return official.accuracy(task, predictions, official.read_targets(TARGETS, task))


def mismatches(task: str, predictions: dict) -> pl.DataFrame:
    """One row per target that `predictions` misses or gets wrong: the key, the expected and the predicted value.

    Values are compared after the official normalization, so 12.3 and 12.30 are the same amount: a target is
    wrong when its (key, value) pair is not among the predictions.
    """
    official = scoring()
    expected = official.read_targets(TARGETS, task)
    got = official.normalize(task, predictions)
    rows = [{"key": str(key), "expected": str(value), "predicted": str(got.get(key))}
            for key, value in sorted(set(expected.items()).difference(got.items()))]
    return pl.DataFrame(rows, schema={"key": pl.String, "expected": pl.String, "predicted": pl.String})
