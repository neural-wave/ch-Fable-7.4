"""`lab serve`: layouts, run history, jobs, the HTTP guard, task definitions, the exact profiling fallback, replay."""
import itertools
import json
import sys
import time
import urllib.error
import urllib.request

import polars as pl
import pytest

from neuronlab import paths, profile, store, taskdef
from neuronlab.web import api, history, layout, legacy, runner, server

TREE = {"split": ["A", "1"], "yes": {"leaf": "0.98", "rows": 10, "errors": 1},
        "no": {"split": ["B", "x"], "yes": {"leaf": "1", "rows": 5, "errors": 0},
               "no": {"split": ["A", "2"], "yes": {"leaf": "0.99", "rows": 3, "errors": 0},
                      "no": {"leaf": "1", "rows": 7, "errors": 2}}}}


def overlap(a, b):
    return a["x"] < b["x"] + b["w"] and b["x"] < a["x"] + a["w"] and a["y"] < b["y"] + b["h"] and b["y"] < a["y"] + a["h"]


def test_tree_layout_has_no_overlap_and_edges_end_on_the_child():
    drawn = layout.tree(TREE)
    nodes = {n["id"]: n for n in drawn["nodes"]}
    assert set(nodes) == {"", "y", "n", "ny", "nn", "nny", "nnn"}
    for a, b in itertools.combinations(drawn["nodes"], 2):
        assert not overlap(a, b), (a["id"], b["id"])
    for e in drawn["edges"]:
        child = nodes[e["to"]]
        x, y = e["points"][-1]
        assert y == child["y"] and child["x"] <= x <= child["x"] + child["w"]
    assert layout.path_to("nny") == ["", "n", "nn", "nny"]


def test_flow_layout_joins_every_leaf_to_the_computation():
    drawn = layout.flow(TREE, "Inputs", "value = x × c", "amount")
    leaves = [n["id"] for n in drawn["nodes"] if n["kind"] == "leaf"]
    into = {e["from"] for e in drawn["edges"] if e["to"] == "compute"}
    assert set(leaves) == into
    assert min(n["x"] for n in drawn["nodes"]) >= 0
    single = layout.flow({"leaf": "NRCOMR.CR_RATE[BR_TIER, RK_TARKEY[6]]"}, "Inputs", "value", "amount")
    assert next(n for n in single["nodes"] if n["id"] == "")["w"] == 560


def test_join_graph_puts_referenced_tables_on_top():
    joins = [{"from": "NRPREM.PR_POLNR", "to": "NRPOLH.PH_POLNR", "kind": "plain"},
             {"from": "NRPOLH.PH_BRKNR", "to": "NRBROK.BR_BRKNR", "kind": "plain"},
             {"from": "NRBROK.BR_BRKNR", "to": "NRPOLH.PH_BRKNR", "kind": "temporal"}]
    drawn = layout.graph(["NRPREM", "NRPOLH", "NRBROK"], joins)
    y = {n["id"]: n["y"] for n in drawn["nodes"]}
    assert y["NRBROK"] < y["NRPOLH"] < y["NRPREM"]
    assert len(drawn["edges"]) == 2  # the temporal edge back from NRBROK shares the plain one's line
    for a, b in itertools.combinations(drawn["nodes"], 2):
        assert not overlap(a, b)


def test_rules_become_the_tree_again():
    def leaves(node, path=()):
        if "leaf" in node:
            return [{"when": [list(c) for c in path], "then": node["leaf"]}]
        f, v = node["split"]
        return leaves(node["yes"], path + ((f, "=", v),)) + leaves(node["no"], path + ((f, "!=", v),))

    def strip(node):
        return {"leaf": node["leaf"]} if "leaf" in node else {"split": node["split"], "yes": strip(node["yes"]),
                                                              "no": strip(node["no"])}
    assert api.rules_tree(leaves(TREE)) == strip(TREE)
    assert api.rules_tree([{"when": [], "then": "0.02"}]) == {"leaf": "0.02"}
    chain = [{"when": [["A", "!=", "1"]], "then": "1"}, {"when": [], "then": "2"}]
    assert api.rules_tree(chain) is None
    assert api.chain_tree(chain)["no"] == {"leaf": "2"}


