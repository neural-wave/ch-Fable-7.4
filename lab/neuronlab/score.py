"""`lab score`: the exact score of a function written in submission.py, and where it is wrong.

This is the step of the loop where the coding agent (or a person) turns the partial rules of the pool into code.
The function runs as `check.py` runs it, behind a firewall (no target file may be opened), and every target row is
compared with the semantics of `scoring.accuracy`. The rows it gets wrong go back into steps 2 and 3. Each value
column gets one label per row:
- `ok` or `missing`;
- the difference target - computed (`+2 days`, `+60.00`) or the ratio target / computed (`x0.67`), whichever is
  found in more policies, when it is found in at least MIN_POLICIES policies: a wrong rate gives a different
  difference on every policy but the same ratio;
- `noise` otherwise: a candidate manual correction, left out of the trees.
The optimal trees over the frame features then say under which conditions the function is wrong. The target's own
dates are expanded into calendar features (weekday, day, month, month end), and more features can be given in the
DSL of step 5.
"""
import builtins
import collections
import contextlib
import datetime as dt
import hashlib
import importlib.util
import inspect
import io
import json
import os
import pathlib
import sys
import time
from decimal import Decimal

import polars as pl

from . import dsl, evaluate, frame as frames, iterate, paths, store, tree
from .store import scoring

MIN_POLICIES = 3
EXPANSIONS = ("weekday", "day", "month", "month_end")
SHOWN = 8


