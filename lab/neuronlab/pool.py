"""Step 4: the pool of partial rules (cards) and complete candidates, scored exactly.

- cards: one per leaf of an optimal tree ("tier A and premium type L -> 4 % of PR_AMTRC"), with support, purity,
  compatible roundings, equivalent conditions and examples;
- candidates: the CART tree, every optimal tree with a minimal feature set, and their generalization into a
  lookup: when the constants of the leaves are values of a parameter table and the leaf features are contained
  (IND) in the key columns of that table, the leaves become one lookup that also covers rates never seen;
- variants: other rounding modes and other anchor dates of the same candidate.
Every candidate is scored on discovery and holdout and written to the ledger; the winner is the best on
holdout, then discovery, then the simplest (lookup before constants, fewer features, fewer anchors).
"""
import itertools
import json
from decimal import Decimal

import polars as pl

from . import evaluate, exact, frame as frames, paths, profile, schema, store

MAX_PARAM_ROWS = 2000


def leaf_rules(leaves):
    return [{"when": [list(c) for c in leaf["path"]], "then": leaf["label"]} for leaf in leaves]


def features_of(candidate):
    if candidate.get("lookup"):
        return sorted(candidate["lookup"]["keys"].values())
    return sorted({c[0] for r in candidate["rules"] for c in r["when"]})


PRIOR = ("ROUND_HALF_UP", "ROUND_HALF_EVEN", "ROUND_DOWN", "ROUND_HALF_DOWN", "ROUND_UP", "ROUND_FLOOR",
         "ROUND_CEILING")  # declared preference when the train data cannot decide between rounding modes


def complexity(candidate):
    feats = features_of(candidate)
    return (0 if candidate.get("lookup") else len(candidate["rules"]), len(feats), sum("@" in f for f in feats),
            PRIOR.index(candidate.get("rounding", "ROUND_HALF_UP")))


def ties(scored):
    """Candidates with the same train behaviour as the winner (same wrong rows): the data cannot tell them apart."""
    best = scored[0]["score"]["fingerprint"]
    return [c["id"] for c in scored[1:] if c["score"]["fingerprint"] == best]


def parameter_tables():
    """(table, value column, key columns) of the small tables: rates, scales, fees."""
    legacy = profile.legacy_profile()
    found = []
    for table in store.tables():
        if table in ("NRDICT", "NRCODE", "NREXCP") or store.load(table).height > MAX_PARAM_ROWS:
            continue
        period = schema.validity(table) or ()
        specs = schema.columns(table)
        for value in (c for c in specs if c.is_amount):
            for ucc in legacy["uccs"].get(table, []):
                keys = [k for k in ucc if k not in period and k != value.name]
                if keys and len(keys) <= 3 and all(schema.column(table, k).is_key_like for k in keys) \
                        and value.name not in ucc:
                    found.append((table, value.name, tuple(keys)))
    return sorted(set(found))


def generalize(df, labelled, minimal, centers):
    """Lookup candidates equivalent to the leaves of an optimal tree."""
    options = {f: [f] + minimal.get("equivalents", {}).get(f, []) for f in minimal["features"]}
    found = []
    wanted = {Decimal(c) for c in centers}
    for table, value, keys in parameter_tables():
        param = store.load(table)
        values = {Decimal(str(v)) for v in param[value].drop_nulls().to_list()}
        if not wanted <= values or len(keys) != len(options):
            continue
        domains = {k: set(param[k].cast(pl.String).drop_nulls().to_list()) for k in keys}
        for choice in itertools.product(*options.values()):
            for order in itertools.permutations(keys):
                mapping = dict(zip(order, choice))
                if not all(set(df[f].cast(pl.String).drop_nulls().unique().to_list()) <= domains[k]
                           for k, f in mapping.items()):
                    continue
                period = schema.validity(table)
                lookup = {"table": table, "column": value, "keys": mapping, "anchor": None}
                got = evaluate.lookup_constants(labelled, lookup)
                agree = (got.cast(pl.Decimal(38, 9)) == labelled["_label"].cast(pl.Decimal(38, 9))).fill_null(False)
                rate = float(agree.mean())
                if rate >= 0.999:
                    found.append({"lookup": lookup, "agreement": round(rate, 6), "versioned": bool(period)})
    return found


def anchor_variants(candidate, anchors):
    """Same candidate with each anchored feature moved to the other anchors and to the latest version."""
    feats = [f for f in features_of(candidate) if "@" in f]
    out = []
    for f in feats:
        base, current = f.split("@", 1)
        for other in [a for a in anchors if a != current] + [None]:
            g = f"{base}@{other}" if other else base
            variant = json.loads(json.dumps(candidate).replace(f'"{f}"', f'"{g}"'))
            variant["id"] = f"{candidate['id']}/{g}"
            variant["origin"] = f"{candidate['id']} with {g} instead of {f}"
            out.append(variant)
    return out


