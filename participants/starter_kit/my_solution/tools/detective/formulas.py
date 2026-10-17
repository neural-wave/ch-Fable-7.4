"""Find the formula: search the choices a rule leaves open, and test every candidate for exact matches.

- `fill_holes` (program synthesis by sketching): the LLM writes a rule with holes, parameters for the choices the
  story leaves open (which date a lookup uses, how a result is rounded). The search runs every combination and
  counts the exact matches, on 80 % of the entities to choose and on the other 20 % to check (`held_out`).
  `where` limits the search to the target rows whose features meet a condition found by a decision tree, so
  the simplest part of a task can be solved first; `only` does the same with a condition on the target columns
  (one booking type), which needs no features.
"""
import itertools
from collections.abc import Callable

import polars as pl

from detective.residuals import residuals
from detective.spec import TaskSpec

HOLD_OUT = 5  # one entity in HOLD_OUT is held out


def held_out(spec: TaskSpec) -> pl.Expr:
    """Whether a row belongs to the held-out entities: a fixed hash of the first key."""
    return pl.col(spec.keys[0]).hash(seed=7).mod(HOLD_OUT).eq(0)


def scored(spec: TaskSpec, predicted: pl.DataFrame, expected: pl.DataFrame, value: str | None = None) -> dict:
    """RIGHT, TOTAL, RIGHT_HELD_OUT and TOTAL_HELD_OUT of the rows `predicted` against `expected`; with `value`,
    a row counts when that value is right."""
    table = residuals(spec, predicted, expected).filter(pl.col("STATUS").ne("extra"))
    right = pl.col(value).eq_missing(pl.col(f"{value}_RULE")) if value else pl.col("STATUS").eq("right")
    flags = table.select(right=right, held=held_out(spec))
    return {"RIGHT": flags.filter(~pl.col("held"))["right"].sum(), "TOTAL": flags.filter(~pl.col("held")).height,
            "RIGHT_HELD_OUT": flags.filter("held")["right"].sum(), "TOTAL_HELD_OUT": flags.filter("held").height}


def subset(spec: TaskSpec, where: pl.Expr | None, only: pl.Expr | None = None) -> pl.DataFrame:
    """The target rows that meet `only` and whose features meet `where` (all rows without them)."""
    from detective.discover import cached_features  # the features are built once per process
    rows = spec.frame() if only is None else spec.frame().filter(only)
    if where is None:
        return rows
    chosen = cached_features(spec).filter(where).select(spec.keys)
    return rows.join(chosen, on=list(spec.keys), how="semi")


def fill_holes(sketch: Callable[..., pl.DataFrame], holes: dict[str, list], spec: TaskSpec,
               value: str | None = None, where: pl.Expr | None = None, only: pl.Expr | None = None) -> list[dict]:
    """Every combination of the `holes` values run through `sketch`, best first, with its exact matches (of
    `value` only, if given) on the target rows that meet `where` and `only`."""
    expected = subset(spec, where, only)
    results = []
    for values in itertools.product(*holes.values()):
        choice = dict(zip(holes, values, strict=True))
        results.append({"HOLES": choice, **scored(spec, sketch(**choice), expected, value)})
    return sorted(results, key=lambda result: (-result["RIGHT"], -result["RIGHT_HELD_OUT"]))
