"""report.md: the compact summary (about 80 lines) that the LLM of step 5 reads instead of the raw data."""
import json

from . import paths


def _load(folder, name):
    path = folder / name
    return json.loads(path.read_text()) if path.exists() else {}


def _rule(candidate):
    if candidate.get("lookup"):
        lk = candidate["lookup"]
        keys = ", ".join(f"{k} = {v}" for k, v in lk["keys"].items())
        return f"{lk['table']}.{lk['column']}[{keys}]"
    return f"{len(candidate['rules'])} constants on {', '.join(candidate['features'])}"


def build(task, conflicts_shown=8):
    folder = paths.run_dir(task)
    prof, clusters, trees = _load(folder, "profile.json"), _load(folder, "clusters.json"), _load(folder, "trees.json")
    pools, resid = _load(folder, "pool.json"), _load(folder, "residuals.json")
    grain = prof.get("grain", {})
    best = grain.get("best") or {}
    lines = [f"# {task}", ""]
    alt = ", ".join(f"{c['table']} {c['coverage']:.1%}" for c in grain.get("candidates", [])[1:3])
    lines.append(f"Grain: {best.get('table')} {best.get('columns')} (reverse coverage {best.get('coverage', 0):.1%};"
                 f" others: {alt})")
    flt = prof.get("filter") or {}
    if flt:
        lines.append(f"Filter: {flt['column']} in {flt['keep']} (excluded rows {flt['excluded_rows']}, errors {flt['errors']})")
    total_rows = clusters.get("rows", "?")
    for value, info in clusters.get("values", {}).items():
        lines += ["", f"## {value}", ""]
        for s in info.get("identities", []):
            lines.append(f"Exact identity: {value} = {' + '.join(s['sum_of'])} on {s['rows']} of {total_rows} rows")
        if not info.get("relation") and str(info.get("note", "")).startswith("text value"):
            lines.append(f"Not searched: {info['note']}. It may copy an input column read on some date.")
            continue
        if not info.get("relation"):
            lines.append("No relation with dense clusters: a feature or a different relation is missing.")
            hint = info.get("approximate")
            if hint:
                lines.append(f"Approximate only: {hint['relation']} is near {', '.join(hint['centers'])} on "
                             f"{hint['covered']:.0%} of the precise rows, but no center reproduces enough rows exactly. "
                             "The value may be a sum of parts rounded one by one (per instalment, per month), or "
                             "the input may be missing a part.")
            continue
        lines.append(f"Relation: {info['relation_name']}: {len(info['centers'])} clusters, "
                     f"noise {info['noise']}, ambiguous {info['ambiguous']}")
        lines.append("| center | rows | roundings that reproduce all rows |")
        lines.append("|---|---|---|")
        for c in info["centers"]:
            full = [m for m, n in c["modes"].items() if n == c["rows"]]
            lines.append(f"| {c['center']} | {c['rows']} | {' '.join(full)} |")
        for alt in info.get("alternatives", [])[:2]:
            lines.append(f"Other relation: {alt['relation']}: {alt['centers']} clusters, {alt['assigned']} rows exact,"
                         f" noise {alt['noise']}")
        t = trees.get("values", {}).get(value, {})
        if t.get("minimal_sets"):
            sets = "; ".join("{" + ", ".join(s["features"]) + "}" for s in t["minimal_sets"])
            lines.append(f"Optimal trees: errors {t['best']['errors']}, leaves {t['best']['leaves']}; "
                         f"smallest feature sets: {sets}")
            for s in t["minimal_sets"][:1]:
                for f, eq in s["equivalents"].items():
                    if eq:
                        lines.append(f"  {f} is interchangeable with: {', '.join(eq[:8])}")
                if s.get("conflicting_vectors"):
                    lines.append(f"  conflicting vectors (same features, different clusters): {s['conflicting_vectors']}")
            for c in t.get("conflicts", []):
                vec = ", ".join(f"{k} = {v}" for k, v in c["vector"].items())
                spread = ", ".join(f"{k} x {n}" for k, n in c["clusters"].items())
                lines.append(f"  conflicting vector ({vec}): clusters {spread}; example {c['example']}")
            lines.append(f"CART for comparison: {t['cart']['leaves']} leaves on {', '.join(t['cart']['features'])}")
        elif t.get("note"):
            lines.append(t["note"])
        p = pools.get("values", {}).get(value)
        if p:
            cands = {c["id"]: c for c in p["candidates"]}
            win = cands[p["best"]]
            s = win["score"]
            lines.append(f"Best candidate {win['id']}: {_rule(win)}, {win['rounding']}; total {s['total'][0]}/{s['total'][1]},"
                         f" holdout {s['holdout'][0]}/{s['holdout'][1]}")
            if p.get("ties"):
                lines.append(f"Same train rows (the data cannot tell them apart): {', '.join(p['ties'][:6])}")
            others = [c for c in p["candidates"] if c["score"]["fingerprint"] != s["fingerprint"]][:4]
            for c in others:
                lines.append(f"  {c['id']}: {_rule(c)}, {c['rounding']}: total {c['score']['total'][0]}")
            for card in p.get("cards", [])[:8]:
                cond = " and ".join(f"{a} {op} {b}" for a, op, b in card["when"])
                lines.append(f"  card {card['id']}: {cond} -> {card['then']['center']} ({card['support_rows']} rows,"
                             f" e.g. {card['examples'][:1]})")
        r = resid.get("values", {}).get(value)
        if r:
            pairs = ", ".join(f"{k} x {n}" for k, n in list(r["structure"].items())[:6]) or "none"
            lines.append(f"Residuals: {r['residuals']} rows. Fit another cluster (a condition is missing): {pairs}."
                         f" Noise {r['noise']} (whole-unit deltas {r['whole_unit_deltas']}, listed in NREXCP"
                         f" {r['in_NREXCP']}), ambiguous {r['ambiguous']}")
            for row in r["rows"][:conflicts_shown]:
                lines.append(f"  {row['key']} {row['class']}: target {row['target']}, computed {row['computed']},"
                             f" delta {row['delta']}")
    text = "\n".join(lines) + "\n"
    (folder / "report.md").write_text(text)
    return text
