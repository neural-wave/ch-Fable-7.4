"""t5: the values that were changed by hand (tools/detective/llm/013-t5-story.md).

A target value that differs from what the rules calculate is a hand edit or a rule not found yet (the task text).
The rules of t0 to t4 calculate every train value but the hand edits, and every difference left is a whole number
of francs, the NREXCP-listed edits among them: a person typed a new amount. A rule not found yet left cents (the
isolation forest of `tools/detective/noise.py` on earlier rounds). So a value is taken for a hand edit when it
differs from the rule by whole francs.
"""
import datetime as dt
import pathlib

import polars as pl

from accounting import accounting, holdings
from commission import commissions
from projection import maturity_values
from statement import LAST_YEAR, statements
from surrender import surrender_values

CENTS_PER_FRANC = 100
KEYS = {"t0_commission": ["policy_id", "due_nr"], "t2_projected_maturity_value": ["policy_id"],
        "t3_surrender_value": ["policy_id", "valuation_date"], "t4_annual_statement": ["policy_id", "year"]}
STATEMENT = {"BK_POLNR": "policy_id", "YEAR": "year", "PREMIUMS": "premiums", "ENTRY": "entry_charges",
             "ADMIN": "admin_fees", "MANAGEMENT": "management_fees", "RISK": "risk_charges", "TOTAL": "total_charges"}


def target_cents(targets_dir, task: str, keys: list[str], values: list[str]) -> pl.DataFrame | None:
    """The keys and the values in cents of the target file of `task` in `targets_dir`, or None without one."""
    path = pathlib.Path(targets_dir, f"{task}.csv")
    match path.exists():
        case False:
            return None
    rows = pl.read_csv(path, try_parse_dates=True).select(*keys, *values)
    return rows.with_columns(pl.col(values).cast(pl.Decimal(38, 2)).mul(CENTS_PER_FRANC).cast(pl.Int64))


def whole_francs(value: str) -> pl.Expr:
    """Whether the target `value` differs from the rule's by a whole number of francs."""
    gap = pl.col(value).sub(pl.col(f"{value}:rule"))
    return gap.ne(0).and_(gap.mod(CENTS_PER_FRANC).eq(0))


def valuation_dates(targets_dir) -> list[dt.date]:
    """The valuation dates of the surrender values in `targets_dir` (the end of LAST_YEAR without them)."""
    path = pathlib.Path(targets_dir, "t3_surrender_value.csv")
    match path.exists():
        case False:
            return [dt.date(LAST_YEAR, 12, 31)]
    return pl.read_csv(path, try_parse_dates=True)["valuation_date"].unique().to_list()


def rule_values(legacy_dir, dates: list[dt.date]) -> dict[str, pl.DataFrame]:
    """{task: the keys and the values in cents that the rules calculate, named as in the target files}."""
    bookings = accounting(legacy_dir, max(dt.date(LAST_YEAR, 12, 31), *dates))
    surrender = surrender_values(legacy_dir, holdings(bookings, dates))
    return {"t0_commission": commissions(legacy_dir), "t2_projected_maturity_value": maturity_values(legacy_dir),
            "t3_surrender_value": surrender.select(policy_id="BK_POLNR", valuation_date="VALUATION",
                                                   surrender_value="SURRENDER_VALUE"),
            "t4_annual_statement": statements(legacy_dir, bookings).rename(STATEMENT)}


def hand_edits(targets_dir, task: str, made: pl.DataFrame) -> list[tuple]:
    """(task, key) of every target row of `task` with a value that differs from `made` (the keys KEYS[task] and
    the values in cents, named as in the target file) by whole francs."""
    keys = KEYS[task]
    values = made.drop(keys).columns
    target = target_cents(targets_dir, task, keys, values)
    match target:
        case None:
            return []
    rules = made.select(*[pl.col(key).cast(target.schema[key]) for key in keys],
                        *[pl.col(value).alias(f"{value}:rule") for value in values])
    edited = target.join(rules, on=keys).filter(pl.any_horizontal(whole_francs(value) for value in values))
    return [(task, key) for key in edited.select(keys).iter_rows()]


def outliers(legacy_dir, targets_dir) -> set[tuple]:
    """{(task, key)} of the target values in `targets_dir` that differ from the rules by whole francs."""
    made = rule_values(legacy_dir, valuation_dates(targets_dir))
    return {edit for task, values in made.items() for edit in hand_edits(targets_dir, task, values)}
