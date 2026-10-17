"""Generic features of target rows: what the export knows about each row, collected along the relation graph.

Starting from the anchor table of a target (`spec.TaskSpec`), every relation of `schema.relations` leads to more
columns, up to DEPTH steps away:

- a relation to a key adds the one row it points to (a premium item -> its event)
- a relation to a versioned table adds the version valid on a date, once for every date of the anchor row and
  once for the last version (`@PR_RCVDT`, `@PR_DUEDT`, `@last`). Which date a rule uses is a question for the
  search, so the features keep all of them.
- a relation from another table whose referencing columns are unique adds that row too (the policy -> its
  insured risk; an event -> the reversal that cancels it, named `^EV_REVNR`)

A table met twice gets the relation in its column names (`EV_EVTTP.EV_REVNR`). Tables with many rows per entity
(the premium items of a policy) give aggregates per entity instead (`entity_aggregates`): how many rows, and the
first and last of every date with its day of the month. Then `derived` adds what rules often depend on: parts of
dates, public holidays of the local calendar, days between two dates, the cents of amounts, and whether a
versioned value changed between two dates. Last, `pruned` drops the columns that say nothing new: constant ones,
and copies of an earlier column (a table without versions is the same in every snapshot).

The local calendar is the one of the story (a company in Ticino): `LOCAL` flags its holidays, and `:holiday`
names the holiday of any Swiss canton on that day, so a rule that skips only some holidays can be found too.
"""
import functools
import itertools
import pathlib

import holidays
import polars as pl

from detective.load import LEGACY, columns, load
from detective.schema import VALIDITY, abbreviation, keyed, keys, relations
from detective.spec import TaskSpec, holders

DEPTH = 3
LAST = "last"
FEW = 12  # a text column with at most this many values becomes one feature per value
NAMES = 40  # the same for the names of holidays
SKIPPED = ("NRBOOK", "NRTAXB")  # tables with many rows per entity: aggregates, not features
COUNTRY, LOCAL = "CH", "TI"  # the calendar of the story: NeuralWave Life is in Ticino
YEARS = range(1990, 2031)


def validity(table: str, legacy: pathlib.Path) -> dict[str, str]:
    """{abbreviation: column} of the version number and validity period of `table`."""
    return {abbreviation(column): column for column in load(table, legacy).columns if abbreviation(column) in VALIDITY}


def unique_reference(table: str, cols: tuple[str, ...], legacy: pathlib.Path) -> bool:
    """Whether the filled references `cols` of `table` are unique (a 0 is no reference)."""
    filled = load(table, legacy).select(cols).with_columns(pl.col(pl.Int64).replace(0, None)).drop_nulls()
    return filled.height > 0 and filled.is_unique().all()


def neighbours(table: str, legacy: pathlib.Path) -> list[tuple[str, tuple, tuple, str]]:
    """(other table, our columns, their columns, name of the step) of the relations from and to `table`."""
    found = []
    for name, cols, other, other_cols in relations(legacy).iter_rows():
        if name == table and other not in SKIPPED:
            found.append((other, tuple(cols), tuple(other_cols), f".{cols[-1]}"))
        if other == table and name not in SKIPPED and unique_reference(name, tuple(cols), legacy):
            found.append((name, tuple(other_cols), tuple(cols), f"^{cols[-1]}"))
    return found


def renamed(frame: pl.DataFrame, suffix: str) -> pl.DataFrame:
    """`frame` with `suffix` after every column name."""
    return frame.rename({column: f"{column}{suffix}" for column in frame.columns})


def plain_join(rows, ours, other, theirs, suffix, legacy):
    """`rows` with the row of `other` that `ours` points to (their columns are a key)."""
    table = renamed(load(other, legacy).unique(list(theirs)), suffix)
    return rows.join(table, left_on=list(ours), right_on=[f"{column}{suffix}" for column in theirs], how="left",
                     coalesce=False)


def snapshot_join(rows, ours, other, theirs, suffix, date, legacy):
    """`rows` with the version of `other` that is valid on the date column `date`, or its last version."""
    period = validity(other, legacy)
    order = period.get("VRSNR", period.get("VLDFR"))
    versions = renamed(load(other, legacy), suffix)
    right = [f"{column}{suffix}" for column in theirs]
    if date == LAST:
        last = versions.sort(f"{order}{suffix}").unique(right, keep="last")
        return rows.join(last, left_on=list(ours), right_on=right, how="left", coalesce=False)
    indexed = rows.with_row_index("ROW")
    candidates = indexed.select("ROW", date, *ours).join(versions, left_on=list(ours), right_on=right,
                                                         coalesce=False)
    valid = candidates.filter(pl.col(date).ge(pl.col(f"{period['VLDFR']}{suffix}")),
                              pl.col(date).le(pl.col(f"{period['VLDTO']}{suffix}")))
    chosen = valid.sort(f"{order}{suffix}").unique("ROW", keep="last").select("ROW", *versions.columns)
    return indexed.join(chosen, on="ROW", how="left").drop("ROW")


