"""Step 6: exact score of a candidate, discovery/holdout split, ledger of every evaluation.

A candidate is data, not code: a relation (ratio/diff/days/const with an input column), a source of constants
(rules "when -> constant", or a lookup into a parameter table) and a rounding mode. The interpreter computes the
value of every frame row exactly (Int128 units, the same rounding as `decimal`) and compares it with the target
value, which is what `scoring.accuracy` does for a whole task.
"""
import datetime as dt
import hashlib
import json
import zlib
from decimal import Decimal

import polars as pl

from . import exact, paths, schema, store
from .cluster import scale_of

HOLDOUT = 5  # policies with crc32(policy_id) % 5 == 0 are the holdout


def holdout(df, policy_col):
    ids = df[policy_col].unique().to_list()
    held = [p for p in ids if zlib.crc32(p.encode()) % HOLDOUT == 0]
    return df[policy_col].is_in(held)


def condition(clause):
    name, op, value = clause
    col = pl.col(name).cast(pl.String)
    return col == value if op == "=" else (col != value) | col.is_null()


def rule_constants(rules):
    """Expression: the constant of the first rule whose conditions hold (as text), else null."""
    expr = pl.lit(None, dtype=pl.String)
    for rule in reversed(rules):
        cond = pl.all_horizontal([condition(c) for c in rule["when"]]) if rule["when"] else pl.lit(True)
        expr = pl.when(cond).then(pl.lit(str(rule["then"]))).otherwise(expr)
    return expr


def lookup_constants(df, lookup):
    """Series: value of the parameter table row whose key columns equal the row's features (valid on the anchor)."""
    table = store.load(lookup["table"])
    keys = lookup["keys"]  # {table column: frame column}
    period = schema.validity(lookup["table"])
    right = table.select(list(keys) + [lookup["column"]] + (list(period[:2]) if period else []))
    right = right.with_columns(pl.col(c).cast(pl.String) for c in keys)
    left = df.select(pl.col(f).cast(pl.String).alias(c) for c, f in keys.items()).with_row_index("_row")
    anchor = lookup.get("anchor")
    if anchor:
        left = left.with_columns(df[anchor].alias("_on"))
    joined = left.join(right, on=list(keys), how="left")
    if period:
        start, end, _ = period
        if anchor:
            joined = joined.filter((pl.col(start) <= pl.col("_on")) & (pl.col("_on") <= pl.col(end)) | pl.col(start).is_null())
        joined = joined.sort(start, descending=True, nulls_last=True)
    joined = joined.unique("_row", keep="first")
    values = left.select("_row").join(joined.select("_row", lookup["column"]), on="_row", how="left").sort("_row")
    return values[lookup["column"]].cast(pl.String)


def constants(df, candidate):
    if candidate.get("lookup"):
        return lookup_constants(df, candidate["lookup"])
    return df.select(rule_constants(candidate["rules"]).alias("c"))["c"]


def predicted(df, candidate, value):
    """Series of the values the candidate computes, in the type of the target column (Decimal or Date)."""
    relation = candidate["relation"]
    c = constants(df, candidate)
    kind, x = relation["kind"], relation.get("input")
    work = df.select([pl.col(x)] if x else [pl.lit(0).alias("_none")]).with_columns(c.alias("_c"))
    if kind == "days":
        expr = pl.col(x) + pl.duration(days=pl.col("_c").cast(pl.Int64))
        return work.select(expr.alias("p"))["p"]
    if kind == "months":
        expr = pl.col(x).dt.offset_by(pl.concat_str(pl.col("_c").cast(pl.Int64).cast(pl.String), pl.lit("mo")))
        return work.select(expr.alias("p"))["p"]
    k = max((exact.constant(s)[1] for s in c.drop_nulls().unique().to_list()), default=0)
    cc = exact.scaled(pl.col("_c").cast(pl.Decimal(38, k)), k)
    sv = scale_of(df[value].dtype)
    if kind == "const":
        units, scale = cc, k
    elif kind == "diff":
        sx = scale_of(df[x].dtype)
        scale = max(sx, k)
        units = exact.scaled(pl.col(x), scale) + cc * 10 ** (scale - k)
    else:
        sx = scale_of(df[x].dtype)
        units = exact.round_to(exact.scaled(pl.col(x), sx) * cc, sx + k, sv,
                               candidate.get("rounding", "ROUND_HALF_UP"))
        scale = sv
    unit = pl.lit(Decimal(1).scaleb(-scale), dtype=pl.Decimal(38, scale))
    return work.select((units.cast(pl.Decimal(38, 0)) * unit).alias("p"))["p"]


def correct(df, candidate, value):
    """Boolean series: the candidate reproduces the target value of each row exactly."""
    p = predicted(df, candidate, value)
    if df[value].dtype == pl.Date:
        return (p == df[value]).fill_null(False)
    s = max(scale_of(df[value].dtype), scale_of(p.dtype))
    both = pl.DataFrame({"p": p, "v": df[value]})
    return both.select((exact.scaled(pl.col("p"), s) == exact.scaled(pl.col("v"), s)).fill_null(False))["p"]


def score(df, meta, candidate, value):
    """{"discovery": [ok, n], "holdout": [ok, n], "total": [ok, n], "wrong": [keys...], "fingerprint": ...}."""
    ok = correct(df, candidate, value)
    held = holdout(df, meta["keys"][0])
    wrong = df.filter(~ok).select(meta["keys"])
    digest = hashlib.sha1(json.dumps(sorted(map(list, wrong.rows())), default=str).encode()).hexdigest()[:12]
    return {
        "discovery": [int((ok & ~held).sum()), int((~held).sum())],
        "holdout": [int((ok & held).sum()), int(held.sum())],
        "total": [int(ok.sum()), df.height],
        "wrong": wrong.rows(),
        "fingerprint": digest,
    }


def record(task, value, candidate, result):
    """Append one evaluation to the task ledger."""
    entry = {"time": dt.datetime.now().isoformat(timespec="seconds"), "task": task, "value": value,
             "candidate": candidate["id"], "origin": candidate.get("origin", ""),
             **{k: result[k] for k in ("discovery", "holdout", "total", "fingerprint")}}
    with open(paths.run_dir(task) / "ledger.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return entry


def as_decimal(text):
    return Decimal(str(text))
