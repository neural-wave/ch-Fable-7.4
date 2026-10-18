"""View models of `lab serve`: what each screen shows, computed from the run artifacts.

Every function returns plain JSON data and reads files only: the pages never compute a score themselves. Exact
numbers are kept as text (`"0.98"`) and as [ok, n] pairs; percentages are formatted here, once.
"""
import ast
import datetime as dt
import json
import math
import re

from .. import freeze, labels, paths
from . import history, layout, runner as runner_module

TOP_CANDIDATES = 12
NOT_A_TASK = ("_jobs",)


def read_json(run, name):
    path = paths.RUNS / run / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def pct(pair):
    if not pair or not pair[1]:
        return "—"
    return f"{100 * pair[0] / pair[1]:.2f} %"


def took(started, ended):
    if not started:
        return "—"
    end = history.parse_time(ended) or dt.datetime.now()
    secs = int((end - history.parse_time(started)).total_seconds())
    if secs <= 0 and ended:
        return "—"  # a run rebuilt from one ledger line: no duration
    return f"{secs // 3600}:{secs // 60 % 60:02d}:{secs % 60:02d}" if secs >= 3600 else f"{secs // 60}:{secs % 60:02d}"


def when(text):
    """'Today 14:31', 'Yesterday 17:20' or '2026-10-15 09:02'."""
    t = history.parse_time(text)
    if t is None:
        return "Queued"
    days = (dt.date.today() - t.date()).days
    day = {0: "Today", 1: "Yesterday"}.get(days, t.date().isoformat())
    return f"{day} {t:%H:%M}"


def tasks():
    """Base tasks that have a run folder, plus the target files without one."""
    names = {r.split("~")[0] for r in history.run_folders()}
    return sorted(n for n in names if n not in NOT_A_TASK)


def pool_best(run, value=None):
    """(value, best candidate, pool info) of a run, None when it has no pool."""
    pool = read_json(run, "pool.json")
    if not pool or not pool.get("values"):
        return None
    value = value if value in pool["values"] else next(iter(pool["values"]))
    info = pool["values"][value]
    best = next(c for c in info["candidates"] if c["id"] == info["best"])
    return value, best, info


def submission_entry(task):
    """The last `lab score` of the submission for this task (a `code:` ledger entry), None if never scored."""
    entries = [e for e in history.ledger(task) if e["candidate"].startswith("code:")]
    return entries[-1] if entries else None


def frozen_state(task):
    """How the submission compares with the best candidate of the last pipeline run of the task."""
    score = submission_entry(task)
    found = pool_best(task)
    best = found[1]["score"] if found else None
    multi = len((read_json(task, "pool.json") or {}).get("values", {})) > 1
    if score is None:
        return {"label": "Not frozen yet", "holdout": best["holdout"] if best else None, "frozen": False}
    if best and not multi and best["holdout"][0] > score["holdout"][0]:
        return {"label": "Winner not frozen", "holdout": score["holdout"], "frozen": False,
                "better": best["holdout"]}
    return {"label": "Frozen in submission", "holdout": score["holdout"], "frozen": True}


def steps_of(record, runner=None):
    """The seven steps of a run record: from its events when it is a job, from its kind otherwise."""
    from . import runner as runner_module
    if record.get("events"):
        import pathlib
        events = runner_module.read_events(pathlib.Path(record["events"]))
        return runner_module.step_states(record["kind"], events, record["status"], record.get("commands"))
    if record.get("steps"):
        return record["steps"]
    return runner_module.step_states(record["kind"], [], record["status"])


def note_of(record):
    if record.get("note"):
        return record["note"]
    if record["status"] == "queued":
        return "Waiting in the queue"
    if record["status"] == "running":
        return "Running"
    if record["status"] in ("failed", "cancelled", "interrupted"):
        return {"failed": "Failed: see the log", "cancelled": "Cancelled", "interrupted": "The server stopped"}[
            record["status"]] if not record.get("error") else record["error"]
    best = record.get("best")
    if best:
        return best.get("origin") or best["candidate"]
    return ""


def run_row(record):
    best = record.get("best") or {}
    return {"id": record["id"], "run": record["run"], "task": record["task"], "kind": record["kind"],
            "status": record["status"], "started": when(record.get("started")), "took": took(record.get("started"),
                                                                                             record.get("ended")),
            "steps": [s["state"] for s in steps_of(record)], "disc": pct(best.get("discovery")),
            "hold": pct(best.get("holdout")), "hold_pair": best.get("holdout"), "note": note_of(record),
            "candidate": best.get("candidate"), "job": bool(record.get("events")), "commands": record.get("commands", []),
            "cost": record.get("cost")}


def runs_view(runner=None):
    """Runs page: every run, newest first, with the delta of holdout against the previous run of the same folder."""
    records = history.runs()
    rows = [run_row(r) for r in records]
    previous = {}
    for row in reversed(rows):  # oldest first
        key = (row["run"], row["kind"])
        if row["hold_pair"] and key in previous and previous[key][1] and row["hold_pair"][1]:
            delta = 100 * (row["hold_pair"][0] / row["hold_pair"][1] - previous[key][0] / previous[key][1])
            row["delta"] = f"{delta:+.2f}" if abs(delta) >= 0.005 else ""
        if row["hold_pair"]:
            previous[key] = row["hold_pair"]
    tiles = []
    for task in tasks():
        last = next((r for r in records if r["task"] == task), None)
        state = frozen_state(task)
        tiles.append({"id": task, "state": (last or {}).get("status", "never run"), "holdout": pct(state["holdout"]),
                      "frozen": state["label"]})
    return {"runs": rows, "tasks": tiles, "kinds": ["All", "Pipeline", "Step 5", "Score", "Ablation", "Agent"],
            "queue": [run_row(dict(j, status="queued")) for j in (runner.queued() if runner else [])]}


