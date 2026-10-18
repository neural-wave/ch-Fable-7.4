"""Step 2: density clustering of the relation features, exact assignment, noise.

For every relation of a target value with an input (relations.py): 1-D density clusters of the relation on the
precise rows (large inputs, little rounding noise), a decimal center per cluster (the shortest one that
reproduces the cluster), then every row goes to the centers that reproduce it EXACTLY with at least one rounding
mode. Rows that no center reproduces in any mode are noise: candidate manual corrections, never mistaken for a
different rounding rule. The relation with the best exact coverage and the fewest clusters wins.
"""
import json
from decimal import Decimal

import polars as pl

from . import exact, frame as frames, paths, relations

MAX_CLUSTERS = 25
SHORTLIST = 4
MIN_COVERAGE = 0.3  # a relation must reproduce at least this share of the rows exactly
SIMPLER = 0.95  # a relation with at most half the clusters wins if it reproduces this share of the best one's rows


def plain(value):
    """Decimal without exponent notation: 1E+1 -> 10, 0.040 -> 0.04."""
    return Decimal(format(value.normalize(), "f"))


def scale_of(dtype):
    return dtype.scale if isinstance(dtype, pl.Decimal) else 0


def matches(df, relation, value, center, mode):
    """Boolean expression: the relation with this center reproduces the target value exactly."""
    v = pl.col(value)
    if relation.kind == "label":
        return v == str(center)
    if relation.kind == "days":
        return (v - pl.col(relation.input)).dt.total_days() == int(center)
    if relation.kind == "months":
        return pl.col(relation.input).dt.offset_by(f"{int(center)}mo") == v
    sv = scale_of(df[value].dtype)
    c_int, k = exact.constant(center)
    if relation.kind == "const":
        s = max(sv, k)
        return exact.scaled(v, s) == c_int * 10 ** (s - k)
    x = pl.col(relation.input)
    sx = scale_of(df[relation.input].dtype)
    if relation.kind == "diff":
        s = max(sv, sx, k)
        return exact.scaled(v, s) - exact.scaled(x, s) == c_int * 10 ** (s - k)
    product = exact.scaled(x, sx) * pl.lit(c_int, dtype=pl.Int128)
    return exact.round_to(product, sx + k, sv, mode) == exact.scaled(v, sv)


def mode_mask(df, relation, value, center):
    """Int16 bitmask of the rounding modes (exact.MODES order) that reproduce each row; bit 0 for exact kinds."""
    if relation.kind != "ratio":
        return matches(df, relation, value, center, None).cast(pl.Int16).fill_null(0)
    bits = [matches(df, relation, value, center, m).fill_null(False).cast(pl.Int16) * (1 << i)
            for i, m in enumerate(exact.MODES)]
    return pl.sum_horizontal(bits).cast(pl.Int16)


def dense_groups(r, eps, min_size):
    """Sorted values split where the gap exceeds eps; groups with at least min_size values."""
    values = r.drop_nulls().drop_nans().sort()
    if values.len() == 0:
        return []
    breaks = (values.diff().fill_null(0) > eps).cum_sum()
    groups = pl.DataFrame({"v": values, "g": breaks}).group_by("g").agg(
        pl.col("v").min().alias("lo"), pl.col("v").max().alias("hi"), pl.len().alias("n"), pl.col("v").mean().alias("mean"))
    return groups.filter(pl.col("n") >= min_size).sort("lo").to_dicts()


def precision(df, relation, value):
    """(rows used to find clusters, gap eps) for a relation."""
    sv = scale_of(df[value].dtype)
    unit = 10.0 ** -sv
    if relation.kind == "ratio":
        size = df[relation.input].cast(pl.Float64).abs()
        threshold = max(size.filter(size > 0).median() or 0.0, unit)
        return size >= threshold, unit / threshold
    if relation.kind in ("days", "months"):
        return pl.Series([True] * df.height), 0.5
    return pl.Series([True] * df.height), unit / 2


def snap(df, relation, value, rows, mean):
    """Shortest decimal center that reproduces (almost) as many rows of the cluster as any longer one."""
    if relation.kind != "ratio":
        r = relations.evaluate(df.filter(rows), relation, value)
        top = r.round(9).mode().sort()[0]
        whole = relation.kind in ("days", "months")
        return Decimal(str(int(round(top)))) if whole else plain(Decimal(str(round(top, 9))))
    sample = df.filter(rows).head(3000)
    scores = []
    for k in range(0, 10):
        center = plain(Decimal(str(round(mean, k))))
        hit = sample.select(pl.any_horizontal(matches(sample, relation, value, center, m).fill_null(False)
                                              for m in exact.MODES).sum()).item()
        scores.append((hit, k, center))
    best = max(s[0] for s in scores)
    return next(center for hit, k, center in scores if hit >= 0.98 * best and (center != 0 or best == hit))


def find_centers(df, relation, value):
    """(centers, precise coverage) of one relation."""
    if relation.kind == "label":  # every category is a cluster, every row is assigned exactly
        values = df[value].drop_nulls().unique().sort().to_list()
        return (values, 1.0) if 1 <= len(values) <= MAX_CLUSTERS else ([], 0.0)
    r = relations.evaluate(df, relation, value)
    precise, eps = precision(df, relation, value)
    keep = precise & r.is_not_null() & r.is_not_nan()
    n = int(keep.sum())
    if n == 0:
        return [], 0.0
    groups = dense_groups(r.filter(keep), eps, max(5, int(0.0002 * n)))
    if not groups or len(groups) > MAX_CLUSTERS:
        return [], 0.0
    covered = sum(g["n"] for g in groups) / n
    centers = []
    for g in groups:
        rows = keep & (r >= g["lo"]) & (r <= g["hi"])
        centers.append(snap(df, relation, value, rows, g["mean"]))
    return sorted(set(centers)), covered


