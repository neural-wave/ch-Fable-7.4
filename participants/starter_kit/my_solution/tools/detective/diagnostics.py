"""Diagnostic targets made from the export: what the export shows of a step that the rules must calculate.

NRBOOK keeps every booking with its dates, but not the amounts and units of the premium and charge bookings: a
new system has to make these bookings itself, from the premiums, the parameters and the market data. The dates
Neuron gave them are then a target for the rule that makes them (the task text: NRBOOK is there to understand and
debug the accounting, not as a source for the formula). `diagnostic` writes such a frame like a target file, so
the whole discovery loop (spec, features, residuals, tree, search) works on it unchanged.
"""
import polars as pl

from detective.load import CACHE
from detective.spec import TaskSpec, spec_for

DIAGNOSTICS = CACHE / "diagnostics"


def diagnostic(name: str, rows: pl.DataFrame, values: tuple[str, ...]) -> TaskSpec:
    """The TaskSpec of `rows` (key columns first, then `values`) written as the target file `name`."""
    DIAGNOSTICS.mkdir(parents=True, exist_ok=True)
    rows.write_csv(DIAGNOSTICS / f"{name}.csv", date_format="%Y-%m-%d")
    return spec_for(name, values, DIAGNOSTICS)


def part(spec: TaskSpec, name: str, only: pl.Expr) -> TaskSpec:
    """The rows of a target that meet `only` (one booking type) as a target of their own, so the features are
    built for these rows alone."""
    return diagnostic(name, spec.frame().filter(only), spec.values)


def marked(candidates: pl.DataFrame, export: pl.DataFrame, made: pl.DataFrame, names: dict[str, str],
           value: str) -> tuple[pl.DataFrame, pl.DataFrame]:
    """(export, rules): one row per candidate (its columns `names`, renamed by it) with `value`, 1 when `export`
    has it and 1 when `made` has it. A rule that makes a row the export does not have is wrong here, where a
    target of the export rows alone would leave it out."""
    keys = list(names)
    unique = candidates.select(keys).unique()
    frames = [unique.join(found.select(keys).unique().with_columns(pl.lit(1).alias(value)), on=keys, how="left")
              for found in (export, made)]
    return tuple(frame.with_columns(pl.col(value).fill_null(0)).rename(names).sort(list(names.values()))
                 for frame in frames)