def rounding_variants(candidate):
    out = []
    for mode in exact.MODES:
        if mode != candidate.get("rounding", "ROUND_HALF_UP"):
            variant = dict(candidate, rounding=mode, id=f"{candidate['id']}/{mode.replace('ROUND_', '')}",
                           origin=f"{candidate['id']} with {mode}")
            out.append(variant)
    return out


def cards(df, labels_col, value, minimal, relation_name, modes, keys):
    """One card per leaf of the first minimal tree."""
    found = []
    for i, leaf in enumerate(minimal["leaf_rules"]):
        cond = pl.all_horizontal([evaluate.condition(c) for c in leaf["path"]]) if leaf["path"] else pl.lit(True)
        rows = df.with_columns(labels_col.alias("_label"), modes.alias("_modes")).filter(
            cond & (pl.col("_label") == leaf["label"]))
        compatible = [m.replace("ROUND_", "") for b, m in enumerate(exact.MODES)
                      if rows.height and int((rows["_modes"] & (1 << b) > 0).sum()) == rows.height]
        found.append({"id": f"L{i + 1}", "when": [list(c) for c in leaf["path"]],
                      "then": {"relation": relation_name, "center": leaf["label"]},
                      "rounding": compatible, "support_rows": leaf["rows"],
                      "purity": round(1 - leaf["errors"] / max(1, leaf["rows"]), 6),
                      "equivalent_when": minimal.get("equivalents", {}),
                      "examples": rows.select(keys).head(2).rows()})
    return found


def run(task):
    """pool.json: cards, candidates with exact scores, the winner; every evaluation goes to the ledger."""
    df, meta = frames.load(task)
    folder = paths.run_dir(task)
    clusters = json.loads((folder / "clusters.json").read_text())
    trees = json.loads((folder / "trees.json").read_text())
    labels = pl.read_parquet(folder / "labels.parquet")
    out = {"task": task, "values": {}}
    for value in meta["values"]:
        info, tinfo = clusters["values"].get(value, {}), trees["values"].get(value, {})
        if not info.get("relation"):
            continue
        relation = info["relation"]
        centers = [c["center"] for c in info["centers"]]
        label_col, modes = labels[f"label:{value}"], labels[f"modes:{value}"]
        base = []
        if len(centers) == 1:
            base.append({"id": "C0", "origin": "single cluster", "rules": [{"when": [], "then": centers[0]}]})
        if tinfo.get("cart"):
            base.append({"id": "C1", "origin": "CART tree as is", "rules": leaf_rules(tinfo["cart"]["leaf_rules"])})
        labelled = df.with_columns(label_col.alias("_label")).filter(~pl.col("_label").is_in(["noise", "ambiguous"]))
        for i, minimal in enumerate(tinfo.get("minimal_sets", [])):
            base.append({"id": f"C2.{i + 1}", "origin": f"optimal tree on {minimal['features']}",
                         "rules": leaf_rules(minimal["leaf_rules"])})
            for j, g in enumerate(generalize(df, labelled, minimal, centers)):
                base.append({"id": f"C3.{i + 1}.{j + 1}", "lookup": g["lookup"],
                             "origin": f"generalization of C2.{i + 1}: constants = {g['lookup']['table']}."
                                       f"{g['lookup']['column']} (agreement {g['agreement']})"})
        for c in base:
            c.update(relation=relation, value=value, rounding=c.get("rounding", "ROUND_HALF_UP"))
        pool = list(base)
        for c in base:
            pool += rounding_variants(c) + anchor_variants(c, meta["anchors"])
        unique = {}
        for c in pool:
            unique.setdefault(json.dumps({k: c.get(k) for k in ("rules", "lookup", "rounding", "relation")},
                                         sort_keys=True), c)
        scored = []
        for c in unique.values():
            result = evaluate.score(df, meta, c, value)
            evaluate.record(task, value, c, result)
            c["score"] = {k: result[k] for k in ("discovery", "holdout", "total", "fingerprint")}
            c["features"] = features_of(c)
            scored.append(c)
        scored.sort(key=lambda c: (-c["score"]["holdout"][0], -c["score"]["discovery"][0], complexity(c)))
        best = scored[0]
        minimal = (tinfo.get("minimal_sets") or [None])[0]
        out["values"][value] = {
            "relation": relation, "best": best["id"], "ties": ties(scored),
            "cards": cards(df, label_col, value, minimal, info["relation_name"], modes, meta["keys"]) if minimal else [],
            "candidates": scored,
            "residuals": evaluate.score(df, meta, best, value)["wrong"],
        }
    (folder / "pool.json").write_text(json.dumps(out, indent=1, default=str))
    return out
