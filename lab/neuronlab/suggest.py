"""Step 5 in batch (`lab suggest`): one request to the open-weights model, a constrained answer, an exact score.

The model reads report.md and the feature vocabulary (dsl.py) and answers with at most 3 features in JSON. The
harness validates them (known primitives, existing columns, at most two levels), retries once with the
validation errors, adds the valid ones to the frame, reruns steps 3, 4 and 7 and compares the best exact score
before and after. Prompt, raw answer and outcome are kept in `lab/runs/<run>/llm/`. With `--ablate GLOB` the
frame first loses the matching columns: the acceptance test of this step on t0.
"""
import datetime as dt
import fnmatch
import hashlib
import json
import re
import shutil

import polars as pl

from . import dsl, frame as frames, iterate, llm, paths, pool, report, tree

SYSTEM = "You propose features for a decision tree. You answer only with JSON."
COPIED = ("profile.json", "clusters.json", "labels.parquet")


def variant(task, ablate):
    """Run folder `<task>~llm` (or `~ablate`) with a copy of the task artifacts and, if asked, fewer columns."""
    run = f"{task}~{'ablate' if ablate else 'llm'}"
    source, folder = paths.run_dir(task), paths.run_dir(run)
    for name in COPIED:
        shutil.copy(source / name, folder / name)
    df, meta = frames.load(task)
    if ablate:
        protected = set(meta["keys"]) | set(meta["values"])
        dropped = [c for c in df.columns if fnmatch.fnmatch(c, ablate) and c not in protected]
        df = df.drop(dropped)
        meta = dict(meta, lineage={k: v for k, v in meta["lineage"].items() if k not in dropped}, ablated=dropped)
    df.write_parquet(folder / "frame.parquet")
    (folder / "frame.json").write_text(json.dumps(meta, indent=1, default=str))
    return run


def rerun(run):
    tree.run(run)
    pool.run(run)
    iterate.run(run)
    return report.build(run)


def best_scores(run):
    """{value: (id of the winner, exact rows)} for every value of the run."""
    data = json.loads((paths.run_dir(run) / "pool.json").read_text())
    found = {}
    for value, info in data["values"].items():
        best = next(c for c in info["candidates"] if c["id"] == info["best"])
        found[value] = best["id"], best["score"]["total"][0]
    return found


def best_score(run):
    return next(iter(best_scores(run).values()))


def per_value(before, after):
    """The change of every value, when a task has more than one (a feature may help only a later value)."""
    if len(before) < 2:
        return ""
    return "; per value: " + ", ".join(f"{v} {before[v][1]} -> {after.get(v, ('', '?'))[1]}" for v in before)


def prompt_for(run, df, full, full_meta, text):
    versioned = sorted({c.split("@")[0] for c in full.columns if "@" in c})
    columns = "\n".join(f"- {c}: {df[c].dtype}" for c in df.columns if not c.endswith("_RAW"))
    template = (paths.REPO / "lab" / "neuronlab" / "prompts" / "suggest.md").read_text()
    return template.format(primitives=dsl.vocabulary(), columns=columns, anchors=", ".join(full_meta["anchors"]),
                           versioned=", ".join(versioned), report=text)


def extract_json(text):
    """The JSON list in a model answer (inside ``` fences or bare)."""
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    body = fenced.group(1) if fenced else text[text.find("["): text.rfind("]") + 1]
    return json.loads(body)


def validate(answer, df, full):
    """(valid proposals with parsed trees, error messages)."""
    good, errors = [], []
    try:
        items = extract_json(answer)
    except (ValueError, json.JSONDecodeError) as e:
        return [], [f"the answer is not a JSON list: {e}"]
    for item in items[:3] if isinstance(items, list) else []:
        try:
            name = re.sub(r"[^A-Za-z0-9_]", "_", str(item["name"]))[:40]
            node = dsl.parse(str(item["expr"]), df.columns, full.columns)
            good.append({"name": name, "expr": str(item["expr"]), "why": item.get("why", ""), "node": node})
        except (KeyError, TypeError) as e:
            errors.append(f"{item}: missing field {e}")
        except dsl.Invalid as e:
            errors.append(f"{item.get('expr')}: {e}")
    return good, errors


def add_feature(task, name, expr):
    """One feature written by hand (or by the agent in OpenCode), same validation and scoring as `suggest`."""
    run = f"{task}~llm"
    if not (paths.run_dir(run) / "frame.parquet").exists():
        variant(task, None)
        rerun(run)
    before, before_all = best_score(run), best_scores(run)
    df, meta = frames.load(run)
    full, full_meta = frames.load(task)
    node = dsl.parse(expr, df.columns, full.columns)
    df = df.with_columns(dsl.evaluate(node, df, full).alias(name))
    meta["lineage"][name] = dsl.lineage_of(node, full_meta)
    df.write_parquet(paths.run_dir(run) / "frame.parquet")
    (paths.run_dir(run) / "frame.json").write_text(json.dumps(meta, indent=1, default=str))
    rerun(run)
    after = best_score(run)
    return (f"{name} = {expr}: best before {before[0]} {before[1]}, after {after[0]} {after[1]} rows exact ({run})"
            + per_value(before_all, best_scores(run)))


def suggest(task, ablate=None, dry_run=False):
    run = variant(task, ablate)
    text = rerun(run)
    before, before_all = best_score(run), best_scores(run)
    df, meta = frames.load(run)
    full, full_meta = frames.load(task)
    prompt = prompt_for(run, df, full, full_meta, text)
    if dry_run:
        return prompt
    answers = [llm.complete(prompt, system=SYSTEM)]
    proposals, errors = validate(answers[0], df, full)
    if not proposals:
        retry = prompt + "\n\nYour previous answer was rejected:\n" + "\n".join(errors) + "\nAnswer again, only JSON."
        answers.append(llm.complete(retry, system=SYSTEM))
        proposals, errors = validate(answers[-1], df, full)
    for p in proposals:
        df = df.with_columns(dsl.evaluate(p["node"], df, full).alias(p["name"]))
        meta["lineage"][p["name"]] = dsl.lineage_of(p["node"], full_meta)
    if proposals:
        df.write_parquet(paths.run_dir(run) / "frame.parquet")
        (paths.run_dir(run) / "frame.json").write_text(json.dumps(meta, indent=1, default=str))
        rerun(run)
    after = best_score(run)
    log = {"time": dt.datetime.now().isoformat(timespec="seconds"), "model": llm.settings()[3],
           "prompt_sha": hashlib.sha1(prompt.encode()).hexdigest()[:12], "answers": answers,
           "proposals": [{k: v for k, v in p.items() if k != "node"} for p in proposals], "errors": errors,
           "before": before, "after": after}
    folder = paths.run_dir(run) / "llm"
    folder.mkdir(exist_ok=True)
    (folder / f"{log['time'].replace(':', '')}.json").write_text(json.dumps(log, indent=1, default=str))
    lines = [f"model {log['model']}: {len(proposals)} valid proposals, {len(errors)} rejected"]
    lines += [f"  + {p['name']} = {p['expr']}  ({p['why']})" for p in log["proposals"]]
    lines += [f"  - {e}" for e in errors]
    lines.append(f"best before: {before[0]} {before[1]} rows exact; after: {after[0]} {after[1]} rows exact"
                 + per_value(before_all, best_scores(run)))
    return "\n".join(lines)