# --- one run ---------------------------------------------------------------------------------------------------

def leaves_of(candidate):
    if candidate.get("lookup"):
        return "lookup"
    return str(len(candidate.get("rules", [])))


def candidate_name(candidate):
    rounding = candidate.get("rounding", "ROUND_HALF_UP").replace("ROUND_", "").lower().replace("_", " ")
    relation = candidate["relation"]
    if candidate.get("lookup"):
        lk = candidate["lookup"]
        what = f"{lk['table']}.{lk['column']} looked up by {', '.join(lk['keys'].values())}"
    elif len(candidate.get("rules", [])) == 1:
        what = f"one constant {candidate['rules'][0]['then']}"
    else:
        what = f"{len(candidate.get('rules', []))} rules"
    op = {"ratio": "×", "diff": "+", "days": "+ days", "months": "+ months", "const": ""}[relation["kind"]]
    return f"{relation.get('input') or 'value'} {op} {what}" + (f", rounded {rounding}" if relation["kind"] == "ratio"
                                                               else "")


def residual_kinds(residuals):
    """Wrong rows of the winner by kind, for the bar list of the run page."""
    rows = []
    for pair, n in residuals.get("structure", {}).items():
        used, fits = pair.split(" -> ")
        rows.append({"kind": f"Another regime: uses {used}, the row fits {fits}",
                     "detail": "a condition is missing: the trees need a feature", "count": n, "tone": "ink",
                     "action": "trees"})
    listed = residuals.get("in_NREXCP", 0)
    noise = residuals.get("noise", 0)
    if listed:
        rows.append({"kind": "Typed by hand (listed in NREXCP)", "detail": "left out of the rules on purpose",
                     "count": listed, "tone": "muted", "action": "outliers"})
    if noise - listed:
        rows.append({"kind": "Noise", "detail": "no cluster centre reproduces the row in any rounding mode",
                     "count": noise - listed, "tone": "accent", "action": "suggest"})
    if residuals.get("ambiguous"):
        rows.append({"kind": "Ambiguous", "detail": "several centres reproduce the row", "count": residuals["ambiguous"],
                     "tone": "muted", "action": "clusters"})
    top = max((r["count"] for r in rows), default=1)
    for r in rows:
        r["width"] = f"{max(2, round(100 * r['count'] / top))}%"
    return sorted(rows, key=lambda r: -r["count"])


def proposals(task):
    """The last step-5 request of a task: proposals with the score before and after, rejected ones."""
    found = []
    for run in (f"{task}~llm", f"{task}~ablate"):
        folder = paths.RUNS / run / "llm"
        if folder.exists():
            found += [(p.name, run, p) for p in folder.glob("*.json")]
    if not found:
        return None
    name, run, path = max(found)
    log = json.loads(path.read_text(encoding="utf-8"))
    items = []
    for p in log.get("proposals", []):
        score = p.get("score") or {}
        items.append({"name": p["name"], "expr": p["expr"], "why": p.get("why", ""),
                      "before": score.get("before"), "after": score.get("after"), "outcome": score.get("outcome", "Kept")})
    for e in log.get("errors", []):
        items.append({"name": "", "expr": e, "why": "", "before": None, "after": None, "outcome": "Refused"})
    return {"run": run, "time": log.get("time"), "model": log.get("model"), "items": items,
            "before": log.get("before"), "after": log.get("after")}


def related(task, run):
    out = []
    for record in history.runs():
        if record["task"] == task and record["run"] != run or (record["run"] == run and record.get("best")):
            row = run_row(record)
            out.append({"run": record["run"], "what": f"{record['kind']} · {row['started']}", "score": row["hold"]})
        if len(out) >= 6:
            break
    return out


def run_detail(run, value=None):
    """Run page: scores, the seven steps, the candidates, the wrong rows, the language model, related runs."""
    task = run.split("~")[0]
    own = [r for r in history.runs() if r["run"] == run]
    record = next((r for r in own if r["kind"] == history.kind_of(run)), own[0] if own else None)
    found = pool_best(run, value)
    pool = read_json(run, "pool.json") or {"values": {}}
    out = {"run": run, "task": task, "kind": history.kind_of(run), "values": list(pool["values"]),
           "record": run_row(record) if record else None, "files": artifact_list(run),
           "frozen": frozen_state(task), "proposals": proposals(task), "related": related(task, run),
           "commands": {"run": f"lab run {task}", "suggest": f"lab suggest {task}", "score": f"lab score {task}"},
           "cannot": {"score": runner_module.score_refusal(task), "ablate": runner_module.ablate_refusal(task)}}
    out["steps"] = steps_from_files(run)
    if not found:
        out.update(value=None, scores=None, candidates=[], residuals=[])
        return out
    value, best, info = found
    res = (read_json(run, "residuals.json") or {"values": {}})["values"].get(value, {})
    ranked = sorted(info["candidates"], key=lambda c: (-c["score"]["holdout"][0], -c["score"]["discovery"][0]))
    refusal = freeze_refusal(run, best["id"])
    candidates = []
    for c in ranked[:TOP_CANDIDATES]:
        candidates.append({"id": c["id"], "winner": c["id"] == best["id"], "name": candidate_name(c),
                           "origin": c.get("origin", ""), "features": c["features"], "leaves": leaves_of(c),
                           "disc": pct(c["score"]["discovery"]), "hold": pct(c["score"]["holdout"]),
                           "tie": c["id"] in info.get("ties", []),
                           "freeze": refusal if c["id"] == best["id"] else freeze_refusal(run, c["id"])})
    wrong_disc = best["score"]["discovery"][1] - best["score"]["discovery"][0]
    wrong_hold = best["score"]["holdout"][1] - best["score"]["holdout"][0]
    out.update(value=value, winner=best["id"], freeze=refusal, pool_size=len(info["candidates"]),
               scores={"discovery": pct(best["score"]["discovery"]), "discovery_pair": best["score"]["discovery"],
                       "holdout": pct(best["score"]["holdout"]), "holdout_pair": best["score"]["holdout"],
                       "wrong": wrong_disc + wrong_hold, "wrong_disc": wrong_disc, "wrong_hold": wrong_hold,
                       "by_hand": res.get("in_NREXCP", 0)},
               candidates=candidates, residuals=residual_kinds(res))
    return out


