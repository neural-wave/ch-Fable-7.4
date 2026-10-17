"""Find the formula (§6 of the task): recover the rates and factors of a rule from its inputs and outputs.

- `factors`: robust linear regression (Huber, no intercept) of a target on candidate terms; the coefficients are
  the factors, approximately, and the rows far off the fit are the ones a single factor does not explain
- `exact_factor`: an integer factor, in units of `scale`, that reproduces every target exactly after the
  rounding `rounding` (Z3); the regression gives the range to search, the solver the one value that fits every
  row to the cent, or none
"""
import numpy as np
import polars as pl
import z3
from sklearn.linear_model import HuberRegressor

from detective.report import REPORTS

SAMPLE = 400  # the rows Z3 is given: enough to pin a factor, few enough to stay fast
SEED = 0


def factors(rows: pl.DataFrame, target: str, terms: list[str]) -> dict[str, float]:
    """{term: coefficient} of the robust fit of `target` on `terms`, and OUTLIERS, the share of rows the fit
    treats as outliers."""
    model = HuberRegressor(fit_intercept=False, max_iter=1000).fit(rows.select(terms).to_numpy().astype(float),
                                                                    rows[target].to_numpy().astype(float))
    return {**dict(zip(terms, model.coef_.tolist())), "OUTLIERS": float(np.mean(model.outliers_))}


def rounded_by(numerator, denominator: int, rounding: str):
    """`numerator` / `denominator` as a Z3 integer, cut off ("down") or rounded half up ("half_up")."""
    halves = {"down": 0, "half_up": denominator // 2}
    return (numerator + halves[rounding]) / denominator


def exact_factor(rows: pl.DataFrame, target: str, term: str, scale: int, rounding: str,
                 low: int, high: int) -> int | None:
    """The integer k between `low` and `high` with `target` = round(`term` x k / `scale`) on every row (a sample
    of SAMPLE rows), by `rounding`; None when no k fits."""
    chosen = rows.sample(min(SAMPLE, rows.height), seed=SEED)
    factor = z3.Int("k")
    solver = z3.Solver()
    solver.add(factor >= low, factor <= high)
    for amount, value in chosen.select(target, term).iter_rows():
        solver.add(rounded_by(factor * value, scale, rounding) == amount)
    return solver.model()[factor].as_long() if solver.check() == z3.sat else None


def write_formulas(target: str, round_name: str, found: list[dict], notes: str = "") -> str:
    """Write `reports/<target>/<round>-formulas.md`: one finding (F1, F2, ...) per group with what the regression
    and the solver recovered."""
    prefix = f"{target}/{round_name}-formulas"
    lines = [f"# {target}, {round_name}-formulas", "", notes, "", "| Finding | Group | Rows | Regression | Exact (Z3) |",
             "| --- | --- | --- | --- | --- |",
             *[f"| {prefix}/F{number} | {row['GROUP']} | {row['ROWS']} | {row['REGRESSION']} | {row['EXACT']} |"
               for number, row in enumerate(found, 1)], ""]
    folder = REPORTS / target
    folder.mkdir(parents=True, exist_ok=True)
    text = "\n".join(lines)
    (folder / f"{round_name}-formulas.md").write_text(text)
    return text