def expand(rows: pl.DataFrame, anchor: str, dates: list[str], legacy: pathlib.Path) -> pl.DataFrame:
    """`rows` of the `anchor` table with the rows of its neighbours, breadth first up to DEPTH steps.

    Every branch has a snapshot: the date column whose versions it follows, LAST, or None before the first
    versioned table. Every table enters once per snapshot, by its shortest way, and meets itself in one step only.
    """
    queue, met = [(anchor, "", None, 0)], {(anchor, None)}
    while queue:
        table, suffix, date, depth = queue.pop(0)
        for other, ours, theirs, step in neighbours(table, legacy) if depth < DEPTH else []:
            exact = set(theirs) in [set(key) for key in keys(other, legacy)] or step.startswith("^")
            versioned = not exact and keyed(other, theirs, legacy) and bool(validity(other, legacy))
            left = [f"{column}{suffix}" for column in ours]
            itself = other == table
            if not (exact or versioned) or any(column not in rows.columns for column in left) or (itself and suffix):
                continue
            for snapshot in [date] if date or exact else [*dates, LAST]:
                name = f"{step if itself else ''}{f'@{snapshot}' if snapshot else ''}"
                if (other, snapshot if not itself else name) in met:
                    continue
                met.add((other, snapshot if not itself else name))
                rows = (plain_join(rows, left, other, theirs, name, legacy) if exact else
                        snapshot_join(rows, left, other, theirs, name, snapshot, legacy))
                queue.append((other, name, snapshot, depth + 1))
    return rows


def date_columns(frame: pl.DataFrame) -> list[str]:
    """The date columns of `frame`."""
    return [column for column, dtype in frame.schema.items() if dtype == pl.Date]


def related(spec: TaskSpec, folder=None, legacy: pathlib.Path = LEGACY) -> pl.DataFrame:
    """The target rows with every column of the export that the relations reach from their anchor."""
    rows = spec.joined(**({"folder": folder} if folder else {}), legacy=legacy)
    if not spec.anchor:
        return rows
    anchor_dates = [column for column in date_columns(load(spec.anchor, legacy))]
    dates = [*anchor_dates, *[key for key in spec.keys if rows.schema[key] == pl.Date]]
    return expand(rows, spec.anchor, dates, legacy)


@functools.cache
def calendar() -> tuple[pl.DataFrame, list]:
    """(DAY, HOLIDAY) of the holidays of every canton, and the days of the local holidays."""
    days = {}
    for canton in holidays.country_holidays(COUNTRY).subdivisions:
        days.update(holidays.country_holidays(COUNTRY, subdiv=canton, years=YEARS))
    local = list(holidays.country_holidays(COUNTRY, subdiv=LOCAL, years=YEARS))
    return pl.DataFrame({"DAY": list(days), "HOLIDAY": list(days.values())}).sort("DAY"), local


def holiday_parts(column: str) -> list[pl.Expr]:
    """Whether a date is a local holiday, and the name of the holiday of any canton on that day."""
    named, local = calendar()
    names = pl.col(column).replace_strict(named["DAY"], named["HOLIDAY"], default=None)
    return [pl.col(column).is_in(local).alias(f"{column}:{LOCAL}_holiday"), names.alias(f"{column}:holiday")]


def derived(frame: pl.DataFrame, dates: list[str], legacy: pathlib.Path = LEGACY) -> pl.DataFrame:
    """`frame` with the derived features of the module docstring; `dates` are the dates to compare pairwise."""
    parts = [expr for column in date_columns(frame) for expr in (
        pl.col(column).dt.year().alias(f"{column}:year"), pl.col(column).dt.month().alias(f"{column}:month"),
        pl.col(column).dt.day().alias(f"{column}:day"), pl.col(column).dt.weekday().alias(f"{column}:weekday"),
        pl.col(column).dt.month_end().eq(pl.col(column)).alias(f"{column}:month_end"), *holiday_parts(column))]
    gaps = [pl.col(late).sub(pl.col(early)).dt.total_days().alias(f"{late}-{early}:days")
            for early, late in itertools.combinations(dates, 2)]
    cents = [pl.col(column).mod(100).alias(f"{column}:cents") for column in amount_columns(frame, legacy)]
    changes = [pl.col(first).ne_missing(pl.col(second)).alias(f"{first}!={second}")
               for first, second in snapshot_pairs(frame)]
    return frame.with_columns(*parts, *gaps, *cents, *changes)