def freeze_refusal(run, candidate_id):
    try:
        return freeze.refusal(run, candidate_id)
    except (OSError, StopIteration, KeyError, ValueError) as e:
        return f"cannot check the freeze: {e}"


STEP_FILES = (("profile.json", "frame.json"), ("clusters.json",), ("trees.json",), ("pool.json",), ("llm",),
              ("ledger.jsonl",), ("residuals.json", "report.md"))


def steps_from_files(run):
    """The seven steps of a run folder as its artifacts show them, with the last duration a job recorded for each."""
    from . import runner as runner_module
    import pathlib
    folder = paths.RUNS / run
    secs = {}
    for job in sorted(history.recorded().values(), key=lambda j: j.get("started") or ""):
        if job.get("run") == run and job.get("events"):
            for st in runner_module.step_states(job["kind"], runner_module.read_events(pathlib.Path(job["events"])),
                                                job["status"], job.get("commands")):
                if st["secs"] is not None:
                    secs[st["n"]] = st["secs"]
    steps = []
    for i, (name, files) in enumerate(zip(history.STEPS, STEP_FILES)):
        present = [f for f in files if (folder / f).exists()]
        steps.append({"n": i + 1, "name": name, "state": "done" if present else "skipped", "secs": secs.get(i + 1),
                      "files": [f for f in present if f != "llm"]})
    return steps


SHOWN_FILES = ("profile.json", "frame.json", "clusters.json", "histograms.json", "trees.json", "pool.json",
               "ledger.jsonl", "residuals.json", "outliers.json", "report.md", "score.md", "ablation.json", "notes.md")


def artifact_list(run):
    folder = paths.RUNS / run
    if not folder.exists():
        return []
    names = [n for n in SHOWN_FILES if (folder / n).exists()]
    names += sorted(p.name for p in folder.glob("agent-*.jsonl"))
    return names


def artifact_path(run, name):
    """Path of an artifact the page may open, None for anything else (no traversal, known names only)."""
    if run not in history.run_folders() or "/" in name or "\\" in name or name.startswith("."):
        return None
    if name not in SHOWN_FILES and not re.fullmatch(r"agent-\d{8}T\d{6}\.jsonl", name):
        return None
    path = paths.RUNS / run / name
    return path if path.exists() else None


# --- step 2: clusters ------------------------------------------------------------------------------------------

def clusters_view(run, value=None):
    data = read_json(run, "clusters.json")
    if not data or not data.get("values"):
        return {"run": run, "value": None, "values": [], "missing": "clusters.json"}
    value = value if value in data["values"] else next(iter(data["values"]))
    info = data["values"][value]
    rows = data["rows"]
    out = {"run": run, "task": run.split("~")[0], "value": value, "values": list(data["values"]), "rows": rows}
    if not info.get("relation"):
        out.update(note=info.get("note"), approximate=info.get("approximate"), relations=[], centers=[])
        return out
    assigned = info["assigned"]
    shapes = (read_json(run, "histograms.json") or {}).get(value) or []
    relations = [{"label": info["relation_name"], "verdict": f"{len(info['centers'])} clusters · "
                  f"{pct([info['noise'], rows])} noise · best", "best": True, "histogram": (shapes or [None])[0]}]
    for i, alt in enumerate(info.get("alternatives", [])):
        relations.append({"label": alt["relation"], "verdict": f"{alt['centers']} clusters · "
                          f"{pct([alt['noise'], rows])} noise · {alt['assigned']} rows reproduced", "best": False,
                          "histogram": shapes[i + 1] if i + 1 < len(shapes) else None,
                          "why": f"Reproduces {alt['assigned']} rows exactly, the best relation {assigned}."})
    centers = []
    for i, c in enumerate(info["centers"]):
        rounding = [m for m, n in c["modes"].items() if n == c["rows"]]
        centers.append({"id": chr(65 + i) if i < 26 else str(i), "center": c["center"], "rows": c["rows"],
                        "share": pct([c["rows"], rows]), "modes": c["modes"],
                        "formula": formula(info["relation"], c["center"]), "exact_modes": rounding})
    res = (read_json(run, "residuals.json") or {"values": {}})["values"].get(value, {})
    out.update(relations=relations, centers=centers, noise=info["noise"], ambiguous=info["ambiguous"],
               assigned=assigned, identities=info.get("identities", []),
               modes=["UP", "DOWN", "CEILING", "FLOOR", "HALF_UP", "HALF_DOWN", "HALF_EVEN"],
               noise_split={"listed": res.get("in_NREXCP"), "whole_units": res.get("whole_unit_deltas"),
                            "noise_of_winner": res.get("noise")},
               noise_examples=info.get("noise_examples", [])[:8])
    return out


