"""Typed, cached copies of the legacy tables and the target files.

Every legacy column gets the type that NRDICT gives it: C -> trimmed text, N(0) -> Int64, N(s) -> exact
Decimal(38, s), D -> Date (0 = no date -> null, 9999999 = open end -> 9999-12-31), T -> Datetime. Empty fields are
null. Targets get the types of the official scoring (policy text, int, Decimal, Date). Parquet copies in
`lab/.cache` make every later load fast; they are rebuilt when the CSV is newer.
"""
import functools
import re
import sys
from decimal import Decimal

import polars as pl

from . import paths, schema

OPEN_END = 9999999
MAX_DATE = (9999, 12, 31)
sys.path.insert(0, str(paths.STARTER_KIT))
import scoring  # noqa: E402  (the organizers' module defines the target formats)


def tables():
    """Names of all legacy tables present in the extract."""
    return sorted(p.stem for p in paths.LEGACY.glob("NR*.csv"))


def _cached(name, folder, build):
    source = folder / f"{name}.csv"
    cache = paths.CACHE / folder.name / f"{name}.parquet"
    if cache.exists() and cache.stat().st_mtime >= source.stat().st_mtime:
        return pl.read_parquet(cache)
    df = build(source)
    cache.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(cache)
    return df


def _legacy_expr(col):
    text = pl.col(col.name).str.strip_chars().replace("", None)
    if col.type == "C":
        return text
    if col.type == "T":
        return text.str.to_datetime("%Y%m%d%H%M%S", strict=False)
    number = text.cast(pl.Int64)
    if col.type == "D":
        parts = [(1900 + number // 10000).cast(pl.String), (number // 100 % 100).cast(pl.String).str.zfill(2),
                 (number % 100).cast(pl.String).str.zfill(2)]
        iso = pl.concat_str(parts, separator="-").str.to_date("%Y-%m-%d", strict=False)  # impossible day -> null
        return (pl.when(number == 0).then(None)
                .when(number == OPEN_END).then(pl.date(*MAX_DATE))
                .otherwise(iso))
    if col.scale:
        unit = Decimal(1).scaleb(-col.scale)
        return number.cast(pl.Decimal(38, 0)) * pl.lit(unit, dtype=pl.Decimal(38, col.scale))
    return number


def load(table):
    """One legacy table, typed by NRDICT. Ragged rows (fewer fields than the header) get nulls.

    A date column with impossible days (e.g. 930931 = 31 September 1993) keeps them as null and gets an extra
    column `<name>_RAW` with the stored number, so that the rule search can find how Neuron read them.
    """
    def build(source):
        raw = pl.read_csv(source, separator=";", infer_schema=False, truncate_ragged_lines=True)
        specs = {c.name: c for c in schema.columns(table)}
        typed = raw.select(_legacy_expr(specs[name]).alias(name) if name in specs else pl.col(name)
                           for name in raw.columns)
        for name in raw.columns:
            if name in specs and specs[name].type == "D":
                number = raw[name].str.strip_chars().replace("", None).cast(pl.Int64)
                if (number.is_not_null() & typed[name].is_null() & (number != 0)).any():
                    typed = typed.with_columns(number.alias(f"{name}_RAW"))
        return typed
    return _cached(table, paths.LEGACY, build)


DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
INT = re.compile(r"^-?\d+$")
DEC = re.compile(r"^-?\d+\.\d+$")


def _infer(series):
    """Type of a target column from its text values: Date, Int64, Decimal with the largest scale, or text."""
    values = series.drop_nulls()
    if values.len() == 0:
        return series
    if values.str.contains(DATE.pattern).all():
        return series.str.to_date("%Y-%m-%d")
    if values.str.contains(INT.pattern).all():
        return series.cast(pl.Int64)
    if values.str.contains(r"^-?\d+(\.\d+)?$").all():
        scale = int(values.str.split(".").list.get(1, null_on_oob=True).str.len_chars().max() or 0)
        return series.cast(pl.Decimal(38, scale))
    return series


def target(name):
    """A target file (scored or diagnostic), typed: keys and values in the canonical types of `scoring.py`."""
    def build(source):
        raw = pl.read_csv(source, separator=",", infer_schema=False)
        return raw.select(_infer(raw[c].str.strip_chars()).alias(c) for c in raw.columns)
    return _cached(name, paths.TARGETS, build)


def target_names():
    return sorted(p.stem for p in paths.TARGETS.glob("t*.csv"))


@functools.cache
def target_columns(task):
    """(key columns, value columns) of a target file.

    Scored tasks: the arity in `scoring.TASKS`. Diagnostic files such as t2_projection_year or t3_booking: the
    shortest unique prefix of the header is the key, with policy_id in front when the prefix lacks it (the holdout
    split is by policy), and the decimal columns after it are the values.
    """
    df = target(task)
    header = df.columns
    if task in scoring.TASKS:
        n = len(scoring.TASKS[task].key)
        return header[:n], header[n:n + len(scoring.TASKS[task].value)]
    n = next(n for n in range(1, len(header) + 1) if df.select(header[:n]).unique().height == df.height)
    keys = header[:n] if "policy_id" in header[:n] or "policy_id" not in header else ["policy_id"] + header[:n]
    return keys, [c for c in header[n:] if isinstance(df[c].dtype, pl.Decimal) and c not in keys]


def ingest():
    """Typed Parquet copies of every legacy table and target file; returns {name: rows}."""
    counts = {t: load(t).height for t in tables()}
    counts.update({t: target(t).height for t in target_names()})
    return counts
