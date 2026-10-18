"""Step 1e: one row per target row, with every column reachable from the grain through the join graph.

A temporal join (into a versioned table) is made once per anchor date of the grain row and once for the latest
version: `PH_BRKNR@PR_RCVDT` is the broker of the policy version valid on the money date, `PH_BRKNR` the broker of
the latest version. Columns reached from an anchored column keep its anchor (`BR_TIER@PR_RCVDT`). Fixed-width code
columns are split by position (`RK_TARKEY[6]`). `frame.json` keeps the lineage of every column, which `freeze`
turns into code. A task definition narrows the joined tables to its scope, casts the legacy columns whose type a
person confirmed, and adds the values of other tasks as inputs (`<task>__<column>`).
"""
import json
import zlib

import polars as pl

from . import dsl, paths, profile, schema, store, taskdef

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
    scope = taskdef.scope_tables(task)
    reached = {(grain_table, LATEST)}
    frontier = [(c, LATEST) for c in lineage]
    for _ in range(MAX_HOPS):
        next_frontier = []
        for column, anchor in frontier:
            table, base = lineage[column]["table"], lineage[column]["column"]
            for e in edges.get(f"{table}.{base}", []):
                target_table, key = profile.split(e["to"])
                if target_table in NOT_JOINED or (scope and target_table not in scope):
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
    frame = confirmed_types(frame, taskdef.column_types(task))
    for other in taskdef.scope_tasks(task):
        frame = other_task(frame, other, keys, lineage)
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


def confirmed_types(frame, types):
    """Cast the columns (and their anchored copies `COL@DATE`) whose type a person confirmed in the definition."""
    for column, kind in types.items():
        for name in [c for c in frame.columns if c == column or c.startswith(column + "@")]:
            if frame[name].dtype != pl.String:
                continue  # NRDICT typed it already
            text = pl.col(name).str.strip_chars()
            if kind == "date":
                expr = text.str.to_date("%Y%m%d", strict=False).fill_null(text.str.to_date("%Y-%m-%d", strict=False))
            elif kind == "int":
                expr = text.cast(pl.Int64, strict=False)
            elif kind.startswith("decimal"):
                expr = text.cast(pl.Decimal(38, int(kind.split(":")[1]) if ":" in kind else 2), strict=False)
            else:
                continue
            frame = frame.with_columns(expr.alias(name))
    return frame


def other_task(frame, other, keys, lineage):
    """The values of another task's target as inputs, joined on the key columns both share.

    When the other task is finer (more key columns, e.g. one row per fund), its values are summed per shared key.
    """
    other_keys, other_values = store.target_columns(other)
    shared = [k for k in other_keys if k in keys]
    if not shared:
        return frame
    df = store.target(other)
    if set(other_keys) - set(shared):
        df = df.group_by(shared).agg(pl.col(v).sum() for v in other_values)
    names = {v: f"{other}__{v}" for v in other_values}
    df = df.select(shared + other_values).rename(names)
    frame = frame.join(df, on=shared, how="left").sort("_row")
    for v, name in names.items():
        lineage[name] = {"task": other, "column": v}
    return frame


def load(task):
    folder = paths.run_dir(task)
    return pl.read_parquet(folder / "frame.parquet"), json.loads((folder / "frame.json").read_text())