def formula(relation, center):
    x = relation.get("input")
    return {"ratio": f"round({x} × {center})", "diff": f"{x} + {center}", "days": f"{x} + {center} days",
            "months": f"{x} + {center} months", "const": center}[relation["kind"]]


# --- step 3: trees ---------------------------------------------------------------------------------------------

def trees_view(run, value=None, index=0):
    data = read_json(run, "trees.json")
    if not data or not data.get("values"):
        return {"run": run, "value": None, "values": [], "missing": "trees.json"}
    value = value if value in data["values"] else next(iter(data["values"]))
    info = data["values"][value]
    out = {"run": run, "task": run.split("~")[0], "value": value, "values": list(data["values"])}
    sets = info.get("minimal_sets") or []
    if not sets:
        out.update(note=info.get("note") or "no optimal tree", sets=[])
        return out
    index = min(max(0, int(index)), len(sets) - 1)
    chosen = sets[index]
    centers = [c["center"] for c in ((read_json(run, "clusters.json") or {}).get("values", {}).get(value, {})
                                     .get("centers", []))]
    task = run.split("~")[0]
    relation = (read_json(run, "clusters.json") or {}).get("values", {}).get(value, {}).get("relation") or {}

    def leaf_words(c):
        return labels.constant(relation, c, task) if relation else c
    diagram = explain(layout.tree(chosen["tree"]), chosen["tree"], task, leaf_words)
    for n in diagram["nodes"]:
        if n["kind"] == "leaf":
            n["cluster"] = centers.index(n["label"]) if n["label"] in centers else None
    leaves = [{"id": n["id"], "path": " → ".join(path_text(chosen["tree"], n["id"])) + f" → {n['label']}",
               "say": f"When {labels.path(path_clauses(chosen['tree'], n['id']), task)}: {leaf_words(n['label'])}",
               "rows": n["rows"], "errors": n["errors"]} for n in diagram["nodes"] if n["kind"] == "leaf"]
    pool = read_json(run, "pool.json") or {"values": {}}
    cart = next((c for c in pool["values"].get(value, {}).get("candidates", []) if c["id"] == "C1"), None)
    conflicting = sum(sum(sorted(c["clusters"].values())[:-1]) for c in info.get("conflicts", []))
    out.update(rows=info["rows"], best=info.get("best"), sets=[{"features": s["features"], "errors": s["errors"],
                                                                 "leaves": s["leaves"]} for s in sets],
               index=index, chosen={"features": chosen["features"], "errors": chosen["errors"],
                                    "leaves": chosen["leaves"], "optimal_trees": chosen.get("optimal_trees"),
                                    "equivalents": chosen.get("equivalents", {})},
               diagram=diagram, leaves=leaves, centers=centers, conflicts=info.get("conflicts", []),
               conflicting_rows=conflicting,
               cart={"leaves": info["cart"]["leaves"], "errors": info["cart"]["errors"],
                     "holdout": pct(cart["score"]["holdout"]) if cart else "—"} if info.get("cart") else None,
               regions=regions(chosen["tree"], chosen["features"], centers, task),
               screened=info.get("screened", []))
    return out


def path_text(root, node_id):
    """Conditions from the root to a node, e.g. ['RK_TARKEY[5] = 2', 'PH_STATE ≠ 10']."""
    node, parts = root, []
    for branch in node_id:
        feature, value = node["split"]
        parts.append(f"{feature} {'=' if branch == 'y' else '≠'} {value}")
        node = node["yes"] if branch == "y" else node["no"]
    return parts


def route(root, row):
    """Id of the leaf a row of feature values reaches (values compared as text, like the pool does)."""
    node, ident = root, ""
    while "leaf" not in node:
        feature, value = node["split"]
        yes = str(row.get(feature)) == str(value)
        ident += "y" if yes else "n"
        node = node["yes"] if yes else node["no"]
    return ident, node["leaf"]


def regions(root, features, centers, task=None):
    """The tree as a grid when it uses exactly two features: one cell per pair of values it tests."""
    if len(features) != 2:
        return None
    values = {f: [] for f in features}

    def collect(node):
        if "leaf" not in node:
            feature, value = node["split"]
            if value not in values[feature]:
                values[feature].append(value)
            collect(node["yes"])
            collect(node["no"])
    collect(root)
    a, b = features
    rows_ = values[a] + ["other"]
    cols = values[b] + ["other"]
    cells = []
    for va in rows_:
        for vb in cols:
            leaf_id, label = route(root, {a: va if va != "other" else "\0", b: vb if vb != "other" else "\0"})
            cells.append({"row": va, "col": vb, "leaf": leaf_id, "label": label,
                          "cluster": centers.index(label) if label in centers else None})
    fa, fb = labels.feature(a, task), labels.feature(b, task)
    return {"rows_feature": a, "cols_feature": b, "rows": rows_, "cols": cols, "cells": cells,
            "rows_subject": fa.subject, "cols_subject": fb.subject,
            "rows_say": {v: fa.value(v) for v in values[a]}, "cols_say": {v: fb.value(v) for v in values[b]}}


