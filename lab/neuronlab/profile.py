"""Step 1 without LLM: keys, inclusion dependencies, join graph, grain and filter of a target.

Desbordante does the dependency mining:
- HyUCC finds the unique column combinations (keys) of every table;
- Spider finds the unary inclusion dependencies (IND) among all key-like columns of all tables and targets.
The lab then turns them into decisions: a join A.c -> B.d needs an IND into a key of B (a temporal join when the
key needs the version or the valid-from column); the grain of a target is the table whose columns contain the
target key tuples (n-ary inclusion, checked exactly) with the highest reverse coverage; the filter is the column
of the grain that separates target rows from the other rows of the train policies.
"""
import itertools
import json

import desbordante
import polars as pl

from . import paths, schema, store

MAX_UCC = 3
SKIP_UCC = {"NRBOOK"}  # 6.8 M rows: its key BK_BOOKID is checked directly
FREE_TEXT = 30  # C columns at least this long are descriptions, not codes


def _strings(series):
    """Values as normalized text, the common ground of legacy and target columns."""
    if series.dtype == pl.Date:
        return series.dt.strftime("%Y-%m-%d")
    return series.cast(pl.String)


def code_positions(df, name):
    """Fixed-length code columns split by character, e.g. RK_TARKEY -> RK_TARKEY[1] ... RK_TARKEY[7].

    Only columns where every value has the same length, the code has few distinct values and each position few
    modalities: tariff keys yes, policy numbers and zip codes no.
    """
    values = df[name].drop_nulls().unique()
    if values.len() < 2 or values.len() > 300:
        return {}
    lengths = values.str.len_chars().unique()
    if lengths.len() != 1 or lengths[0] < 3:
        return {}
    width = lengths[0]
    parts = {f"{name}[{i + 1}]": df[name].str.slice(i, 1) for i in range(width)}
    counts = [p.drop_nulls().n_unique() for p in parts.values()]
    if max(counts) > 12 or sum(c > 1 for c in counts) < 2:
        return {}
    return {k: v for k, v in parts.items() if v.drop_nulls().n_unique() > 1}


def key_like(table):
    """Columns of a table that can take part in a join: codes, whole numbers, dates (no amounts, no free text)."""
    specs = {c.name: c for c in schema.columns(table)}
    df = store.load(table)
    cols = {}
    for name in df.columns:
        spec = specs.get(name)
        if spec and spec.is_key_like and spec.type != "T" and not (spec.type == "C" and spec.length >= FREE_TEXT):
            cols[name] = df[name]
            if spec.type == "C":
                cols.update(code_positions(df, name))
    return cols


def mine_uccs(table, max_size=MAX_UCC):
    """Minimal unique column combinations of a table (Desbordante HyUCC), smallest first."""
    df = store.load(table)
    if table in SKIP_UCC:
        return [[c] for c in df.columns if df[c].n_unique() == df.height]
    frame = df.select(pl.all().cast(pl.String).fill_null("")).to_pandas()
    algorithm = desbordante.ucc.algorithms.HyUCC()
    algorithm.load_data(table=frame)
    algorithm.execute(threads=0)
    uccs = (sorted(df.columns[i] for i in u.indices) for u in algorithm.get_uccs())
    return sorted((u for u in uccs if len(u) <= max_size), key=lambda u: (len(u), u))


def mine_inds(columns):
    """Unary inclusion dependencies {(lhs, rhs)} among named value sets (Desbordante Spider)."""
    names = [n for n, values in columns.items() if values]
    frames = [pl.DataFrame({"v": sorted(columns[n])}).to_pandas() for n in names]
    algorithm = desbordante.ind.algorithms.Spider()
    algorithm.load_data(tables=frames)
    algorithm.execute(threads=0)
    pairs = set()
    for ind in algorithm.get_inds():
        lhs, rhs = names[ind.get_lhs().table_index], names[ind.get_rhs().table_index]
        if lhs != rhs:
            pairs.add((lhs, rhs))
    return sorted(pairs)


