"""Step 1e: one row per target row, with every column reachable from the grain through the join graph.

A temporal join (into a versioned table) is made once per anchor date of the grain row and once for the latest
version: `PH_BRKNR@PR_RCVDT` is the broker of the policy version valid on the money date, `PH_BRKNR` the broker of
the latest version. Columns reached from an anchored column keep its anchor (`BR_TIER@PR_RCVDT`). Fixed-width code
columns are split by position (`RK_TARKEY[6]`). `frame.json` keeps the lineage of every column, which `freeze`
turns into code.
"""
import json
import zlib

import polars as pl

from . import dsl, paths, profile, schema, store

MAX_HOPS = 3
CALENDAR = ("weekday", "day", "month", "month_end")  # features of the target's own dates
MAX_ROWS = 1_000_000  # larger targets (t3_booking: 5 million bookings) use a fixed sample of policies
SAMPLE = 10  # ... the policies with crc32 % SAMPLE == 0 or 1: a fifth, half of it in the holdout
NOT_JOINED = {"NRBOOK", "NRCODE", "NRDICT", "NREXCP"}
LATEST = ""  # anchor of the latest version


def _suffix(anchor):
    return f"@{anchor}" if anchor else ""


def _usable(table):
    """Columns copied into the frame: no timestamps, no free text."""
    specs = {c.name: c for c in schema.columns(table)}
    df = store.load(table)
    keep = [c for c in df.columns if c in specs and specs[c].type != "T"
            and not (specs[c].type == "C" and specs[c].length >= profile.FREE_TEXT)]
    return keep + [c for c in df.columns if c.endswith("_RAW")]


def _attach(frame, source_col, table, key, kind, anchor, lineage):
    """Left-join `table` on frame[source_col] == table[key], returns the frame and the new column names.

    Temporal: the row valid on the anchor date (highest version among the valid ones), otherwise the latest
    version, the same rule as `neuron.valid`.
    """
    cols = [c for c in _usable(table) if c != key]
    names = {c: f"{c}{_suffix(anchor)}" for c in cols}
    if any(n in frame.columns for n in names.values()):
        return frame, []
    right = store.load(table).select([key] + cols).rename({key: "_key"})
    left = frame.select("_row", pl.col(source_col).alias("_key"),
                        *([pl.col(anchor).alias("_on")] if kind == "temporal" and anchor else []))
    candidates = left.join(right, on="_key", how="left")
    if kind == "plain":
        joined = candidates
    else:
        start, end, version = schema.validity(table)
        order = version or start
        latest = candidates.sort(order, descending=True, nulls_last=True).unique("_row", keep="first")
        joined = latest
        if anchor:
            on = pl.col("_on")
            live = candidates.filter((pl.col(start).fill_null(pl.date(1, 1, 1)) <= on)
                                     & (on <= pl.col(end).fill_null(pl.date(9999, 12, 31))))
            live = live.sort(order, descending=True, nulls_last=True).unique("_row", keep="first")
            joined = pl.concat([live, latest.join(live.select("_row"), on="_row", how="anti")], how="diagonal")
    joined = joined.select("_row", *[pl.col(c).alias(names[c]) for c in cols])
    frame = frame.join(joined, on="_row", how="left")
    step = {"from": source_col, "to": f"{table}.{key}", "kind": kind, "anchor": anchor or None}
    path = lineage.get(source_col, {}).get("path", []) + [step]
    for c in cols:
        lineage[names[c]] = {"table": table, "column": c, "path": path}
    return frame, list(names.values())


def build(task):
    """frame.parquet and frame.json of a task (runs the profile first if needed)."""
    folder = paths.run_dir(task)
    prof_path = folder / "profile.json"
    prof = json.loads(prof_path.read_text()) if prof_path.exists() else profile.profile(task)
    grain = prof["grain"]["best"]
    keys, values = store.target_columns(task)
    grain_table, mapping = grain["table"], grain["columns"]
    df = store.load(grain_table).select(_usable(grain_table)).with_columns(pl.lit(True).alias("_grain"))
    target = store.target(task)
    if target.height > MAX_ROWS:
        kept = [p for p in target["policy_id"].unique().to_list() if zlib.crc32(p.encode()) % SAMPLE < 2]
        target = target.filter(pl.col("policy_id").is_in(kept))
    frame = target.join(df, left_on=list(mapping), right_on=list(mapping.values()), how="left")
    unmatched = int(frame["_grain"].is_null().sum())
    frame = (frame.drop("_grain").with_columns(pl.col(k).alias(c) for k, c in mapping.items())
             .with_row_index("_row"))
    lineage = {c: {"table": grain_table, "column": c, "path": []} for c in df.columns if c != "_grain"}
    target_dates = [k for k in keys if k not in mapping and frame[k].dtype == pl.Date]  # e.g. valuation_date
    lineage.update({k: {"table": "target", "column": k, "path": []} for k in target_dates})
    anchors = [c for c in df.columns if df[c].dtype == pl.Date] + target_dates
    edges = {}
    for e in prof["joins"]:
        edges.setdefault(e["from"], []).append(e)
    reached = {(grain_table, LATEST)}
    frontier = [(c, LATEST) for c in lineage]
    for _ in range(MAX_HOPS):
        next_frontier = []
        for column, anchor in frontier:
            table, base = lineage[column]["table"], lineage[column]["column"]
            for e in edges.get(f"{table}.{base}", []):
                target_table, key = profile.split(e["to"])
                if target_table in NOT_JOINED:
                    continue
                # anchors start at the grain: a chain read on a date stays on that date, a latest chain stays latest
                from_grain = not lineage[column]["path"]
                choices = [LATEST] + anchors if e["kind"] == "temporal" and from_grain else [anchor]
                for a in choices:
                    if (target_table, a) in reached:
                        continue
                    reached.add((target_table, a))
                    frame, added = _attach(frame, column, target_table, key, e["kind"], a, lineage)
                    next_frontier += [(c, a) for c in added]
        frontier = next_frontier
    for column in [c for c in frame.columns if frame[c].dtype == pl.String and c not in keys]:
        for name, series in profile.code_positions(frame, column).items():
            frame = frame.with_columns(series.alias(name))
            lineage[name] = dict(lineage.get(column, {}), position=int(name.rsplit("[", 1)[1][:-1]))
    order = keys[-1]
    if len(keys) > 1 and frame[order].dtype in (pl.Int64, pl.Date):  # (policy, n), (policy, year): a sequence
        for v in values:
            frame = frame.with_columns(pl.col(v).shift(1).over(keys[:-1], order_by=order).alias(f"previous({v})"))
            lineage[f"previous({v})"] = {"dsl": f"previous({v})"}
    for column in [c for c in keys + values if frame[c].dtype == pl.Date]:
        for name in CALENDAR:
            text = f"{name}({column})"
            frame = frame.with_columns(dsl.evaluate(dsl.parse(text, frame.columns), frame, frame).alias(text))
            lineage[text] = {"dsl": text}
    frame = frame.drop("_row")
    frame.write_parquet(folder / "frame.parquet")
    meta = {"task": task, "keys": keys, "values": values, "grain": grain_table, "mapping": mapping,
            "anchors": anchors, "filter": prof.get("filter"), "rows": frame.height, "unmatched": unmatched,
            "sampled": frame.height < store.target(task).height,
            "lineage": lineage}
    (folder / "frame.json").write_text(json.dumps(meta, indent=1, default=str))
    return frame, meta


def load(task):
    folder = paths.run_dir(task)
    return pl.read_parquet(folder / "frame.parquet"), json.loads((folder / "frame.json").read_text())