def assign(df, relation, value, centers):
    """Per row: matching centers and modes; label = the only matching center, 'ambiguous' or 'noise'."""
    masks = df.select(mode_mask(df, relation, value, c).alias(f"m{i}") for i, c in enumerate(centers))
    hits = masks.select(pl.sum_horizontal((pl.col(f"m{i}") > 0).cast(pl.Int8) for i in range(len(centers)))
                        .alias("hits"))["hits"]
    label = pl.Series(["noise"] * df.height, dtype=pl.String)
    modes = pl.Series([0] * df.height, dtype=pl.Int16)
    for i, c in enumerate(centers):
        only = (masks[f"m{i}"] > 0) & (hits == 1)
        label = pl.select(pl.when(only).then(pl.lit(str(c))).otherwise(label)).to_series()
        modes = pl.select(pl.when(only).then(masks[f"m{i}"]).otherwise(modes)).to_series()
    label = pl.select(pl.when(hits > 1).then(pl.lit("ambiguous")).otherwise(label)).to_series()
    return label, modes


def cluster_value(df, meta, value):
    """Relations that reproduce enough rows exactly, best first, and the best approximate one as a hint.

    The hint is a relation with dense clusters that no center reproduces exactly, e.g. a charge that is 2 % of
    the premiums but rounded per instalment: the agent learns the rate even though the formula is a sum.
    """
    tried, hint = _cluster(df, meta, value, relations.candidates(df, meta, value))
    if not tried:  # sequences: the previous value of the same policy as the input
        tried, previous_hint = _cluster(df, meta, value, relations.candidates(df, meta, value, sequence=True))
        hint = hint or previous_hint
    return tried, hint


def _cluster(df, meta, value, candidates):
    shortlist = []
    for relation in candidates:
        centers, covered = find_centers(df, relation, value)
        if centers:
            shortlist.append((covered, -len(centers), relation, centers))
    shortlist.sort(key=lambda s: (round(s[0], 3), s[1]), reverse=True)
    tried = []
    for covered, _, relation, centers in shortlist[:SHORTLIST]:
        label, modes = assign(df, relation, value, centers)
        assigned = int((label != "noise").sum())
        tried.append({"relation": relation, "centers": centers, "label": label, "modes": modes,
                      "assigned": assigned, "noise": int((label == "noise").sum()),
                      "ambiguous": int((label == "ambiguous").sum())})
    hint = None
    if shortlist and shortlist[0][0] >= 0.5:  # dense on at least half of the precise rows, else it says nothing
        covered, _, relation, centers = shortlist[0]
        hint = {"relation": relation.name, "centers": [str(c) for c in centers[:8]], "covered": round(covered, 3)}
    tried = [t for t in tried if t["assigned"] >= MIN_COVERAGE * df.height]  # tiny clusters are chance
    tried.sort(key=lambda t: (t["assigned"], -len(t["centers"])), reverse=True)
    if tried:  # days from the previous due date need 11 clusters (28..31, 89..92, ...), months need 4 (1, 3, 6, 12)
        simpler = [t for t in tried if t["assigned"] >= SIMPLER * tried[0]["assigned"]
                   and len(t["centers"]) <= len(tried[0]["centers"]) / 2]
        if simpler:
            best = min(simpler, key=lambda t: (len(t["centers"]), -t["assigned"]))
            tried = [best] + [t for t in tried if t is not best]
    return tried, hint


def run(task):
    """clusters.json and labels.parquet of a task."""
    df, meta = frames.load(task)
    folder = paths.run_dir(task)
    out, labels = {"task": task, "rows": df.height, "values": {}}, df.select(meta["keys"])
    for value in meta["values"]:
        tried, hint = cluster_value(df, meta, value)
        sums = relations.identities(df, meta, value)
        if not tried:
            out["values"][value] = {"relation": None, "note": "no clusterable relation", "approximate": hint,
                                    "identities": sums}
            continue
        best = tried[0]
        label, modes = best["label"], best["modes"]
        sizes = pl.DataFrame({"label": label, "modes": modes}).group_by("label").agg(pl.len().alias("rows"))
        noise_keys = df.filter(label == "noise").select(meta["keys"]).head(50).rows()
        out["values"][value] = {
            "relation": best["relation"].to_json(), "relation_name": best["relation"].name,
            "centers": [{"center": str(c), "rows": int(sizes.filter(pl.col("label") == str(c))["rows"].sum()),
                         "modes": _mode_counts(modes.filter(label == str(c)))} for c in best["centers"]],
            "assigned": best["assigned"], "noise": best["noise"], "ambiguous": best["ambiguous"],
            "noise_examples": noise_keys, "identities": sums,
            "alternatives": [{"relation": t["relation"].name, "centers": len(t["centers"]), "assigned": t["assigned"],
                              "noise": t["noise"]} for t in tried[1:]],
        }
        labels = labels.with_columns(label.alias(f"label:{value}"), modes.alias(f"modes:{value}"))
    labels.write_parquet(folder / "labels.parquet")
    (folder / "clusters.json").write_text(json.dumps(out, indent=1, default=str))
    return out


def _mode_counts(modes):
    return {m.replace("ROUND_", ""): int(((modes & (1 << i)) > 0).sum()) for i, m in enumerate(exact.MODES)}
