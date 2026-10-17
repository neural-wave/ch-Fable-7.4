"""Freeze never makes the submission worse: refused runs and candidates leave submission.py as it was."""
import json

import pytest

from neuronlab import freeze, paths

TASK = "t0_commission"


@pytest.fixture(autouse=True, scope="module")
def pipeline():
    if not (paths.run_dir(TASK) / "pool.json").exists():
        from neuronlab import cli
        cli.run(TASK)


def submission():
    return (paths.SUBMISSION / "submission.py").read_text(encoding="utf-8")


def test_an_ablation_run_is_refused():
    before = submission()
    with pytest.raises(ValueError, match="ablation run"):
        freeze.freeze(f"{TASK}~ablate")
    assert submission() == before


def test_a_worse_candidate_does_not_replace_the_function():
    info = json.loads((paths.run_dir(TASK) / "pool.json").read_text())["values"]["amount"]
    best = next(c for c in info["candidates"] if c["id"] == info["best"])
    worse = next(c for c in info["candidates"] if c["score"]["total"][0] < best["score"]["total"][0])
    before = submission()
    with pytest.raises(ValueError, match="submission.py is unchanged"):
        freeze.freeze(TASK, worse["id"])
    assert submission() == before


def test_a_task_with_several_values_is_refused():
    before = submission()
    with pytest.raises(ValueError, match="value columns"):
        freeze.freeze("t1_next_due_dates")
    assert submission() == before