def test_ledger_bursts_split_on_silence_and_on_scores():
    def entry(t, candidate="C1", hold=1):
        return {"time": t, "candidate": candidate, "holdout": [hold, 2], "discovery": [1, 2], "origin": ""}
    groups = history.bursts([entry("2026-10-17T10:00:00"), entry("2026-10-17T10:00:40", hold=2),
                             entry("2026-10-17T10:05:00"), entry("2026-10-17T10:05:01", "code:abc"),
                             entry("2026-10-17T10:05:02", "code:def")])
    assert [len(g["entries"]) for g in groups] == [2, 1, 1, 1]
    assert history.best_entry(groups[0]["entries"])["holdout"] == [2, 2]
    assert history.kind_of("t0_commission~off-HALF_UP") == "Ablation"
    assert history.kind_of("t0_commission~llm") == "Step 5"


def test_planned_steps_follow_the_commands():
    assert runner.planned("Pipeline", ["lab iterate t0", "lab report t0"]) == {6}
    assert runner.planned("Pipeline", ["lab run t0"]) == {0, 1, 2, 3, 5, 6}
    states = runner.step_states("Pipeline", [{"event": "step", "step": "pool", "state": "done", "secs": 2.0,
                                              "files": ["pool.json"]}], "running", ["lab pool t0", "lab iterate t0"])
    assert [s["state"] for s in states] == ["skipped", "skipped", "skipped", "done", "skipped", "done", "waiting"]


@pytest.fixture
def lab_runs(tmp_path, monkeypatch):
    """An empty runs folder: the history and the jobs of the tests stay out of lab/runs."""
    monkeypatch.setattr(paths, "RUNS", tmp_path / "runs")
    (tmp_path / "runs").mkdir()
    return tmp_path / "runs"


def stub_plan(script):
    def plan(action, task, options=None):
        return "Pipeline", task, [[sys.executable, "-c", script]], {}
    return plan


def wait_for(job_id, states=("done", "failed", "cancelled"), timeout=30):
    end = time.time() + timeout
    while time.time() < end:
        job = history.recorded().get(job_id, {})
        if job.get("status") in states:
            return job
        time.sleep(0.1)
    raise AssertionError(f"job {job_id} still {history.recorded().get(job_id, {}).get('status')}")


def test_a_job_runs_records_its_events_and_ends_done(lab_runs, monkeypatch):
    script = ("from neuronlab import events\n"
              "with events.step('tree', 't0'):\n    print('working', flush=True)\n")
    monkeypatch.setattr(runner, "plan", stub_plan(script))
    jobs = runner.Runner()
    job = jobs.submit("run", "t0")
    done = wait_for(job["id"])
    assert done["status"] == "done" and done["exit"] == 0
    assert done["steps"][2]["state"] == "done"
    assert "working" in open(done["log"], encoding="utf-8").read()
    assert api.job_view(job["id"])["job"]["status"] == "done"


def test_a_running_job_is_cancelled_with_its_children(lab_runs, monkeypatch):
    monkeypatch.setattr(runner, "plan", stub_plan("import time; time.sleep(60)"))
    jobs = runner.Runner()
    job = jobs.submit("run", "t0")
    queued = jobs.submit("run", "t1")
    wait_for(job["id"], ("running",))
    assert jobs.stop_queue() == 1
    assert history.recorded()[queued["id"]]["status"] == "cancelled"
    assert jobs.cancel(job["id"])
    assert wait_for(job["id"])["status"] == "cancelled"