def amount_columns(frame: pl.DataFrame, legacy: pathlib.Path) -> list[str]:
    """The columns of `frame` that hold amounts in cents (scale 2 in the dictionary)."""
    described = [columns(table, legacy) for table in load_tables(frame)]
    scales = dict(pl.concat(described).filter(pl.col("TYPE").eq("N")).select("COLUMN", "SCALE").iter_rows()) if (
        described) else {}
    return [column for column in frame.columns if scales.get(column.split("@")[0].split(".")[0].split("^")[0]) == 2]


def load_tables(frame: pl.DataFrame) -> set[str]:
    """The tables whose columns `frame` holds, from the two-letter aliases of the dictionary."""
    dictionary = pl.concat([columns(table) for table in relations()["TABLE"].unique()])
    aliases = {column.split("_")[0]: table for table, column in dictionary.select("TABLE", "COLUMN").iter_rows()}
    return {aliases[column.split("_")[0]] for column in frame.columns if column.split("_")[0] in aliases}


def snapshot_pairs(frame: pl.DataFrame) -> list[tuple[str, str]]:
    """Pairs of columns that are the same column of two snapshots (`PH_BRKNR@PR_DUEDT`, `PH_BRKNR@last`)."""
    by_base = itertools.groupby(sorted(column for column in frame.columns if "@" in column and ":" not in column),
                                key=lambda column: column.split("@")[0])
    return [pair for _, group in by_base for pair in itertools.combinations(list(group), 2)]


def pruned(frame: pl.DataFrame, kept: tuple[str, ...]) -> pl.DataFrame:
    """`frame` without constant columns and without copies of an earlier column; the `kept` columns stay."""
    fingerprints = frame.select(pl.col(column).hash(seed=0).sum() for column in frame.columns).row(0)
    counts = frame.select(pl.all().n_unique()).row(0)
    seen, chosen = set(), []
    for column, fingerprint, count in zip(frame.columns, fingerprints, counts, strict=True):
        if column in kept or (count > 1 and fingerprint not in seen):
            chosen.append(column)
        seen.add(fingerprint)
    return frame.select(chosen)


def entity_aggregates(spec: TaskSpec, rows: pl.DataFrame, legacy: pathlib.Path) -> pl.DataFrame:
    """`rows` with aggregates per entity (the first key) of every table that has many rows per entity."""
    key = spec.keys[0]
    for table, column in holders(rows[key], legacy):
        frame = load(table, legacy)
        if table in SKIPPED or frame[column].is_unique().all():
            continue
        dates = date_columns(frame)
        stats = frame.group_by(column).agg(
            pl.len().alias(f"{table}:rows"),
            *[pl.col(date).min().alias(f"{date}:first") for date in dates],
            *[pl.col(date).max().alias(f"{date}:last") for date in dates],
            *[pl.col(date).dt.day().n_unique().alias(f"{date}:days_of_month") for date in dates])
        rows = rows.join(stats.rename({column: key}), on=key, how="left")
    return rows


def features(spec: TaskSpec, folder=None, legacy: pathlib.Path = LEGACY) -> pl.DataFrame:
    """The related columns, the aggregates per entity and the derived features of every target row, pruned.

    The value columns of the target are kept as they are: features derived from them would give the answer away.
    """
    rows = entity_aggregates(spec, related(spec, folder, legacy), legacy)
    anchor_dates = date_columns(load(spec.anchor, legacy)) if spec.anchor else []
    target_dates = [column for column in spec.keys if rows.schema[column] == pl.Date]
    known = derived(rows.drop(spec.values), [*anchor_dates, *target_dates], legacy)
    return pruned(known.with_columns(rows.select(spec.values)), (*spec.keys, *spec.values))


def numeric(frame: pl.DataFrame) -> pl.DataFrame:
    """The features as numbers for a model: dates as days, booleans as 0/1, few texts one-hot, ids dropped."""
    kept = []
    for column, dtype in frame.schema.items():
        if dtype == pl.Date:
            kept.append(pl.col(column).cast(pl.Int32).cast(pl.Float64).alias(column))
        elif dtype == pl.Datetime("us") or isinstance(dtype, pl.Datetime):
            kept.append(pl.col(column).dt.epoch("s").truediv(86400).alias(column))
        elif dtype.is_numeric() or dtype == pl.Boolean:
            kept.append(pl.col(column).cast(pl.Float64))
        elif dtype == pl.String and frame[column].n_unique() <= (NAMES if column.endswith(":holiday") else FEW):
            kept.extend(pl.col(column).eq(value).cast(pl.Float64).fill_null(0).alias(f"{column}={value}")
                        for value in frame[column].drop_nulls().unique().sort())
    return frame.select(kept)