def node_at(root, node_id):
    node = root
    for branch in node_id:
        node = node["yes"] if branch == "y" else node["no"]
    return node


def path_clauses(root, node_id):
    """Conditions from the root to a node as [feature, op, value]; a passed chain test holds all its conditions."""
    node, clauses = root, []
    for branch in node_id:
        if node.get("clauses"):
            clauses += node["clauses"] if branch == "y" else []
        else:
            feature, value = node["split"]
            clauses.append([feature, "=" if branch == "y" else "!=", value])
        node = node["yes"] if branch == "y" else node["no"]
    return clauses


def explain(diagram, root, task, leaf_words):
    """Plain words on the nodes of a laid-out tree: a question for each test, a phrase for each leaf."""
    for n in diagram["nodes"]:
        if n["kind"] == "split":
            node = node_at(root, n["id"])
            if node.get("clauses"):
                tests = "; ".join(labels.condition(c, task) for c in node["clauses"])
                n["say"], n["known"] = f"Does all of this hold: {tests}?", True
            else:
                f = labels.feature(n["feature"], task)
                n["say"], n["known"] = f.question(n["value"]), f.known and f.explained(n["value"])
        elif n["kind"] == "leaf":
            n["say"] = leaf_words(n["label"])
    return diagram


# --- control flow ----------------------------------------------------------------------------------------------

def rules_tree(rules):
    """The decision tree behind leaf rules in depth-first order (yes before no), None if they are not a tree."""
    if len(rules) == 1 and not rules[0]["when"]:
        return {"leaf": str(rules[0]["then"])}
    if not rules or any(not r["when"] for r in rules):
        return None
    feature, op, value = rules[0]["when"][0]
    if op != "=":
        return None
    yes = [dict(r, when=r["when"][1:]) for r in rules if r["when"][0] == [feature, "=", value]]
    no = [dict(r, when=r["when"][1:]) for r in rules if r["when"][0] == [feature, "!=", value]]
    if len(yes) + len(no) != len(rules) or not yes or not no:
        return None
    left, right = rules_tree(yes), rules_tree(no)
    if left is None or right is None:
        return None
    return {"split": [feature, value], "yes": left, "no": right}


def chain_tree(rules):
    """If-elif chain of arbitrary rules as a tree of all-conditions tests."""
    if not rules:
        return {"leaf": "none"}
    head, rest = rules[0], rules[1:]
    if not head["when"]:
        return {"leaf": str(head["then"])}
    text = " and ".join(f"{c} {'=' if op == '=' else '≠'} {v}" for c, op, v in head["when"])
    return {"split": [text, "true"], "yes": {"leaf": str(head["then"])}, "no": chain_tree(rest), "chain": True,
            "clauses": head["when"]}


def candidate_of(run, value, candidate_id):
    pool = read_json(run, "pool.json") or {"values": {}}
    if not pool["values"]:
        return None, None
    value = value if value in pool["values"] else next(iter(pool["values"]))
    info = pool["values"][value]
    wanted = candidate_id or info["best"]
    return value, next((c for c in info["candidates"] if c["id"] == wanted), None)


def compute_text(candidate):
    relation, rounding = candidate["relation"], candidate.get("rounding", "ROUND_HALF_UP")
    x = relation.get("input")
    return {"ratio": f"value = round_{rounding.replace('ROUND_', '').lower()}({x} × c)",
            "diff": f"value = {x} + c", "days": f"value = {x} + c days", "months": f"value = {x} + c months",
            "const": "value = c"}[relation["kind"]]


def features_used(candidate):
    used = list(candidate["features"]) + ([candidate["relation"]["input"]] if candidate["relation"].get("input") else [])
    return list(dict.fromkeys(used))


def flow_view(run, value=None, candidate_id=None):
    """Control flow page: the graph of the candidate, the code freeze writes for it, presets of rows to replay."""
    value, candidate = candidate_of(run, value, candidate_id)
    if candidate is None:
        return {"run": run, "missing": "pool.json", "value": None}
    meta = read_json(run, "frame.json") or {}
    if candidate.get("lookup"):
        lk = candidate["lookup"]
        root = {"leaf": f"{lk['table']}.{lk['column']}[{', '.join(lk['keys'].values())}]"}
        kind = "lookup"
    else:
        root = rules_tree(candidate["rules"])
        kind = "tree" if root else "chain"
        root = root or chain_tree(candidate["rules"])
    used = features_used(candidate)
    task = run.split("~")[0]
    subjects = {f: labels.feature(f, task).subject for f in used}
    diagram = layout.flow(root, "Inputs: " + ", ".join(used), compute_text(candidate), value)
    lookup = labels.lookup_words(candidate, task) if candidate.get("lookup") else None
    explain(diagram, root, task, lambda c: lookup or labels.constant(candidate["relation"], c, task))
    fixed = {"in": "Reads the " + "; the ".join(subjects.values()), "compute": labels.computation(candidate, task),
             "result": f"the {labels.target_meaning(task, value) or labels.words(value)}"}
    for n in diagram["nodes"]:
        n["say"] = fixed.get(n["id"], n.get("say"))
    source, lines, reason = code_of(run, candidate)
    values = list((read_json(run, "pool.json") or {}).get("values", {}))
    out = {"run": run, "task": run.split("~")[0], "value": value, "values": values, "candidate": candidate["id"],
           "kind": kind,
           "features": used, "subjects": subjects, "diagram": diagram, "code": lines, "freeze": reason,
           "source": source,
           "presets": presets(run, value, candidate, meta), "relation": candidate["relation"],
           "replay": (paths.RUNS / run / "frame.parquet").exists(),
           "rounding": candidate.get("rounding"), "name": candidate_name(candidate),
           "score": {k: pct(candidate["score"][k]) for k in ("discovery", "holdout", "total")}}
    if not source:
        out["hand_written"] = hand_written(run.split("~")[0])
    return out


