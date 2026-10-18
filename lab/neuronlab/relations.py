"""Relation features between a target value and the inputs of the frame: the space where step 2 clusters.

ratio  value ~ round(x * c)    a rate (commission, charges)
diff   value = x + c           a fixed amount on top of an input
days   value = x + c days      a date shifted from an input date
months value = x + c months    a schedule (due dates), the 31st clipped to shorter months
const  value = c               a constant (fees)
label  value = c               a category (a tax type, a country): the value is its own cluster

When no input gives dense clusters, a second pass relates the value to `previous(value)`, the value of the same
policy one step before (the previous due date, last year's projection): sequences and recurrences.
"""
import dataclasses
import functools
import itertools
import operator

import polars as pl

KINDS = ("ratio", "diff", "days", "months", "const", "label")


@dataclasses.dataclass(frozen=True)
class Relation:
    kind: str
    input: str | None  # frame column, None for const

    @property
    def name(self):
        if self.kind in ("const", "label"):
            return "value"
        symbol = {"ratio": "/", "diff": "-", "days": "- (days)", "months": "- (months)"}[self.kind]
        return f"value {symbol} {self.input}"

    def to_json(self):
        return {"kind": self.kind, "input": self.input}


def numeric(dtype):
    return isinstance(dtype, pl.Decimal) or dtype in (pl.Int64, pl.Int32)


def candidates(frame, meta, value, sequence=False):
    """All relations of a target value column with the usable inputs of the frame.

    The value columns that come before it in the target file are inputs too (collection date - due date, total -
    fees): the function computes the values in file order, so a value never depends on a later one.
    """
    later = meta["values"][meta["values"].index(value):]
    skip = set(meta["keys"]) | set(meta["mapping"].values()) | set(later)
    target = frame[value].dtype
    if target == pl.String:
        return [] if sequence else [Relation("label", None)]
    found = [] if sequence else [Relation("const", None)]
    for name in frame.columns:
        if name in skip or name.endswith("_RAW") or frame[name].null_count() > 0.5 * frame.height:
            continue
        if name.startswith("previous(") != sequence:
            continue
        dtype = frame[name].dtype
        if target == pl.Date and dtype == pl.Date:
            found += [Relation("days", name), Relation("months", name)]
        elif numeric(target) and isinstance(dtype, pl.Decimal) and frame[name].n_unique() > 1:
            found += [Relation("ratio", name), Relation("diff", name)]  # amounts only: no IDs or counters
    return found


def identities(frame, meta, value, top=3):
    """Exact sums among the value columns: value = the sum of some of the values before it, on most rows.

    A cheap check over all subsets (at most a few dozen), e.g. total_charges = the four charges of a statement.
    """
    earlier = [v for v in meta["values"][:meta["values"].index(value)] if numeric(frame[v].dtype)]
    if not numeric(frame[value].dtype) or len(earlier) < 2:
        return []
    found = []
    for size in range(2, len(earlier) + 1):
        for subset in itertools.combinations(earlier, size):
            total = functools.reduce(operator.add, [pl.col(c) for c in subset])
            rows = int(frame.select((pl.col(value) == total).fill_null(False).sum()).item())
            if rows >= 0.5 * frame.height:
                found.append({"sum_of": list(subset), "rows": rows})
    return sorted(found, key=lambda f: -f["rows"])[:top]


def evaluate(frame, relation, value):
    """Float series of the relation, null where it is undefined (division by zero, missing input)."""
    v = pl.col(value)
    if relation.kind == "const":
        expr = v.cast(pl.Float64)
    elif relation.kind == "days":
        expr = (v - pl.col(relation.input)).dt.total_days().cast(pl.Float64)
    elif relation.kind == "months":
        x = pl.col(relation.input)
        expr = ((v.dt.year() - x.dt.year()) * 12 + v.dt.month() - x.dt.month()).cast(pl.Float64)
    elif relation.kind == "diff":
        expr = v.cast(pl.Float64) - pl.col(relation.input).cast(pl.Float64)
    else:
        x = pl.col(relation.input).cast(pl.Float64)
        expr = pl.when(x != 0).then(v.cast(pl.Float64) / x)
    return frame.select(expr.alias("r"))["r"]
