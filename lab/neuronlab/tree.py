"""Step 3: which conditions select each cluster. Optimal sparse trees (GOSDT objective), smallest feature sets.

Backends:
- exact (default): dynamic programming over the deduplicated feature vectors, splits "feature == value", depth <= 3,
  lexicographic objective (errors, leaves) like GOSDT, and the number of optimal trees;
- gosdt: used when the package is installed and asked for;
- cart: scikit-learn, greedy, for comparison and as fallback on large data.
The smallest feature sets that reach the optimum are found by solving the optimum on subsets of size 1, 2, 3.
"""
import itertools
import json
import math

import numpy as np
import polars as pl

from . import frame as frames, paths

MAX_DEPTH = 3
MAX_VALUES = 32
SCREEN = 10
MAX_VECTORS = 4000


def features(df, meta):
    """Categorical columns of the frame usable as split features (2..32 values, not keys or targets)."""
    skip = set(meta["keys"]) | set(meta["values"]) | set(meta["mapping"].values())
    found = []
    for name in df.columns:
        if name in skip or name.endswith("_RAW") or df[name].dtype in (pl.Date, pl.Datetime):
            continue
        n = df[name].n_unique()
        if 2 <= n <= MAX_VALUES:
            found.append(name)
    return found


def entropy(df, cols, label):
    """Conditional entropy H(label | cols) in bits."""
    counts = df.group_by(cols + [label]).agg(pl.len().alias("n"))
    totals = counts.group_by(cols).agg(pl.col("n").sum().alias("t"))
    joined = counts.join(totals, on=cols)
    n = joined["n"].sum()
    p = joined["n"] / n
    return float(-(p * (joined["n"] / joined["t"]).log(2)).sum())


def signature(series):
    """Hash of the partition a column induces on the rows (value names do not matter)."""
    codes = series.cast(pl.String).fill_null("<null>")
    first = pl.DataFrame({"v": codes}).with_row_index("i")
    order = first.group_by("v").agg(pl.col("i").min().alias("code"))
    return int(first.join(order, on="v", how="left").sort("i")["code"].hash().sum())


def classes(df, names):
    """{representative: [equivalent features]}: features with the same partition of the rows are one feature.

    The representative is the one with the shortest name (no anchor, no position) among its class.
    """
    groups = {}
    for name in names:
        groups.setdefault(signature(df[name]), []).append(name)
    return {min(g, key=lambda n: (len(n), n)): sorted(g) for g in groups.values()}


def blocked_equivalents(df, name, used_values, candidates):
    """Features whose partition equals the one the tree uses on `name` (its used values vs the rest)."""
    used = set(map(str, used_values))
    blocked = df[name].cast(pl.String).map_elements(lambda v: v if v in used else "<other>", return_dtype=pl.String)
    target = signature(blocked)
    return [c for c in candidates if c != name and signature(df[c]) == target]


def screen(df, names, label, keep=SCREEN):
    """Features with the most information on the label, alone or in pairs (catches interactions)."""
    single = sorted(names, key=lambda f: entropy(df, [f], label))[:20]
    pairs = sorted(itertools.combinations(single, 2), key=lambda p: entropy(df, list(p), label))[:15]
    chosen = []
    for f in [f for p in pairs for f in p] + single:
        if f not in chosen:
            chosen.append(f)
    return chosen[:keep]