def code_of(run, candidate):
    """(source, lines with the leaves they belong to, refusal) of the code `freeze` would write for the candidate."""
    reason = freeze_refusal(run, candidate["id"])
    try:
        source, _ = freeze.render(run, candidate)
    except Exception as e:  # noqa: BLE001 - any template failure is shown, not raised
        return None, [], reason or f"no code template: {e}"
    rules = candidate.get("rules") or []
    lines, rule = [], -1
    for i, text in enumerate(source.splitlines()):
        stripped = text.strip()
        tag = None
        if stripped.startswith(("if ", "elif ")) and stripped.endswith(":") and "rate" not in stripped and rules:
            rule += 1
            tag = {"rule": rule, "test": True}
        elif stripped.startswith("rate = Decimal(") and rule >= 0:
            tag = {"rule": rule, "test": False}
        lines.append({"n": i + 1, "src": text, **(tag or {})})
    return source, lines, reason


def hand_written(task):
    """Source of the task function in the submission, read with `ast` (not imported), for tasks freeze cannot write."""
    for path in [paths.SUBMISSION / "submission.py", *sorted((paths.SUBMISSION / "tasks").glob("*.py"))]:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name == task:
                body = ast.get_source_segment(text, node) or ""
                return {"file": str(path.relative_to(paths.REPO)).replace("\\", "/"), "source": body}
    return None


def presets(run, value, candidate, meta):
    """Rows to replay: an example of each leaf, a wrong row and a row listed in NREXCP when there is one."""
    found = []
    pool = read_json(run, "pool.json") or {"values": {}}
    for card in pool["values"].get(value, {}).get("cards", [])[:8]:
        for key in card.get("examples", [])[:1]:
            found.append({"key": key, "label": f"{' · '.join(map(str, key))}  (leaf {card['id']}, {card['then']['center']})"})
    res = (read_json(run, "residuals.json") or {"values": {}})["values"].get(value, {})
    for row in res.get("rows", [])[:40]:
        if row.get("in_NREXCP"):
            found.append({"key": row["key"], "label": f"{' · '.join(map(str, row['key']))}  (wrong, listed in NREXCP)"})
            break
    for row in res.get("rows", [])[:1]:
        found.append({"key": row["key"], "label": f"{' · '.join(map(str, row['key']))}  (wrong: {row['class']})"})
    unique = {json.dumps(p["key"]): p for p in found}
    return list(unique.values())


def flow_eval(run, value, candidate_id, key=None, inputs=None):
    """Replay one row through a candidate: feature values, the leaf it reaches, the constant, the value, the target.

    The row is the frame row of `key`; `inputs` overrides some of its columns (custom values). The value is
    computed by `evaluate.predicted`, the exact interpreter of the pool: the page does no arithmetic.
    """
    import polars as pl
    from .. import evaluate, frame as frames
    value, candidate = candidate_of(run, value, candidate_id)
    if not (paths.RUNS / run / "frame.parquet").exists():
        raise ValueError(f"the frame of {run} is not on this machine (parquet files are not versioned): run steps 1 "
                         f"and 2 of the pipeline to replay rows")
    df, meta = frames.load(run)
    keys = meta["keys"]
    if key is None:
        raise ValueError("a key of the target is needed: the row it gives is the starting point of custom values")
    cond = pl.all_horizontal([pl.col(k).cast(pl.String) == str(v) for k, v in zip(keys, key)])
    row = df.filter(cond).head(1)
    if row.height == 0:
        raise ValueError(f"no frame row for the key {key}")
    target = row[value][0]
    for name, text in (inputs or {}).items():
        if name not in row.columns:
            raise ValueError(f"unknown column {name}")
        row = row.with_columns(parse_value(text, row[name].dtype).alias(name))
    used = features_used(candidate)
    shown = row.select(pl.col(f).cast(pl.String) for f in used if f in row.columns).row(0, named=True)
    constant = evaluate.constants(row, candidate)[0]
    computed = evaluate.predicted(row, candidate, value)[0]
    rule = None
    if candidate.get("lookup"):
        leaf, steps = "", [f"look up {candidate['lookup']['table']}.{candidate['lookup']['column']} → {constant}"]
    else:
        rule = matched_rule(candidate, row)
        tree = rules_tree(candidate["rules"])
        if tree:
            leaf, steps = walk(tree, shown)
        else:  # an if/elif chain: the first rule that holds
            n = len(candidate["rules"]) if rule is None else rule
            leaf = "n" * n + ("y" if rule is not None else "")
            steps = [f"rule {i + 1} holds?  {'yes' if i == rule else 'no'}" for i in range(n + (rule is not None))]
            steps.append(f"c = {none_text(constant)}")
    say = trace_words(candidate, run.split("~")[0], shown, leaf, none_text(constant), none_text(computed))
    return {"key": key, "inputs": shown, "leaf": leaf, "path": layout.path_to(leaf), "constant": none_text(constant),
            "say": say,
            "computed": none_text(computed), "target": None if inputs else none_text(target),
            "equal": None if inputs else none_text(target) == none_text(computed),
            "trace": [f"read {', '.join(f'{k} = {v}' for k, v in shown.items())}", *steps,
                      f"{compute_text(candidate)} with c = {none_text(constant)} → {none_text(computed)}"],
            "rule": rule}


