"""The frozen submission: same score as the lab (scoring.accuracy), no target files read outside t5."""
import builtins
import sys

import polars as pl
import pytest

from neuronlab import evaluate, frame, paths, store

sys.path.insert(0, str(paths.SUBMISSION))
import submission  # noqa: E402
import scoring  # noqa: E402  (store puts the starter kit on sys.path)

LEGACY = str(paths.LEGACY)


def test_t0_matches_the_lab_and_the_official_scoring():
    predictions = submission.t0_commission(LEGACY)
    targets = scoring.read_targets(paths.TARGETS, "t0_commission")
    assert scoring.accuracy("t0_commission", predictions, targets) == (225848, 225858)
    df, meta = frame.load("t0_commission")
    pool = __import__("json").loads((paths.run_dir("t0_commission") / "pool.json").read_text())
    info = pool["values"]["amount"]
    best = next(c for c in info["candidates"] if c["id"] == info["best"])
    lab = df.select("policy_id", "due_nr").with_columns(evaluate.predicted(df, best, "amount").alias("p"))
    assert all(predictions[(p, d)] == v for p, d, v in lab.iter_rows())


def test_t5_reports_the_manual_corrections():
    outliers = submission.t5_outlier_detection(LEGACY, str(paths.TARGETS))
    assert len(outliers) == 10 and all(task == "t0_commission" for task, _ in outliers)


@pytest.mark.parametrize("task", list(scoring.TASKS))
def test_firewall(task, monkeypatch, tmp_path):
    """Task functions t0-t4 never open a file of the targets folder."""
    real_open = builtins.open
    targets = str(paths.TARGETS.resolve())

    def guarded(file, *args, **kwargs):
        if str(file).startswith(targets) or "/targets/" in str(file):
            raise AssertionError(f"{task} opened a target file: {file}")
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", guarded)
    args = scoring.arguments(task, store.target(task).select(store.target_columns(task)[0]).rows()
                             if task == "t3_surrender_value" else {})
    getattr(submission, task)(LEGACY, *args)