def load_submission(folder=paths.SUBMISSION):
    """The submission module, loaded like check.py loads it: fresh, with its folder first on sys.path."""
    sys.path.insert(0, str(folder))
    helpers = {path.stem for path in pathlib.Path(folder).glob("*.py")}
    helpers |= {path.parent.name for path in pathlib.Path(folder).glob("*/__init__.py")}
    for name in [name for name in sys.modules if name.split(".")[0] in helpers]:
        sys.modules.pop(name)  # a helper module or package loaded from another folder must not be reused
    spec = importlib.util.spec_from_file_location("submission", pathlib.Path(folder) / "submission.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@contextlib.contextmanager
def firewall():
    """While a task function runs, opening a file of the targets folder raises PermissionError."""
    targets, real = str(paths.TARGETS.resolve()), builtins.open

    def guarded(file, *args, **kwargs):
        if isinstance(file, (str, os.PathLike)) and str(pathlib.Path(file).resolve()).startswith(targets):
            raise PermissionError(f"task functions may not read target files: {file}")
        return real(file, *args, **kwargs)

    builtins.open = io.open = guarded
    try:
        yield
    finally:
        builtins.open = io.open = real


def label(target, computed):
    """ok, missing, or the difference target - computed: whole days for dates, the amount otherwise."""
    if computed is None:
        return "missing"
    if target == computed:
        return "ok"
    if isinstance(target, dt.date):
        return f"{(target - computed).days:+d} days"
    if isinstance(target, Decimal):
        return f"{target - computed:+}"
    return "different"


def ratio(target, computed):
    """Ratio of two amounts with two decimals, e.g. x0.67; the rounding to the cent blurs more decimals."""
    if isinstance(target, Decimal) and isinstance(computed, Decimal) and computed:
        return f"x{target / computed:.2f}"
    return None


def column_labels(rows):
    """Labels of one value column from (policy, target, computed) rows."""
    deltas = [label(t, c) for _, t, c in rows]
    ratios = [ratio(t, c) if d not in ("ok", "missing") else None for (_, t, c), d in zip(rows, deltas)]
    policies = collections.defaultdict(set)
    for (policy, _, _), d, r in zip(rows, deltas, ratios):
        policies[d].add(policy)
        if r:
            policies[r].add(policy)
    labels = []
    for d, r in zip(deltas, ratios):
        best = d if d in ("ok", "missing") else max(filter(None, (d, r)), key=lambda x: len(policies[x]))
        labels.append(best if best in ("ok", "missing") or len(policies[best]) >= MIN_POLICIES else "noise")
    return labels


def compare(task, targets, predictions):
    """{value column: labels in the order of `targets`}."""
    _, values = store.target_columns(task)
    out = {}
    for i, value in enumerate(values):
        def part(v):
            return v if v is None or len(values) == 1 else v[i]
        out[value] = column_labels([(k[0] if isinstance(k, tuple) else k, part(t), part(predictions.get(k)))
                                    for k, t in targets.items()])
    return out


def difference(target, computed):
    """target - computed as a number: whole days for dates, currency units for amounts, None if not comparable."""
    if computed is None or target is None:
        return None
    if isinstance(target, dt.date):
        return float((target - computed).days)
    if isinstance(target, Decimal):
        return float(target - computed)
    return None


def differences(task, targets, predictions, keys, dtypes):
    """One row per target row: the keys and, per value column, the target, the computed value and their difference.

    The values are kept as text, so that they stay exact; the difference is a float, for the charts of `lab viz`.
    """
    _, values = store.target_columns(task)
    columns = {}
    for i, value in enumerate(values):
        def part(v):
            return v if v is None or len(values) == 1 else v[i]
        pairs = [(part(t), part(predictions.get(k))) for k, t in targets.items()]
        columns[f"target:{value}"] = pl.Series([None if t is None else str(t) for t, _ in pairs], dtype=pl.String)
        columns[f"computed:{value}"] = pl.Series([None if c is None else str(c) for _, c in pairs], dtype=pl.String)
        columns[f"diff:{value}"] = pl.Series([difference(t, c) for t, c in pairs], dtype=pl.Float64)
    return key_frame(targets, keys, dtypes).with_columns(**columns)


def key_frame(targets, keys, dtypes):
    """The target keys as a DataFrame with the dtypes of the frame's key columns."""
    parts = [k if isinstance(k, tuple) else (k,) for k in targets]
    return pl.DataFrame({name: [p[i] for p in parts] for i, name in enumerate(keys)},
                        schema={name: dtypes[name] for name in keys})


def with_features(df, meta, extra):
    """Calendar features of the target's own dates, plus the DSL features `extra` ({name: expression})."""
    dates = [c for c in meta["keys"] + meta["values"] if df[c].dtype == pl.Date]
    wanted = {f"{f}({c})": f"{f}({c})" for c in dates for f in EXPANSIONS if f"{f}({c})" not in df.columns}
    wanted |= dict(extra)
    lineage = dict(meta["lineage"])
    for name, text in wanted.items():
        node = dsl.parse(text, df.columns)
        df = df.with_columns(dsl.evaluate(node, df, df).alias(name))
        lineage[name] = {"dsl": text}
    return df, dict(meta, lineage=lineage)


def explain(task, df, meta, labels):
    """Run steps 3 (optimal trees) on the labels in the scratch run `<task>~score`, return its trees.json."""
    run = f"{task}~score"
    folder = paths.run_dir(run)
    df.write_parquet(folder / "frame.parquet")
    (folder / "frame.json").write_text(json.dumps(meta, indent=1, default=str))
    labels.write_parquet(folder / "labels.parquet")
    return tree.run(run)


def matching(df, path):
    cond = pl.all_horizontal([evaluate.condition(c) for c in path]) if path else pl.lit(True)
    return df.filter(cond)


def describe(task, value, df, keys, labels, trees):
    """Lines of score.md for one value column."""
    counts = collections.Counter(labels)
    noise = df.filter(pl.col("_label") == "noise")
    listed = iterate.known_corrections(task, value)
    lines = ["", f"## {value}", "",
             f"ok {counts['ok']}, missing {counts['missing']}, noise {counts['noise']} "
             f"(policies listed in NREXCP: {noise.filter(pl.col(keys[0]).is_in(list(listed))).height})",
             "| label | rows | examples |", "|---|---|---|"]
    for lab, n in counts.most_common(SHOWN + 2):
        if lab != "ok":
            examples = df.filter(pl.col("_label") == lab).select(keys).head(3).rows()
            lines.append(f"| {lab} | {n} | {examples} |")
    info = trees["values"].get(value, {})
    if info.get("minimal_sets"):
        best = info["minimal_sets"][0]
        lines.append(f"Where it is wrong: optimal tree errors {best['errors']}, leaves {best['leaves']} on "
                     f"{{{', '.join(best['features'])}}}")
        for leaf in best["leaf_rules"]:
            if leaf["label"] != "ok":
                example = matching(df, leaf["path"]).filter(pl.col("_label") == leaf["label"]).select(keys).head(2)
                path = " and ".join(f"{c} {op} {v}" for c, op, v in leaf["path"]) or "every row"
                lines.append(f"  {path} -> {leaf['label']} ({leaf['rows']} rows, {leaf['errors']} of them not "
                             f"{leaf['label']}), e.g. {example.rows()}")
        for c in info.get("conflicts", [])[:3]:
            lines.append(f"  conflicting vector {c['vector']}: {c['clusters']}; example {c['example']}")
    elif info.get("note"):
        lines.append(f"Trees: {info['note']}")
    return lines


def record(task, source, ok, held, wrong):
    entry = {"time": dt.datetime.now().isoformat(timespec="seconds"), "task": task, "value": "all",
             "candidate": "code:" + hashlib.sha1(source.encode()).hexdigest()[:12], "origin": "submission.py",
             "discovery": [int((ok & ~held).sum()), int((~held).sum())],
             "holdout": [int((ok & held).sum()), int(held.sum())], "total": [int(ok.sum()), len(ok)],
             "fingerprint": hashlib.sha1(json.dumps(sorted(map(list, wrong)), default=str).encode()).hexdigest()[:12]}
    with open(paths.run_dir(task) / "ledger.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return entry


def score(task, extra=None, folder=None):
    """Score the task function of submission.py, explain its wrong rows, write runs/<task>/score.md and diffs.parquet.

    `folder` scores another submission folder (a scratch copy): nothing is written to the ledger then.
    """
    module = load_submission(folder or paths.SUBMISSION)
    targets = scoring.read_targets(paths.TARGETS, task)
    started = time.time()
    with firewall():
        raw = getattr(module, task)(str(paths.LEGACY), *scoring.arguments(task, targets))
    seconds = time.time() - started
    predictions = scoring.normalize(task, raw)
    correct, total = scoring.accuracy(task, predictions, targets)
    df, meta = frames.load(task)
    keys = meta["keys"]
    per_value = compare(task, targets, predictions)
    differences(task, targets, predictions, keys, df.schema).write_parquet(paths.run_dir(task) / "diffs.parquet")
    labels = key_frame(targets, keys, df.schema).with_columns(
        pl.Series(f"label:{v}", per_value[v]) for v in per_value)
    df = df.with_row_index("_order").join(labels, on=keys, how="left").sort("_order").drop("_order")
    labels = df.select(keys + [f"label:{v}" for v in per_value])
    df = df.drop([f"label:{v}" for v in per_value])
    df, meta = with_features(df, meta, extra or {})
    trees = explain(task, df, meta, labels)
    ok = pl.all_horizontal([pl.col(f"label:{v}") == "ok" for v in per_value])
    flags = labels.select(ok.alias("ok"))["ok"]
    held = evaluate.holdout(labels, keys[0])
    source = inspect.getsource(getattr(module, task))
    wrong = labels.filter(~flags).select(keys).rows()
    entry = record(task, source, flags, held, wrong) if folder is None else {
        "candidate": "code:" + hashlib.sha1(source.encode()).hexdigest()[:12],
        "holdout": [int((flags & held).sum()), int(held.sum())]}
    policies = {k[0] if isinstance(k, tuple) else k for k in targets}
    extra_keys = sum(1 for k in set(predictions) - set(targets) if (k[0] if isinstance(k, tuple) else k) in policies)
    lines = [f"# score of {task} ({entry['candidate']})", "",
             f"Exact rows: {correct} / {total} (holdout {entry['holdout'][0]} / {entry['holdout'][1]}); "
             f"keys computed for target policies but not in the target: {extra_keys}; {seconds:.1f} s"]
    for value in per_value:
        work = df.with_columns(labels[f"label:{value}"].alias("_label"))
        lines += describe(task, value, work, keys, per_value[value], trees)
    text = "\n".join(lines) + "\n"
    (paths.run_dir(task) / "score.md").write_text(text)
    return text
