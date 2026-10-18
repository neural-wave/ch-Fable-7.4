"""Plain-language labels: every word comes from NRDICT, NRCODE, SCHEMA.md or the rule, and t0-t4 are covered."""
import json

import pytest

from neuronlab import labels, paths

DATA = pytest.mark.skipif(not (paths.LEGACY / "NRDICT.csv").exists(), reason="needs the legacy extract")
TASKS = ("t0_commission", "t1_next_due_dates", "t2_projected_maturity_value", "t3_surrender_value",
         "t4_annual_statement")


def test_numbers_and_constants_in_words():
    assert labels.ordinal(1) == "1st" and labels.ordinal(12) == "12th" and labels.ordinal(23) == "23rd"
    assert [labels.number(x) for x in ("0.020000", "61100.00", "0.005000", "7", "FLSP")] == [
        "0.02", "61100.00", "0.005", "7", "FLSP"]
    assert labels.percent("0.985") == "98.5 %"
    assert labels.constant({"kind": "ratio", "input": "policy_value"}, "1") == "the policy value itself"
    assert labels.constant({"kind": "const"}, "12.50") == "always 12.5"


@DATA
def test_conditions_read_the_dictionary_and_the_codes():
    assert labels.condition(["PH_FREQ", "=", "M"]) == "the premium frequency is monthly"
    assert labels.condition(["PH_STATE", "!=", "30"]) == "the policy state is not premium holiday"
    assert labels.condition(["PR_STATE", "=", "P"]) == "the item state is paid"  # domain PRSTAT, not STATE
    assert labels.condition(["PH_VRSST", "=", "C"]) == "the version status is current"  # codes inline in NRDICT
    assert labels.condition(["BR_TIER@PR_RCVDT", "=", "A"]) == "the broker tier on the money received date is A"
    assert labels.condition(["RK_TARKEY[6]", "=", "E"]) == "the premium type (6th character of the tariff key) is single"
    assert labels.condition(["weekday(valuation_date)", "=", "7"]) == "the day of the week of the valuation date is a Sunday"
    assert labels.condition(["month_end(valuation_date)", "!=", "true"]) == \
        "the valuation date is not the last day of its month"
    assert labels.feature("PH_FREQ").question("H") == "Is the premium frequency half-yearly?"
    assert labels.constant({"kind": "ratio", "input": "PR_AMTRC"}, "0.02") == "2 % of the amount received"
    assert labels.constant({"kind": "months", "input": "previous(due_date)"}, "1") == \
        "1 month after the previous due date of the same policy"


@DATA
@pytest.mark.parametrize("task", TASKS)
def test_every_feature_of_the_trees_and_winners_has_words(task):
    folder = paths.RUNS / task
    if not (folder / "trees.json").exists():
        pytest.skip("no run of the task")
    tests = []

    def walk(node):
        if "leaf" not in node:
            tests.append(tuple(node["split"]))
            walk(node["yes"])
            walk(node["no"])
    for info in json.loads((folder / "trees.json").read_text())["values"].values():
        for chosen in info.get("minimal_sets", [])[:1]:
            walk(chosen["tree"])
    features = {f for f, _ in tests}
    for info in json.loads((folder / "pool.json").read_text())["values"].values():
        best = next(c for c in info["candidates"] if c["id"] == info["best"])
        features |= set(best["features"]) | ({best["relation"]["input"]} if best["relation"].get("input") else set())
    assert [f for f in features if not labels.feature(f, task).known] == []
    unexplained = {f"{f}={v}" for f, v in tests if not labels.feature(f, task).explained(v)}
    assert unexplained <= {"PH_PRDCD=FLSP"}  # product codes have no text in NRCODE
