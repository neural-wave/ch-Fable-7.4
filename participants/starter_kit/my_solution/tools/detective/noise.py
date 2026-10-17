"""Separate the rules from the noise (§6 of the task): an isolation forest on the differences that remain.

When the rules explain almost everything, a difference is either a rule not found yet or a value changed by hand.
A rule not found yet repeats: many rows with the same difference (a cent of rounding), or differences that cancel
within a policy (an amount booked in the next year). A hand edit is rare and stands alone: a person typed a new
amount. An isolation forest isolates the
rows that are few and different, from features of the difference alone, so it needs no labels; NREXCP, the
incomplete list of hand edits, only checks what it found.
"""
import json

import numpy as np
import polars as pl
from sklearn.ensemble import IsolationForest

from detective.load import load
from detective.report import REPORTS
from detective.residuals import DIFF, residuals
from detective.spec import TaskSpec

SEED = 0
CENT = 100


def listed(spec: TaskSpec) -> pl.DataFrame:
    """The first key column of `spec` and LISTED: the entities with a hand edit of this target in NREXCP."""
    exceptions = load("NREXCP").filter(pl.col("EX_TARGET").str.starts_with(f"{spec.target}."))
    return exceptions.select(pl.col("EX_POLNR").alias(spec.keys[0])).unique().with_columns(LISTED=pl.lit(True))


def difference_features(spec: TaskSpec, table: pl.DataFrame) -> tuple[pl.DataFrame, list[str]]:
    """(the wrong rows of a residual table with features of their differences, the feature names): per value the
    size (log10), the cents part, the share of the target value, how often the same difference occurs (log10) and
    how much the differences of the entity add up rather than cancel (0 to 1); and how many values of the row
    differ."""
    wrong = table.filter(pl.col("STATUS").eq("wrong"))
    numbers = [value for value in spec.values if wrong.schema[f"{value}{DIFF}"].is_numeric()]
    features = {}
    for value in numbers:
        signed = pl.col(f"{value}{DIFF}")
        gap = signed.abs()
        net = signed.sum().over(spec.keys[0]).abs().truediv(gap.sum().over(spec.keys[0])).fill_nan(0)
        features |= {f"{value}:size": gap.add(1).log10(), f"{value}:cents": gap.mod(CENT),
                     f"{value}:share": gap.truediv(pl.col(value).abs().add(1)),
                     f"{value}:frequency": pl.len().over(signed).log10(), f"{value}:net": net}
    differing = pl.sum_horizontal([pl.col(f"{value}{DIFF}").ne(0).cast(pl.Int32) for value in numbers])
    described = wrong.with_columns(**features, VALUES_DIFFERING=differing)
    return described, [*features, "VALUES_DIFFERING"]


def isolate(spec: TaskSpec, predicted: pl.DataFrame) -> pl.DataFrame:
    """The wrong rows of the rule `predicted` with ANOMALY (the isolation forest's score, higher is stranger),
    FLAGGED (isolated as an anomaly) and LISTED (the entity has a hand edit of the target in NREXCP)."""
    described, names = difference_features(spec, residuals(spec, predicted))
    matrix = described.select(names).fill_null(0).to_numpy()
    forest = IsolationForest(random_state=SEED).fit(matrix)
    scored = described.with_columns(ANOMALY=pl.Series(np.negative(forest.score_samples(matrix))),
                                    FLAGGED=pl.Series(np.equal(forest.predict(matrix), -1)))
    return scored.join(listed(spec), on=spec.keys[0], how="left").with_columns(pl.col("LISTED").fill_null(False))


def common(rows: pl.DataFrame, spec: TaskSpec) -> dict[str, list[dict]]:
    """{value: the most common differences of `rows`, with their counts}."""
    return {value: rows.group_by(f"{value}{DIFF}").len().sort("len", descending=True).head(5).rename(
        {f"{value}{DIFF}": "DIFF", "len": "ROWS"}).to_dicts() for value in spec.values}


def write_noise(spec: TaskSpec, round_name: str, scored: pl.DataFrame, notes: str = "") -> str:
    """Write `reports/<target>/<round>-noise.md` and `.json`: what the forest isolated, checked against NREXCP."""
    flagged, kept = scored.filter(pl.col("FLAGGED")), scored.filter(pl.col("FLAGGED").not_())
    prefix = f"{spec.target}/{round_name}-noise"
    whole = flagged.filter(pl.all_horizontal(pl.col(f"{value}{DIFF}").mod(CENT).eq(0) for value in spec.values
                                             if scored.schema[f"{value}{DIFF}"].is_numeric()))
    found = [{"ID": f"{prefix}/N1", "TEXT": f"isolated {flagged.height} of {scored.height} differences as "
                                            f"anomalies, {whole.height} of them in whole francs"},
             {"ID": f"{prefix}/N2", "TEXT": f"NREXCP lists {scored['LISTED'].sum()} of the differing entities: "
                                            f"{flagged['LISTED'].sum()} isolated, {kept['LISTED'].sum()} not"}]
    lines = [f"# {spec.target}, {round_name}-noise", "", notes, "", "## Findings", "",
             *[f"- **{item['ID']}** {item['TEXT']}" for item in found], "", "## Isolated (most common differences)", "",
             *[f"- {value}: {rows}" for value, rows in common(flagged, spec).items()], "",
             "## Not isolated (most common differences)", "",
             *[f"- {value}: {rows}" for value, rows in common(kept, spec).items()], ""]
    folder = REPORTS / spec.target
    folder.mkdir(parents=True, exist_ok=True)
    text = "\n".join(lines)
    (folder / f"{round_name}-noise.md").write_text(text)
    (folder / f"{round_name}-noise.json").write_text(json.dumps({"findings": found}, indent=1))
    return text