def trace_words(candidate, task, shown, leaf, constant, computed):
    """The replay of a row in plain words: what it reads, the answer to each test, the constant, the result."""
    feats = {name: labels.feature(name, task) for name in shown}
    lines = ["Reads " + "; ".join(f"the {f.subject}: {f.value(shown[name])}" for name, f in feats.items())]
    if candidate.get("lookup"):
        lines.append(f"Looks up {labels.lookup_words(candidate, task)}: {labels.number(constant)}")
    else:
        node = rules_tree(candidate["rules"]) or chain_tree(candidate["rules"])
        for branch in leaf:
            answer = "Yes" if branch == "y" else "No"
            if node.get("clauses"):
                tests = "; ".join(labels.condition(c, task) for c in node["clauses"])
                lines.append(f"Does all of this hold: {tests}? {answer}.")
            else:
                lines.append(f"{labels.feature(node['split'][0], task).question(node['split'][1])} {answer}.")
            node = node["yes"] if branch == "y" else node["no"]
        lines.append(f"So the constant is {labels.number(constant)}: "
                     f"{labels.constant(candidate['relation'], constant, task)}.")
    lines.append(f"{labels.computation(candidate, task)} = {computed}")
    return lines


def walk(root, row):
    node, ident, steps = root, "", []
    while "leaf" not in node:
        feature, value = node["split"]
        yes = str(row.get(feature)) == str(value)
        steps.append(f"{feature} = {value}?  {row.get(feature)} → {'yes' if yes else 'no'}")
        ident += "y" if yes else "n"
        node = node["yes"] if yes else node["no"]
    steps.append(f"c = {node['leaf']}")
    return ident, steps


def matched_rule(candidate, row):
    """Index of the first rule whose conditions hold on the row (the if/elif chain of the code), None if none."""
    import polars as pl
    from .. import evaluate
    for i, rule in enumerate(candidate.get("rules") or []):
        cond = pl.all_horizontal([evaluate.condition(c) for c in rule["when"]]) if rule["when"] else pl.lit(True)
        if row.select(cond.alias("ok"))["ok"][0]:
            return i
    return None


def parse_value(text, dtype):
    import polars as pl
    series = pl.Series([str(text).strip()])
    if dtype == pl.Date:
        return series.str.to_date("%Y-%m-%d")
    if isinstance(dtype, pl.Decimal):
        return series.cast(pl.Decimal(38, dtype.scale))
    return series.cast(dtype)


def none_text(v):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    return str(v)


# --- a job in progress -----------------------------------------------------------------------------------------

LOG_LINES = 300


def job_view(job_id, runner=None):
    """Live page of a job: steps with progress, the log, the agent's timeline, the files written so far."""
    import pathlib
    from . import runner as runner_module
    job = history.recorded().get(job_id)
    if job is None:
        raise ValueError(f"unknown job {job_id}")
    events = runner_module.read_events(pathlib.Path(job["events"]))
    steps = runner_module.step_states(job["kind"], events, job["status"], job.get("commands"))
    log_path = pathlib.Path(job["log"])
    log = log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-LOG_LINES:] if log_path.exists() else []
    running = next((s for s in steps if s["state"] == "running"), None)
    started = history.parse_time(job.get("started"))
    written = []
    folder = paths.RUNS / job["run"]
    if started and folder.exists():
        written = sorted(p.name for p in folder.iterdir() if p.is_file()
                         and dt.datetime.fromtimestamp(p.stat().st_mtime) >= started - dt.timedelta(seconds=1))
    queue = [{"id": j["id"], "task": j["task"], "kind": j["kind"]} for j in (runner.queued() if runner else [])]
    return {"job": dict(job, started_text=when(job.get("started")), took=took(job.get("started"), job.get("ended"))),
            "steps": steps, "running": running, "progress": (running or {}).get("progress"), "log": log,
            "written": written, "queue": queue, "agent": agent_timeline(job) if job["kind"] == "Agent" else None}


def agent_timeline(job):
    """The newest Claude Code trace of the job's task: what the agent did, one line per tool call."""
    folder = paths.RUNS / job["run"]
    traces = sorted(folder.glob("agent-*.jsonl")) if folder.exists() else []
    started = history.parse_time(job.get("started"))
    traces = [t for t in traces if started is None or dt.datetime.fromtimestamp(t.stat().st_mtime) >= started]
    if not traces:
        return {"trace": None, "items": []}
    trace = traces[-1]
    items = []
    for line in trace.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        for block in (event.get("message") or {}).get("content") or []:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                items.append({"tool": block.get("name"), "what": tool_summary(block.get("input") or {})})
            elif isinstance(block, dict) and block.get("type") == "text" and event.get("type") == "assistant":
                text = history.last_line(block.get("text"), 140)
                if text:
                    items.append({"tool": "says", "what": text})
        if event.get("type") == "result":
            items.append({"tool": "result", "what": history.last_line(event.get("result"), 200)})
    return {"trace": trace.name, "items": items[-30:], "total": len(items)}