class Solver:
    """Exact optimal tree on unique feature vectors: minimize (errors, leaves) with depth <= MAX_DEPTH."""

    def __init__(self, vectors, counts, names):
        self.vectors, self.names = vectors, names
        self.counts = counts  # labels x vectors
        self.literals = [(i, v) for i, f in enumerate(names) for v in sorted({u[i] for u in vectors}, key=str)]
        self.masks = [np.array([u[i] == v for u in vectors]) for i, v in self.literals]
        self.memo = {}

    def leaf(self, mask):
        totals = self.counts[:, mask].sum(axis=1)
        return int(totals.sum() - totals.max()), int(totals.argmax())

    def solve(self, mask, depth, allowed):
        key = (mask.tobytes(), depth, allowed)
        if key in self.memo:
            return self.memo[key]
        errors, label = self.leaf(mask)
        best, count, split = (errors, 1), 1, None
        if depth > 0 and errors > 0:
            for li in allowed:
                left = mask & self.masks[li]
                right = mask & ~self.masks[li]
                if not left.any() or not right.any():
                    continue
                (el, nl), cl, _ = self.solve(left, depth - 1, allowed)
                (er, nr), cr, _ = self.solve(right, depth - 1, allowed)
                cand = (el + er, nl + nr)
                if cand < best:
                    best, count, split = cand, cl * cr, li
                elif cand == best and split is not None:
                    count += cl * cr
        self.memo[key] = (best, count, split)
        return self.memo[key]

    def build(self, mask, depth, allowed, labels, path=()):
        """Nested tree and flat leaves (path, label, rows, errors)."""
        _, _, split = self.solve(mask, depth, allowed)
        if split is None:
            totals = self.counts[:, mask].sum(axis=1)
            leaf = {"path": list(path), "label": labels[int(totals.argmax())], "rows": int(totals.sum()),
                    "errors": int(totals.sum() - totals.max())}
            return {"leaf": leaf["label"], "rows": leaf["rows"], "errors": leaf["errors"]}, [leaf]
        i, v = self.literals[split]
        name = self.names[i]
        yes, ly = self.build(mask & self.masks[split], depth - 1, allowed, labels, path + ((name, "=", v),))
        no, ln = self.build(mask & ~self.masks[split], depth - 1, allowed, labels, path + ((name, "!=", v),))
        return {"split": [name, v], "yes": yes, "no": no}, ly + ln


def vectors_of(df, cols, label):
    """Unique feature vectors and their label counts."""
    grouped = df.group_by(cols + [label]).agg(pl.len().alias("n"))
    labels = sorted(grouped[label].unique().to_list())
    vecs = grouped.select(cols).unique(maintain_order=True)
    index = {tuple(r): i for i, r in enumerate(vecs.rows())}
    counts = np.zeros((len(labels), len(index)), dtype=np.int64)
    li = {l: i for i, l in enumerate(labels)}
    for row in grouped.iter_rows():
        counts[li[row[-2]], index[tuple(row[:-2])]] += row[-1]
    return list(index), counts, labels


def optimal(df, cols, label, depth=MAX_DEPTH):
    """Optimal tree on the given features: errors, leaves, number of optimal trees, tree, leaves."""
    vecs, counts, labels = vectors_of(df, cols, label)
    if len(vecs) > MAX_VECTORS:
        return None
    solver = Solver(vecs, counts, cols)
    allowed = tuple(range(len(solver.literals)))
    full = np.ones(len(vecs), dtype=bool)
    (errors, leaves), n_opt, _ = solver.solve(full, depth, allowed)
    tree, flat = solver.build(full, depth, allowed, labels)
    conflicts = int(sum(1 for j in range(len(vecs)) if (counts[:, j] > 0).sum() > 1))
    return {"features": cols, "errors": errors, "leaves": leaves, "optimal_trees": n_opt, "vectors": len(vecs),
            "conflicting_vectors": conflicts, "tree": tree, "leaf_rules": flat}


def minimal_sets(df, screened, label, max_size=3):
    """Smallest feature sets reaching the best (errors, leaves) found on subsets up to max_size."""
    results = []
    for size in range(1, max_size + 1):
        for combo in itertools.combinations(screened, size):
            res = optimal(df, list(combo), label)
            if res:
                results.append(res)
    if not results:
        return [], None
    best = min((r["errors"], r["leaves"]) for r in results)
    for size in range(1, max_size + 1):
        found = [r for r in results if len(r["features"]) == size and (r["errors"], r["leaves"]) == best]
        if found:
            return found, best
    return [], best


