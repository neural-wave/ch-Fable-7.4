"""Acceptance test of the pipeline on t0: every step finds what the plan measured, without any LLM."""
import json

import pytest

from neuronlab import cli, paths

TASK = "t0_commission"


@pytest.fixture(scope="module")
def run():
    cli.run(TASK)
    folder = paths.run_dir(TASK)
    return {name: json.loads((folder / f"{name}.json").read_text())
            for name in ("profile", "clusters", "trees", "pool", "residuals")}


def test_grain_and_filter(run):
    grain = run["profile"]["grain"]["best"]
    assert grain["table"] == "NRPREM" and grain["columns"] == {"policy_id": "PR_POLNR", "due_nr": "PR_DUENR"}
    assert round(grain["coverage"], 3) == 0.948
    flt = run["profile"]["filter"]
    assert flt["column"] == "PR_STATE" and flt["keep"] == ["P"] and flt["errors"] == 0


def test_clusters(run):
    info = run["clusters"]["values"]["amount"]
    assert info["relation"] == {"kind": "ratio", "input": "PR_AMTRC"}
    assert [c["center"] for c in info["centers"]] == ["0.005", "0.01", "0.015", "0.02", "0.03", "0.04"]
    assert [c["rows"] for c in info["centers"]] == [137, 253, 185, 53683, 102865, 68725]
    assert info["noise"] == 10


def test_optimal_tree(run):
    info = run["trees"]["values"]["amount"]
    assert info["best"] == {"errors": 0, "leaves": 6}
    sets = [set(s["features"]) for s in info["minimal_sets"]]
    assert {"BR_TIER@PR_RCVDT", "RK_TARKEY[6]"} in sets


def test_pool_winner_is_the_lookup(run):
    info = run["pool"]["values"]["amount"]
    best = next(c for c in info["candidates"] if c["id"] == info["best"])
    assert best["lookup"]["table"] == "NRCOMR"
    assert best["lookup"]["keys"] == {"CR_TIER": "BR_TIER@PR_RCVDT", "CR_PAYTP": "RK_TARKEY[6]"}
    assert best["score"]["total"] == [225848, 225858]
    assert best["score"]["holdout"] == [44051, 44052]


def test_residuals_are_noise(run):
    info = run["residuals"]["values"]["amount"]
    assert info["residuals"] == 10 and info["noise"] == 10 and info["structure"] == {}
    assert info["whole_unit_deltas"] == 10 and info["in_NREXCP"] == 6