def tool_summary(arguments):
    for key in ("command", "file_path", "pattern", "description", "prompt", "skill"):
        if arguments.get(key):
            return str(arguments[key]).splitlines()[0][:140]
    return json.dumps(arguments)[:140]


# --- tasks and their definitions -------------------------------------------------------------------------------

def tasks_view():
    """Tasks page: every task with a target file, a run folder or a definition."""
    from .. import store, taskdef
    from ..store import scoring
    defined = {d["id"]: d for d in taskdef.all_definitions()}
    targets = set(store.target_names()) if paths.TARGETS.exists() else set()
    run = set(tasks())
    rows = []
    for name in sorted(targets | run | set(defined)):
        state = frozen_state(name) if name in run else {"label": "Never run", "holdout": None}
        rows.append({"id": name, "title": (defined.get(name) or {}).get("title", ""), "defined": name in defined,
                     "target": name in targets, "scored": name in scoring.TASKS, "frozen": state["label"],
                     "holdout": pct(state.get("holdout")), "run": name in run})
    return {"tasks": rows}


def task_definition(task):
    """The saved definition, else one drafted from the artifacts of the task, else an empty one."""
    from .. import taskdef
    found = taskdef.find(task)
    if found:
        return {"definition": found, "saved": True}
    if (paths.RUNS / task / "frame.json").exists():
        return {"definition": taskdef.init(task), "saved": False, "drafted": True}
    return {"definition": taskdef.empty("" if task == "new" else task), "saved": False}


def settings():
    import os
    import shutil
    return {"legacy": str(paths.LEGACY), "targets": str(paths.TARGETS), "claude": bool(shutil.which("claude")),
            "model": os.environ.get("LLM_MODEL", ""), "workspace": paths.REPO.name}


def dsl_check(task, expr):
    """Parse a feature of the DSL on the task's frame columns (syntax only before step 1 has run)."""
    from .. import dsl
    meta = read_json(task, "frame.json") if task and task in history.run_folders() else None
    columns = list(meta["lineage"]) if meta else None
    try:
        dsl.parse(expr, columns or [], columns or [])
    except dsl.Invalid as e:
        unknown = str(e).startswith("unknown column") or "not versioned" in str(e)
        if columns is None and unknown:
            return {"ok": True, "level": "info", "message": f"{e}: checked again on the frame of step 1"}
        return {"ok": False, "level": "error", "message": str(e)}
    return {"ok": True, "level": "ok", "message": "valid DSL"}


def upload(files):
    """Legacy files sent by the page ({name: base64}) become the legacy folder of the lab."""
    import base64
    from . import legacy
    folder, notes = legacy.receive({name: base64.b64decode(data) for name, data in files.items()})
    return dict(legacy.switch(str(folder)), notes=notes)


def target_preview(definition):
    """Target file of a definition: its columns matched to the output, rows, policies, first values."""
    import polars as pl
    from .. import taskdef
    path = taskdef.target_file(definition)
    if path is None or not path.exists():
        return {"exists": False, "path": str(path) if path else ""}
    df = pl.read_csv(path, infer_schema=False, n_rows=1000)
    task = definition.get("task", {})
    keys = [k["name"] for k in task.get("keys", [])]
    values = [v["name"] for v in task.get("values", [])]
    inputs = (definition.get("examples", {}).get("target_file") or {}).get("inputs", [])
    mapping = []
    for c in df.columns:
        part = "key" if c in keys else "value" if c in values else "input" if c in inputs else "unused"
        present = df[c].drop_nulls()
        mapping.append({"file": c, "part": part, "to": f"{part} {c}" if part != "unused" else "not used",
                        "example": str(present[0]) if present.len() else ""})
    policy = keys[0] if keys and keys[0] in df.columns else df.columns[0]
    column = pl.read_csv(path, columns=[policy], infer_schema=False)[policy]
    return {"exists": True, "path": str(path), "columns": mapping, "rows": column.len(),
            "policies": column.n_unique(), "missing": [c for c in keys + values if c not in df.columns],
            "sampled": column.len() > 1_000_000}


def pair_resolve(definition, key):
    """A hand pair's key: is it in the target file, how many legacy rows its policy has, is it listed in NREXCP."""
    import polars as pl
    from .. import store, taskdef
    keys = [k["name"] for k in definition.get("task", {}).get("keys", [])]
    policy = str(key.get(keys[0], "")) if keys else ""
    tables = (definition.get("task", {}).get("scope") or {}).get("tables") or []
    joined = []
    for t in tables[:8]:
        df = store.load(t)
        column = next((c for c in df.columns if c.endswith("_POLNR")), None)
        if column:
            joined.append({"table": t, "rows": df.filter(pl.col(column) == policy).height})
    path = taskdef.target_file(definition)
    in_target = False
    if path and path.exists() and keys:
        target = pl.read_csv(path, infer_schema=False, columns=keys)
        cond = pl.all_horizontal([pl.col(k) == str(key.get(k, "")) for k in keys])
        in_target = target.filter(cond).height > 0
    listed = False
    if "NREXCP" in store.tables():
        listed = store.load("NREXCP").filter(pl.col("EX_POLNR") == policy).height > 0
    return {"joined": joined, "in_target": in_target, "listed": listed}