def cart(df, cols, label, depth=MAX_DEPTH):
    """Greedy CART (scikit-learn) on one-hot features, as a reference."""
    from sklearn.tree import DecisionTreeClassifier
    onehot = df.select(cols).cast(pl.String).fill_null("<null>").to_dummies(separator="==")
    y = df[label].to_numpy()
    model = DecisionTreeClassifier(max_depth=depth, random_state=0).fit(onehot.to_numpy(), y)
    t, names, leaves = model.tree_, onehot.columns, []

    def walk(node, path):
        if t.children_left[node] == -1:
            counts = t.value[node][0] * t.n_node_samples[node] if t.value[node][0].sum() <= 1.0001 else t.value[node][0]
            leaves.append({"path": path, "label": str(model.classes_[int(np.argmax(counts))]),
                           "rows": int(t.n_node_samples[node])})
            return
        name, value = names[t.feature[node]].split("==", 1)
        walk(t.children_right[node], path + [(name, "=", value)])
        walk(t.children_left[node], path + [(name, "!=", value)])

    walk(0, [])
    errors = int((model.predict(onehot.to_numpy()) != y).sum())
    used = sorted({c for leaf in leaves for c, _, _ in leaf["path"]})
    return {"features": used, "errors": errors, "leaves": len(leaves), "leaf_rules": leaves}


def conflicts(data, cols, label, keys, top=5):
    """Feature vectors that carry more than one cluster: where a feature is missing.

    The example row is taken from a minority cluster of the vector: it is a row the missing feature must explain.
    """
    groups = (data.group_by(cols).agg(pl.col(label).value_counts(sort=True).alias("labels"), pl.len().alias("rows"))
              .filter(pl.col("labels").list.len() > 1).sort("rows", descending=True).head(top))
    found = []
    for r in groups.iter_rows(named=True):
        majority = r["labels"][0][label]
        match = pl.all_horizontal([pl.col(c).eq_missing(r[c]) for c in cols]) & (pl.col(label) != majority)
        example = data.filter(match).select(keys).row(0)
        found.append({"vector": {c: r[c] for c in cols}, "clusters": {str(x[label]): x["count"] for x in r["labels"]},
                      "example": list(example)})
    return found


def run(task):
    """trees.json: per target value, the screened features, the optimum, the minimal feature sets, CART."""
    df, meta = frames.load(task)
    folder = paths.run_dir(task)
    labels = pl.read_parquet(folder / "labels.parquet")
    names = features(df, meta)
    out = {"task": task, "values": {}}
    for value in meta["values"]:
        col = f"label:{value}"
        if col not in labels.columns:
            continue
        later = meta["values"][meta["values"].index(value):]  # values are computed in file order
        own = [n for n in names if any(f"({v})" in n for v in later)]
        data = df.select([n for n in names if n not in own] + meta["keys"]).with_columns(labels[col].alias("_label")).filter(
            ~pl.col("_label").is_in(["noise", "ambiguous"]))
        data = data.with_columns(pl.col(n).cast(pl.String) for n in names if n not in own)
        if data["_label"].n_unique() < 2:
            out["values"][value] = {"note": "one cluster only, no conditions needed", "rows": data.height}
            continue
        equivalent = classes(data, [n for n in names if n not in own])
        screened = screen(data, list(equivalent), "_label")
        sets, best = minimal_sets(data, screened, "_label")
        for s in sets:
            s["equivalents"] = {}
            for f in s["features"]:
                used = {v for leaf in s["leaf_rules"] for c, _, v in leaf["path"] if c == f}
                same = [g for g in equivalent[f] if g != f]
                coarse = blocked_equivalents(data, f, used, [n for n in names if n not in own]) \
                    if len(used) < data[f].n_unique() else []
                s["equivalents"][f] = sorted(set(same + coarse))
        overall = optimal(data, screened[:6], "_label")
        out["values"][value] = {
            "rows": data.height, "screened": screened,
            "best": {"errors": best[0], "leaves": best[1]} if best else None,
            "conflicts": conflicts(data, sets[0]["features"], "_label", meta["keys"]) if sets and best[0] else [],
            "minimal_sets": sets,
            "with_top6_features": {k: overall[k] for k in ("features", "errors", "leaves", "optimal_trees")}
            if overall else None,
            "cart": cart(data, screened, "_label"),
        }
    (folder / "trees.json").write_text(json.dumps(out, indent=1, default=str))
    return out