def legacy_profile():
    """Keys and INDs of the legacy tables plus the key-like columns of all targets; cached, task independent."""
    cache = paths.CACHE / "profile_legacy.json"
    if cache.exists():
        return json.loads(cache.read_text())
    values = {}
    for table in store.tables():
        if table in ("NRDICT", "NRCODE"):
            continue
        for name, series in key_like(table).items():
            values[f"{table}.{name}"] = set(_strings(series).drop_nulls().unique().to_list()) - {""}
    for name in store.target_names():
        df = store.target(name)
        for col in df.columns:
            if not isinstance(df[col].dtype, pl.Decimal):
                values[f"{name}.{col}"] = set(_strings(df[col]).drop_nulls().unique().to_list())
    result = {
        "uccs": {t: mine_uccs(t) for t in store.tables() if t not in ("NRDICT", "NRCODE")},
        "inds": mine_inds(values),
        "distinct": {name: len(v) for name, v in values.items()},
    }
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(result, indent=1))
    return result


def split(qualified):
    table, column = qualified.split(".", 1)
    return table, column


def base(column):
    """`RK_TARKEY[6]` -> `RK_TARKEY`."""
    return column.split("[", 1)[0]


def join_kind(table, column, uccs):
    """'plain' if `column` alone is a key of `table`, 'temporal' if it is with the version or valid-from column."""
    keys = [set(u) for u in uccs.get(table, [])]
    if {column} in keys:
        return "plain"
    period = schema.validity(table)
    if period:
        start, _, version = period
        if any(k in ({column, version}, {column, start}) for k in keys):
            return "temporal"
    return None


def joins(legacy):
    """Join edges A.c -> B.d: an IND into a key of B, with the same abbreviation or enough shared values.

    Without the same abbreviation the IND must cover at least 10 % of the key's values and have 20 distinct
    values: small numbers such as instalment numbers 1..300 are contained in every ID column by chance.
    """
    edges = []
    distinct = legacy["distinct"]
    for lhs, rhs in legacy["inds"]:
        (ta, ca), (tb, cb) = split(lhs), split(rhs)
        if ta == tb or not ta.startswith("NR") or not tb.startswith("NR") or "[" in cb:
            continue
        kind = join_kind(tb, cb, legacy["uccs"])
        if kind is None:
            continue
        same_key = "[" not in ca and ca.split("_", 1)[1] == cb.split("_", 1)[1]
        shared = distinct.get(lhs, 0) >= 20 and distinct.get(lhs, 0) >= 0.1 * distinct.get(rhs, 1)
        if same_key or shared:
            edges.append({"from": lhs, "to": rhs, "kind": kind,
                          "evidence": "IND + same abbreviation" if same_key else "IND + cardinality"})
    return edges


def _key_frame(df, columns):
    return df.select(_strings(df[c]).alias(f"k{i}") for i, c in enumerate(columns))


MIN_COVERAGE = 0.5


def _grain_candidates(task, keys, legacy):
    """Tables whose columns contain the target tuples of `keys`: missing tuples, uniqueness, reverse coverage."""
    tgt = store.target(task)
    targets_keys = _key_frame(tgt, keys).unique()
    policies = list(set(_strings(tgt[keys[0]]).unique().to_list()))
    by_table = {}
    for lhs, rhs in legacy["inds"]:
        source, column = split(lhs)
        if source == task and column in keys and rhs.startswith("NR") and "[" not in rhs:
            table, col = split(rhs)
            by_table.setdefault(table, {}).setdefault(column, []).append(col)
    candidates = []
    for table, mapping in by_table.items():
        if set(mapping) != set(keys):
            continue
        df = store.load(table)
        for combo in itertools.product(*(mapping[k] for k in keys)):
            if len(set(combo)) < len(combo):
                continue
            rows = _key_frame(df, combo)
            distinct = rows.unique()
            missing = targets_keys.join(distinct, on=list(distinct.columns), how="anti").height
            on_train = distinct.filter(pl.col("k0").is_in(policies))
            candidates.append({"table": table, "columns": dict(zip(keys, combo)), "missing": missing,
                               "unique": distinct.height == rows.height,
                               "coverage": round(targets_keys.height / max(1, on_train.height), 4),
                               "rows_on_train_policies": on_train.height})
    # complete inclusion first, then tables where the key is unique (one row per target row), then coverage
    candidates.sort(key=lambda c: (c["missing"] > 0, not c["unique"], -c["coverage"], c["table"]))
    return candidates, targets_keys.height


