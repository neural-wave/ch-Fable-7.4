"""Data quality findings that the rules have to live with (no LLM, no target files)."""
import csv
import re

import polars as pl

from . import paths, schema, store


def ragged_rows(table):
    """Rows with fewer or more fields than the header."""
    with open(paths.LEGACY / f"{table}.csv", newline="", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=";")
        width = len(next(reader))
        return sum(1 for row in reader if len(row) != width)


def documented_domain(column):
    """Values listed in the NRDICT description, e.g. 'smoker (Y/N)' -> {'Y', 'N'}."""
    m = re.search(r"\(([^)]*)\)", column.desc)
    if not m:
        return None
    parts = [p.strip().split("=")[0].strip() for p in re.split(r"[/,]", m.group(1))]
    return set(parts) if parts and all(0 < len(p) <= column.length for p in parts) else None


def findings():
    out = []
    for table in store.tables():
        n = ragged_rows(table)
        if n:
            out.append(f"{table}: {n} rows with a different number of fields than the header")
    codes = store.load("NRCODE")
    domains = {d: set(g["CD_CODE"].to_list()) for (d,), g in codes.group_by("CD_DOMAIN")}
    for table in store.tables():
        if table in ("NRCODE", "NRDICT"):
            continue
        df = store.load(table)
        for col in schema.columns(table):
            if col.name not in df.columns or col.type != "C" or col.length > 8:
                continue
            values = df[col.name].drop_nulls()
            known = domains.get(col.abbreviation)
            if known:
                unknown = values.filter(~values.is_in(list(known)))
                if unknown.len():
                    out.append(f"{table}.{col.name}: {unknown.len()} values not in NRCODE domain {col.abbreviation}:"
                               f" {sorted(set(unknown.to_list()))[:6]}")
            doc = documented_domain(col)
            if doc:
                other = values.filter(~values.is_in(list(doc)))
                if other.len():
                    out.append(f"{table}.{col.name}: documented {sorted(doc)}, found {sorted(set(other.to_list()))[:6]}"
                               f" in {other.len()} rows")
            lower = values.filter(values.str.contains("[a-z]"))
            if 0 < lower.len() < 0.05 * values.len():
                out.append(f"{table}.{col.name}: {lower.len()} lowercase values among uppercase codes, e.g. "
                           f"{sorted(set(lower.to_list()))[:4]}")
        raw = [c for c in df.columns if c.endswith("_RAW")]
        for c in raw:
            bad = df.filter(df[c.removesuffix("_RAW")].is_null() & df[c].is_not_null())
            out.append(f"{table}.{c.removesuffix('_RAW')}: {bad.height} impossible dates, e.g. {bad[c].head(4).to_list()}")
    prices = store.load("NRFPRC")
    restated = prices.group_by("FP_FNDID", "FP_PRCDT").len().filter(pl.col("len") > 1)
    out.append(f"NRFPRC: {restated.height} prices published more than once (the latest publication counts)")
    heads = store.load("NRPOLH")
    open_old = heads.filter((pl.col("PH_VRSST") == "S") & (pl.col("PH_VLDTO") == pl.date(9999, 12, 31)))
    out.append(f"NRPOLH: {open_old.height} superseded versions with an open end (the highest version wins)")
    events = store.load("NREVNT").filter(pl.col("EV_USRID").str.contains("BATCH"))
    users = events.group_by("EV_USRID").agg(pl.col("EV_EFFDT").min().alias("first"), pl.col("EV_EFFDT").max().alias("last"),
                                            pl.len().alias("rows")).sort("first")
    for r in users.iter_rows(named=True):
        out.append(f"NREVNT: batch user {r['EV_USRID']} from {r['first']} to {r['last']} ({r['rows']} events)")
    return out


def report():
    return "\n".join(f"- {f}" for f in findings())
