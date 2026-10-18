"""Step 7: residuals of the best candidate -> missing structure or noise; noise -> outlier list (t5).

Every residual row is classified with the clusters of step 2:
- another regime: the row is reproduced exactly by a different cluster center than the one the candidate used,
  so a condition is missing (the tree needs a new feature): structure, reported per (used -> actual) pair;
- noise: no cluster center reproduces it in any rounding mode: a candidate manual correction, checked against
  the incomplete list NREXCP;
- ambiguous: several centers reproduce it.
"""
import json
from decimal import Decimal

import polars as pl

from . import evaluate, frame as frames, paths, store


def known_corrections(task, value):
    """Policies listed in NREXCP for this task value (the list is incomplete)."""
    exc = store.load("NREXCP")
    return set(exc.filter(pl.col("EX_TARGET") == f"{task}.{value}")["EX_POLNR"].to_list())


def residuals(df, labels, meta, candidate, value):
    """Rows the candidate gets wrong, with their signatures and their class."""
    p = evaluate.predicted(df, candidate, value)
    used = evaluate.constants(df, candidate)
    table = (df.select(meta["keys"] + [value]).with_columns(p.alias("computed"), used.alias("used"),
                                                           labels[f"label:{value}"].alias("label"))
             .filter((pl.col(value) != pl.col("computed")).fill_null(True)))
    rows = []
    for r in table.iter_rows(named=True):
        v, c = r[value], r["computed"]
        delta = (v - c) if isinstance(v, Decimal) and c is not None else None
        kind = r["label"] if r["label"] in ("noise", "ambiguous") else "other regime"
        rows.append({"key": [r[k] for k in meta["keys"]], "target": str(v), "computed": str(c), "class": kind,
                     "used": r["used"], "fits": r["label"], "delta": str(delta) if delta is not None else None,
                     "whole_units": bool(delta is not None and delta == delta.to_integral_value())})
    return rows


def run(task):
    """residuals.json and outliers.json of a task (or of a variant run `<task>~...`) from the pool winner."""
    df, meta = frames.load(task)
    base_task = task.split("~")[0]
    folder = paths.run_dir(task)
    pools = json.loads((folder / "pool.json").read_text())
    labels = pl.read_parquet(folder / "labels.parquet")
    report, outliers = {"task": task, "values": {}}, []
    for value, info in pools["values"].items():
        best = next(c for c in info["candidates"] if c["id"] == info["best"])
        rows = residuals(df, labels, meta, best, value)
        pairs = {}
        for r in rows:
            if r["class"] == "other regime":
                pairs[f"{r['used']} -> {r['fits']}"] = pairs.get(f"{r['used']} -> {r['fits']}", 0) + 1
        noise = [r for r in rows if r["class"] == "noise"]
        listed = known_corrections(base_task, value)
        for r in noise:
            r["in_NREXCP"] = r["key"][0] in listed
            outliers.append({"task": base_task, "value": value, **r})
        report["values"][value] = {
            "candidate": best["id"], "residuals": len(rows),
            "structure": dict(sorted(pairs.items(), key=lambda kv: -kv[1])), "noise": len(noise),
            "ambiguous": sum(r["class"] == "ambiguous" for r in rows),
            "whole_unit_deltas": sum(r["whole_units"] for r in noise),
            "in_NREXCP": sum(r["in_NREXCP"] for r in noise),
            "rows": noise[:30] + [r for r in rows if r["class"] != "noise"][:10],
        }
    (folder / "residuals.json").write_text(json.dumps(report, indent=1, default=str))
    (folder / "outliers.json").write_text(json.dumps(outliers, indent=1, default=str))
    return report
