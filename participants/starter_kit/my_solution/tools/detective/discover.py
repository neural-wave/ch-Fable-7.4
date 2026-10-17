"""One round of the discovery loop: from the rows a rule calculates to the findings about the rows it misses.

    from detective.discover import discover
    discover(spec, predicted, "r1", notes="baseline from the story")

1. residuals: the rule's values next to the target values (`residuals`)
2. features: what the export knows about every target row (`features`)
3. conditions: a decision tree on the wrong rows and the change points along every date (`conditions`)
4. report: the findings with ids, for the LLM that writes the next version of the rule (`report`)

A missing row (a target row the rule does not calculate) counts as wrong; an extra row has no target to learn
from and only shows in the counts. With `value`, the round looks at one value column only, and the other value
columns of the target row become features: a collection date can depend on the due date.
"""
import functools
import pathlib

import polars as pl

from detective.conditions import change_points, tree
from detective.features import derived, features
from detective.report import write
from detective.residuals import DIFF, RULE, residuals
from detective.spec import TaskSpec


@functools.cache
def cached_features(spec: TaskSpec) -> pl.DataFrame:
    """The features of a target, built once per process."""
    return features(spec)


def learning_table(spec: TaskSpec, table: pl.DataFrame, value: str | None = None,
                   context: tuple[str, ...] = ()) -> tuple[pl.DataFrame, pl.Series]:
    """The features of the target rows and whether the rule got each of them wrong; the values the rule is judged
    on and its own columns are left out, so the tree cannot learn from the answer. `context` are target values
    that the judged value may depend on (a collection date on its due date)."""
    scored = table.filter(pl.col("STATUS").ne("extra"))
    flag = (pl.col(value).ne_missing(pl.col(f"{value}{RULE}")) if value else pl.col("STATUS").ne("right")).alias("WRONG")
    rows = derived(scored.select(*spec.keys, *context, flag), [])
    joined = rows.join(cached_features(spec).drop(spec.values), on=list(spec.keys), how="left")
    hidden = [column for column in joined.columns if column.endswith((RULE, DIFF))]
    return joined.drop("WRONG", *hidden), joined["WRONG"]


def discover(spec: TaskSpec, predicted: pl.DataFrame, round_name: str, notes: str = "", value: str | None = None,
             context: tuple[str, ...] = (), where: pl.Expr | None = None, only: pl.Expr | None = None) -> pathlib.Path:
    """Run one round on the rows `predicted` (keys and values of the spec) and write its report; with `where` and
    `only`, only on the target rows that meet them (`formulas.subset`)."""
    from detective.formulas import subset
    table = residuals(spec, predicted, subset(spec, where, only))
    frame, wrong = learning_table(spec, table, value, context)
    rules = tree(frame, wrong) if wrong.any() else []
    changes = change_points(frame, wrong) if wrong.any() else []
    return write(spec, round_name, table, rules, changes, notes)
