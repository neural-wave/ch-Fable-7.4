"""Residuals: a rule's values next to the target values, row by row, exact.

`residuals` joins the rows a rule calculated with the target rows on the keys of the `TaskSpec`:

- STATUS: right (all values equal), wrong (some value differs), missing (a target row the rule has no value
  for) or extra (a value for a key the target does not have). Rows of entities without any target row (the
  first key, e.g. a policy of the public set) are left out: nothing says whether they are right.
- for every value column v: v (target), v_RULE, and v_DIFF = rule minus target (days for dates)
"""
import polars as pl

from detective.spec import TaskSpec

RULE = "_RULE"
DIFF = "_DIFF"


def residuals(spec: TaskSpec, predicted: pl.DataFrame, expected: pl.DataFrame | None = None) -> pl.DataFrame:
    """The target rows and the rule's rows side by side, with STATUS and the differences per value."""
    expected = spec.frame() if expected is None else expected
    entities = expected.select(spec.keys[0]).unique()
    typed = predicted.with_columns(pl.col(key).cast(expected.schema[key]) for key in spec.keys)  # as read from csv
    rule = typed.join(entities, on=spec.keys[0], how="semi").select(
        *spec.keys, *[pl.col(value).alias(f"{value}{RULE}") for value in spec.values])
    both = expected.select(*spec.keys, *spec.values).join(rule, on=list(spec.keys), how="full", coalesce=True)
    equal = pl.all_horizontal([pl.col(value).eq(pl.col(f"{value}{RULE}")) for value in spec.values])
    status = (pl.when(pl.col(spec.values[0]).is_null()).then(pl.lit("extra"))
              .when(pl.col(f"{spec.values[0]}{RULE}").is_null()).then(pl.lit("missing"))
              .when(equal).then(pl.lit("right")).otherwise(pl.lit("wrong")))
    return both.with_columns(STATUS=status, **{f"{value}{DIFF}": difference(both, value) for value in spec.values})


def difference(frame: pl.DataFrame, value: str) -> pl.Expr:
    """Rule minus target: in days for dates, else in the unit of the value."""
    gap = pl.col(f"{value}{RULE}").sub(pl.col(value))
    return gap.dt.total_days() if frame.schema[value] == pl.Date else gap


def summary(table: pl.DataFrame) -> dict[str, int]:
    """{status: rows} of a residual table."""
    return dict(table.group_by("STATUS").len().sort("STATUS").iter_rows())