def request(url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers=headers or {}, method="POST" if data is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def test_the_server_answers_and_refuses_foreign_requests(lab_runs):
    httpd, _, base = server.start_in_thread()
    try:
        status, body = request(f"{base}/api/runs")
        assert status == 200 and json.loads(body)["runs"] == []
        assert request(f"{base}/")[0] == 200
        assert request(f"{base}/static/../server.py")[0] == 404
        assert request(f"{base}/api/queue/stop", b"{}", {"Content-Type": "application/json"})[0] == 403
        assert request(f"{base}/api/runs", headers={"Host": "evil.example"})[0] == 403
        status, body = request(f"{base}/api/queue/stop", b"{}", {"Content-Type": "application/json", "X-Ergo": "1"})
        assert status == 200 and json.loads(body) == {"cancelled": 0}
        status, body = request(f"{base}/api/tasks/save", json.dumps({"definition": {"id": "Bad"}}).encode(),
                               {"Content-Type": "application/json", "X-Ergo": "1"})
        assert status == 400 and "schema" in json.loads(body)["error"]
    finally:
        httpd.shutdown()


@pytest.fixture
def task_folder(tmp_path, monkeypatch):
    monkeypatch.setattr(taskdef, "folder", lambda: tmp_path)
    store.target_columns.cache_clear()
    yield tmp_path
    store.target_columns.cache_clear()


def test_a_definition_is_checked_saved_and_read_back(task_folder):
    definition = taskdef.empty("t9_example")
    assert any("key" in p for p in taskdef.structure(definition))
    definition["task"]["keys"] = [{"name": "policy_id", "type": "string"}]
    definition["task"]["values"] = [{"name": "amount", "type": "Decimal(38, 2)", "rounding": "ROUND_HALF_UP"}]
    definition["task"]["hints"] = [{"note": "rounded per instalment"}, {"feature": "f", "expr": "weekday(PR_DUEDT)"}]
    taskdef.save(definition)
    assert taskdef.find("t9_example~llm")["id"] == "t9_example"
    assert taskdef.rounding("t9_example", "amount") == "ROUND_HALF_UP"
    assert taskdef.features("t9_example") == [{"name": "f", "expr": "weekday(PR_DUEDT)"}]
    definition["task"]["values"][0]["rounding"] = "ROUND_SIDEWAYS"
    with pytest.raises(taskdef.Invalid):
        taskdef.save(definition)


@pytest.mark.skipif(not (paths.TARGETS / "t0_commission.csv").exists(), reason="needs the target files")
def test_declared_columns_and_discovery_pairs_reach_the_target(task_folder):
    definition = taskdef.empty("t0_commission")
    definition["task"]["keys"] = [{"name": "policy_id"}, {"name": "due_nr"}]
    definition["task"]["values"] = [{"name": "amount", "rounding": "discover"}]
    definition["examples"]["pairs"] = [{"in": {"policy_id": "ZZ0000001", "due_nr": "1"}, "out": {"amount": "1.00"}}]
    definition["examples"]["pairs_use"] = "discovery"
    taskdef.save(definition)
    assert store.target_columns("t0_commission") == (["policy_id", "due_nr"], ["amount"])
    target = store.target("t0_commission")
    assert target.filter(pl.col("policy_id") == "ZZ0000001")["amount"].to_list()[0] == pytest.approx(1)
    assert any(c["level"] == "ok" and "target file" in c["title"] for c in taskdef.check(definition))


def test_exact_mining_matches_brute_force():
    df = pl.DataFrame({"a": [1, 1, 2, 2], "b": ["x", "y", "x", "y"], "c": [1, 2, 3, 4], "d": [None, None, 5, 5]})
    assert profile.exact_uccs(df) == [["c"], ["a", "b"], ["b", "d"]]
    columns = {"T.a": {"1", "2"}, "T.c": {"1", "2", "3", "4"}, "U.k": {"1", "2"}, "U.z": set()}
    assert profile.exact_inds(columns) == [("T.a", "T.c"), ("T.a", "U.k"), ("U.k", "T.a"), ("U.k", "T.c")]


@pytest.mark.skipif(not (paths.RUNS / "t0_commission" / "frame.parquet").exists(), reason="needs the t0 frame")
def test_a_replayed_row_gets_the_value_of_the_pool():
    from neuronlab import evaluate, frame
    view = api.flow_view("t0_commission")
    df, meta = frame.load("t0_commission")
    pool = json.loads((paths.RUNS / "t0_commission" / "pool.json").read_text())["values"]["amount"]
    best = next(c for c in pool["candidates"] if c["id"] == pool["best"])
    computed = evaluate.predicted(df, best, "amount")
    for preset in view["presets"][:4]:
        replay = api.flow_eval("t0_commission", "amount", None, preset["key"])
        row = df.with_columns(computed.alias("_p")).filter(
            (pl.col("policy_id") == preset["key"][0]) & (pl.col("due_nr") == preset["key"][1]))
        assert replay["computed"] == str(row["_p"][0])
        assert replay["equal"] == (str(row["amount"][0]) == replay["computed"])
    custom = api.flow_eval("t0_commission", "amount", None, view["presets"][0]["key"], {"PR_AMTRC": "1000.00"})
    assert custom["target"] is None and custom["computed"] == "5.00"


def test_schema_files_become_a_dictionary():
    ddl = """CREATE TABLE NRXMPL (
      XM_POLNR CHAR(12) NOT NULL,
      XM_AMNT DECIMAL(15, 2),
      XM_DATE DATE,
      PRIMARY KEY (XM_POLNR)
    );"""
    rows = legacy.dictionary_from_schema(ddl, "sql")
    assert rows == [("NRXMPL", "XM_POLNR", "C", 12, 0, ""), ("NRXMPL", "XM_AMNT", "N", 15, 2, ""),
                    ("NRXMPL", "XM_DATE", "D", 7, 0, "")]
    spec = {"tables": {"NRXMPL": [{"name": "XM_POLNR", "type": "C", "length": 12, "description": "policy"}]}}
    assert legacy.dictionary_from_schema(json.dumps(spec), "json") == [("NRXMPL", "XM_POLNR", "C", 12, 0, "policy")]
    with pytest.raises(ValueError, match="copybook"):
        legacy.receive({"policy.cpy": b"01 POLICY."})


FAKE_CLAUDE = """import json, sys
args = sys.argv[1:]
print(json.dumps({"type": "system", "subtype": "init", "args": args}))
print(json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {"command": "lab run t9"}}]}}))
print(json.dumps({"type": "result", "result": "t9: 10 / 10 exact", "num_turns": 3, "total_cost_usd": 0.5, "session_id": "s-1"}))
sys.exit(int("--fail" in args[-1]))
"""


def test_agent_sessions_write_their_trace_and_summary(tmp_path, monkeypatch, capsys):
    from neuronlab import agent
    fake = tmp_path / "fake_claude.py"
    fake.write_text(FAKE_CLAUDE, encoding="utf-8")
    monkeypatch.setenv("AGENT_MODEL", "opus")
    monkeypatch.delenv("MAX_BUDGET_USD", raising=False)
    command = agent.command("t9_example", [sys.executable, str(fake)])
    assert command[2:9] == ["-p", "--permission-mode", "auto", "--output-format", "stream-json", "--verbose", "--model"]
    assert command[-1].startswith("Use the skill rule-discovery on the task t9_example. Read lab/runs/t9_example/notes.md")
    assert agent.session("t9_example", tmp_path / "runs", [sys.executable, str(fake)]) == 0
    trace = next((tmp_path / "runs" / "t9_example").glob("agent-*.jsonl"))
    record = history.agent_run("t9_example", trace)
    assert record["status"] == "done" and record["cost"] == 0.5 and record["note"] == "t9: 10 / 10 exact"
    out = capsys.readouterr().out
    assert "t9: 10 / 10 exact" in out and "3 turns, 0.50 USD, session s-1" in out


def test_tasks_without_a_submission_function_are_refused_before_queueing():
    from neuronlab import score
    assert score.refusal("t0_commission") is None
    assert "no function in submission.py" in score.refusal("t2_projection_year")
    for action in ("score", "ablate", "freeze"):
        with pytest.raises(ValueError, match="no function in submission.py"):
            runner.plan(action, "t2_projection_year")
    assert runner.plan("score", "t0_commission")[0] == "Score"