def grain(task, legacy):
    """Table whose columns contain the target key tuples, ranked by reverse coverage on the train policies.

    When no table contains the whole key with enough coverage (keys such as (policy, year) or (policy, n) of
    future due dates), the grain is the policy-level table and the other key columns stay target inputs.
    """
    keys, _ = store.target_columns(task)
    candidates, rows = _grain_candidates(task, keys, legacy)
    best = candidates[0] if candidates and candidates[0]["missing"] == 0 else None
    fallback = None
    if len(keys) > 1 and (best is None or best["coverage"] < MIN_COVERAGE or not best["unique"]):
        policy_level, _ = _grain_candidates(task, keys[:1], legacy)
        fallback = next((c for c in policy_level if c["missing"] == 0 and c["unique"]), None)
        if fallback:
            best = dict(fallback, kind="policy level", extra_keys=keys[1:])
    return {"best": best, "candidates": candidates[:6], "target_rows": rows}


def filter_rule(task, chosen):
    """The grain column whose values separate target rows from the other rows of the train policies."""
    if not chosen or chosen.get("kind") == "policy level":
        return None
    keys, _ = store.target_columns(task)
    tgt = store.target(task)
    table, columns = chosen["table"], [chosen["columns"][k] for k in keys]
    df = store.load(table)
    policies = _strings(tgt[keys[0]]).unique().to_list()
    df = df.filter(_strings(df[columns[0]]).is_in(policies))
    marks = _key_frame(tgt, keys).unique().with_columns(pl.lit(True).alias("in_target"))
    df = (df.with_columns(_key_frame(df, columns))
            .join(marks, on=[f"k{i}" for i in range(len(keys))], how="left")
            .with_columns(pl.col("in_target").fill_null(False)))
    best = None
    for name in df.columns:
        if name in columns or name.startswith("k") or name == "in_target":
            continue
        categorical = df[name].dtype in (pl.String, pl.Int64, pl.Boolean)
        values = df[name] if categorical else df[name].is_null()
        if values.n_unique() > 20:
            continue
        rates = (df.with_columns(values.alias("_v")).group_by("_v")
                 .agg(pl.col("in_target").mean().alias("rate"), pl.len().alias("rows")))
        errors = int(rates.select(pl.min_horizontal(pl.col("rate"), 1 - pl.col("rate")) * pl.col("rows")).sum().item())
        if best is None or errors < best["errors"]:
            keep = sorted(str(v) for v in rates.filter(pl.col("rate") >= 0.5)["_v"].to_list())
            drop = {str(r["_v"]): r["rows"] for r in rates.filter(pl.col("rate") < 0.5).iter_rows(named=True)}
            best = {"column": name if categorical else f"{name} is null", "keep": keep,
                    "excluded_rows": drop, "errors": errors}
    return best if best and best["excluded_rows"] else None  # every row is in the target: no filter


def profile(task):
    """profile.json of a task: keys, joins, grain, filter."""
    legacy = legacy_profile()
    chosen = grain(task, legacy)
    result = {
        "task": task,
        "keys": {t: [u for u in uccs if len(u) <= 2][:8] for t, uccs in legacy["uccs"].items()},
        "temporal": {t: list(schema.validity(t)) for t in store.tables() if t in schema.dictionary()
                     and schema.validity(t)},
        "joins": joins(legacy),
        "grain": chosen,
        "filter": filter_rule(task, chosen["best"]),
        "inds_of_target": [p for p in legacy["inds"] if p[0].startswith(task + ".")],
    }
    (paths.run_dir(task) / "profile.json").write_text(json.dumps(result, indent=1, default=str))
    return result
