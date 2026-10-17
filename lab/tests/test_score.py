"""`lab score`: exact score of a written function, residuals explained by the trees, firewall on target files."""
import shutil

import pytest

from neuronlab import paths, score

TASK = "t0_commission"
RECEIPT_DATE = 'valid(policy_headers[premium_item["PR_POLNR"]], "PH", premium_item["PR_RCVDT"])'


@pytest.fixture(autouse=True, scope="module")
def pipeline():
    if not (paths.run_dir(TASK) / "frame.parquet").exists():
        from neuronlab import cli
        cli.run(TASK)


def scratch(tmp_path, replace=None):
    """A copy of the submission folder, with one piece of t0_commission replaced."""
    shutil.copytree(paths.SUBMISSION, tmp_path, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__"))
    if replace:
        source = (tmp_path / "submission.py").read_text(encoding="utf-8")
        assert replace[0] in source
        (tmp_path / "submission.py").write_text(source.replace(*replace), encoding="utf-8")
    return tmp_path


def test_the_frozen_rule_leaves_only_noise(tmp_path):
    text = score.score(TASK, folder=scratch(tmp_path))
    assert "Exact rows: 225848 / 225858 (holdout 44051 / 44052)" in text
    assert "noise 10 (policies listed in NREXCP: 6)" in text
    assert "one cluster only" in text


def test_the_differences_are_saved_for_the_charts(tmp_path):
    """diffs.parquet: one row per target row, difference 0 exactly on the right rows, whole units on the others."""
    import polars as pl
    score.score(TASK, folder=scratch(tmp_path))
    diffs = pl.read_parquet(paths.run_dir(TASK) / "diffs.parquet")
    assert diffs.height == 225858
    assert (diffs["target:amount"] == diffs["computed:amount"]).sum() == 225848
    wrong = diffs.filter(pl.col("diff:amount") != 0)
    assert wrong.height == 10 and (wrong["diff:amount"] % 1 == 0).all()


def test_a_wrong_rule_is_explained_by_the_missing_feature(tmp_path):
    """Current tier instead of the tier on the money date: the trees point at the receipt date."""
    folder = scratch(tmp_path, (RECEIPT_DATE, 'latest(policy_headers[premium_item["PR_POLNR"]], "PH")'))
    source = (folder / "submission.py").read_text(encoding="utf-8")
    (folder / "submission.py").write_text(source.replace("from neuron import cents,", "from neuron import cents, latest,"),
                                          encoding="utf-8")
    text = score.score(TASK, folder=folder)
    assert "Exact rows: 224418 / 225858" in text
    assert "| x0.67 | 515 |" in text
    where = next(line for line in text.splitlines() if line.startswith("Where it is wrong"))
    assert "@PR_RCVDT" in where


def test_reading_a_target_file_is_refused(tmp_path):
    folder = scratch(tmp_path, ('    commission_rates = keyed(', '    open(r"%s")\n    commission_rates = keyed('
                                % (paths.TARGETS / "t0_commission.csv")))
    with pytest.raises(PermissionError):
        score.score(TASK, folder=folder)


def test_labels_of_dates_in_tuples_and_of_amounts():
    """Two date values per key (t1) and one amount per policy (t2): shared differences and shared ratios."""
    import datetime as dt
    from decimal import Decimal
    day = dt.date(2026, 7, 4)
    targets = {(p, 1): (day, day + dt.timedelta(days=2)) for p in ("P1", "P2", "P3", "P4")}
    computed = {k: (v[0], v[0]) for k, v in targets.items() if k[0] != "P4"}
    labels = score.compare("t1_next_due_dates", targets, computed)
    assert labels["due_date"] == ["ok", "ok", "ok", "missing"]
    assert labels["collection_date"] == ["+2 days", "+2 days", "+2 days", "missing"]
    amounts = {"P1": Decimal("98.00"), "P2": Decimal("196.00"), "P3": Decimal("294.00"), "P4": Decimal("10.00")}
    computed = {"P1": Decimal("100.00"), "P2": Decimal("200.00"), "P3": Decimal("300.00"), "P4": Decimal("10.01")}
    assert score.compare("t2_projected_maturity_value", amounts, computed)["maturity_value"] == [
        "x0.98", "x0.98", "x0.98", "noise"]
