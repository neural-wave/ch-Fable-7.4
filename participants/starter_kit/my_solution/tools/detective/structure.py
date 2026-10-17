"""Find the structure (§6 of the task): which columns matter for the rows a rule misses, and which policies
behave alike. Both help to decide where to look first, before a tree or a search pins the rule down.

- `importance`: a random forest learns from the features which rows the current rule gets wrong; the permutation
  importance on held-out rows ranks the columns (shuffling a column that matters spoils the forest's guesses).
- `clusters`: the entities (policies) grouped by how often the rule misses them and by the columns that matter
  (k-means on standardized columns, k by the silhouette); a cluster where the rule is wrong far more often than
  elsewhere is a group with a rule of its own.
"""
import json

import numpy as np
import polars as pl
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import silhouette_score
from sklearn.model_selection import train_test_split

from detective.conditions import training_rows
from detective.discover import learning_table
from detective.features import numeric
from detective.report import REPORTS
from detective.residuals import residuals
from detective.spec import TaskSpec

SEED = 0
HELD_OUT = 0.3
CHECKED = 5_000  # the held-out rows the permutation importance is measured on
REPEATS = 3
TOP = 10
KS = range(2, 7)
SILHOUETTE_SAMPLE = 5_000
DEVIATIONS = 3  # the features that set a cluster apart most, shown per cluster


def importance(frame: pl.DataFrame, wrong: pl.Series) -> list[dict]:
    """The TOP columns by permutation importance for telling the wrong rows from the right ones: COLUMN, DROP
    (how much the area under the ROC curve falls when the column is shuffled) and SPREAD."""
    numbers = numeric(frame)
    matrix, flags = numbers.to_numpy().astype(float), wrong.to_numpy().astype(bool)
    chosen = training_rows(flags)
    learn, check = train_test_split(chosen, test_size=HELD_OUT, random_state=SEED, stratify=flags[chosen])
    forest = RandomForestClassifier(n_estimators=100, min_samples_leaf=5, class_weight="balanced", n_jobs=-1,
                                    random_state=SEED).fit(np.nan_to_num(matrix[learn]), flags[learn])
    checked = np.random.default_rng(SEED).choice(check, min(CHECKED, check.size), replace=False)
    result = permutation_importance(forest, np.nan_to_num(matrix[checked]), flags[checked], n_repeats=REPEATS,
                                    scoring="roc_auc", random_state=SEED, n_jobs=-1)
    ranked = np.argsort(-result.importances_mean)[:TOP]
    return [{"COLUMN": numbers.columns[index], "DROP": float(result.importances_mean[index]),
             "SPREAD": float(result.importances_std[index])} for index in ranked]


def entity_profiles(spec: TaskSpec, frame: pl.DataFrame, wrong: pl.Series, columns: list[str]) -> pl.DataFrame:
    """One row per entity (the first key): WRONG_SHARE and the mean of the numeric features `columns` of its
    rows."""
    entity = spec.keys[0]
    numbers = numeric(frame.drop(entity)).select(columns)
    rows = pl.concat([frame.select(entity), numbers, pl.DataFrame({"WRONG_SHARE": wrong.cast(pl.Float64)})],
                     how="horizontal")
    return rows.group_by(entity).mean()


def clusters(spec: TaskSpec, frame: pl.DataFrame, wrong: pl.Series, columns: list[str]) -> list[dict]:
    """The clusters of the entities by WRONG_SHARE and the numeric features `columns`: SIZE, WRONG_SHARE and
    APART, the features whose cluster mean lies furthest from the overall mean (in standard deviations); clusters
    with the most wrong rows first."""
    profiles = entity_profiles(spec, frame, wrong, columns)
    columns = [column for column in profiles.columns if column != spec.keys[0]]
    raw = np.nan_to_num(profiles.select(columns).to_numpy().astype(float))
    spread = raw.std(axis=0)
    usable = spread > 0
    scaled = (raw[:, usable] - raw[:, usable].mean(axis=0)) / spread[usable]
    names = [name for name, keep in zip(columns, usable) if keep]
    generator = np.random.default_rng(SEED)
    sample = generator.choice(len(scaled), min(SILHOUETTE_SAMPLE, len(scaled)), replace=False)
    fits = {k: KMeans(n_clusters=k, n_init=10, random_state=SEED).fit(scaled) for k in KS}
    best = max(fits, key=lambda k: silhouette_score(scaled[sample], fits[k].labels_[sample]))
    labels = fits[best].labels_
    found = []
    for label in range(best):
        members = labels == label
        centre = scaled[members].mean(axis=0)
        apart = np.argsort(-np.abs(centre))[:DEVIATIONS]
        found.append({"SIZE": int(members.sum()), "WRONG_SHARE": float(raw[members, columns.index("WRONG_SHARE")].mean()),
                      "APART": [f"{names[index]} {centre[index]:+.1f} sd" for index in apart]})
    return sorted(found, key=lambda row: -row["WRONG_SHARE"] * row["SIZE"])


def structure(spec: TaskSpec, predicted: pl.DataFrame, round_name: str, notes: str = "") -> str:
    """Write `reports/<target>/<round>-structure.md` and `.json`: the permutation importance of the columns for the
    wrong rows (findings I1...) and the clusters of the entities (K1...)."""
    table = residuals(spec, predicted)
    frame, wrong = learning_table(spec, table)
    prefix = f"{spec.target}/{round_name}-structure"
    ranked = [{"ID": f"{prefix}/I{number}", **row} for number, row in enumerate(importance(frame, wrong), 1)]
    mattering = [row["COLUMN"] for row in ranked if row["COLUMN"] in numeric(frame.drop(spec.keys[0])).columns]
    grouped = [{"ID": f"{prefix}/K{number}", **row}
               for number, row in enumerate(clusters(spec, frame, wrong, mattering), 1)]
    lines = [f"# {spec.target}, {round_name}-structure", "", notes, "",
             f"wrong: {int(wrong.sum())} of {len(wrong)}", "", "## Permutation importance (wrong rows)", "",
             *[f"- **{row['ID']}** {row['COLUMN']}: the ROC AUC drops by {row['DROP']:.3f} "
               f"(± {row['SPREAD']:.3f})" for row in ranked], "", "## Clusters of the policies", "",
             *[f"- **{row['ID']}** {row['SIZE']} policies, wrong {row['WRONG_SHARE']:.1%}; apart: "
               f"{', '.join(row['APART'])}" for row in grouped], ""]
    folder = REPORTS / spec.target
    folder.mkdir(parents=True, exist_ok=True)
    text = "\n".join(lines)
    (folder / f"{round_name}-structure.md").write_text(text)
    (folder / f"{round_name}-structure.json").write_text(json.dumps({"importance": ranked, "clusters": grouped},
                                                                     indent=1))
    return text
