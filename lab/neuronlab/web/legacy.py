"""Step 1 of a new task: the legacy data as the lab reads it (tables, keys, column types, relationships).

Keys and relationships come from the cached legacy profile (`lab/.cache/profile_legacy.json`); without it the
page says that profiling has to run first. Column types come from NRDICT, the data dictionary every Neuron extract
carries; an extract without one can bring a schema file (JSON or SQL DDL), which becomes its NRDICT.csv. COBOL
copybooks are not read.
"""
import csv
import io
import json
import os
import re
import shutil

from .. import paths, profile, schema, store
from . import layout

ROLE_DATE, ROLE_AMOUNT, ROLE_KEY, ROLE_REF, ROLE_CATEGORY, ROLE_TEXT = (
    "Date", "Amount", "Key", "Reference", "Category", "Text")


def cached_profile():
    path = paths.CACHE / "profile_legacy.json"
    return json.loads(path.read_text()) if path.exists() else None


def titles():
    from .. import freeze
    try:
        return freeze.titles()
    except OSError:
        return {}


def key_of(table, prof):
    return schema.key_of(table, (prof or {}).get("uccs", {}).get(table))


def header(table):
    with open(paths.LEGACY / f"{table}.csv", encoding="utf-8") as f:
        return f.readline().strip().split(";")


def rows_of(table):
    cache = paths.CACHE / "legacy" / f"{table}.parquet"
    source = paths.LEGACY / f"{table}.csv"
    if cache.exists() and cache.stat().st_mtime >= source.stat().st_mtime:
        import polars as pl
        return pl.scan_parquet(cache).select(pl.len()).collect().item()
    with open(source, "rb") as f:
        return sum(1 for _ in f) - 1


def overview():
    """Tables of the legacy folder: what each holds, rows, key found, columns without a type."""
    if not paths.LEGACY.exists():
        return {"folder": str(paths.LEGACY), "missing": True, "tables": [], "joins": []}
    prof = cached_profile()
    typed = schema.dictionary() if (paths.LEGACY / "NRDICT.csv").exists() else {}
    names = titles()
    tables = []
    for t in store.tables():
        if t in ("NRDICT", "NRCODE"):
            continue
        declared = {c.name for c in typed.get(t, [])}
        untyped = [c for c in header(t) if c not in declared]
        key = key_of(t, prof)
        tables.append({"name": t, "desc": names.get(t, ""), "rows": rows_of(t),
                       "key": ", ".join(key) if key else None, "untyped": untyped})
    joins = profile.joins(prof) if prof else []
    return {"folder": str(paths.LEGACY), "env": bool(os.environ.get("NEURON_LEGACY")),
            "dictionary": bool(typed), "profiled": prof is not None, "tables": tables,
            "joins": [dict(j, id=f"{j['from']}->{j['to']}") for j in joins],
            "files": sorted(p.name for p in paths.LEGACY.glob("*.csv"))}


def declared_type(c):
    if c.type == "C":
        return f"CHAR({c.length})"
    if c.type == "N":
        return f"N({c.scale})"
    return {"D": "DATE CYYMMDD", "T": "TIMESTAMP"}.get(c.type, c.type)


def table(name):
    """Columns of one table: declared type, the type the lab reads, meaning, role, an example value."""
    if name not in store.tables():
        raise ValueError(f"unknown table {name}")
    import polars as pl
    df = store.load(name)
    specs = {c.name: c for c in schema.columns(name)} if name in schema.dictionary() else {}
    prof = cached_profile() or {}
    key = set(key_of(name, prof) or [])
    refs = {j["from"].split(".", 1)[1] for j in (profile.joins(prof) if prof else []) if j["from"].startswith(name + ".")}
    columns = []
    for col in df.columns:
        spec = specs.get(col)
        values = df[col].drop_nulls()
        example = str(values[0]) if values.len() else ""
        if spec is None:
            role = "Unknown"
        elif col in key:
            role = ROLE_KEY
        elif col in refs:
            role = ROLE_REF
        elif spec.type in ("D", "T"):
            role = ROLE_DATE
        elif spec.is_amount:
            role = ROLE_AMOUNT
        elif spec.type == "C" and spec.length >= profile.FREE_TEXT:
            role = ROLE_TEXT
        else:
            role = ROLE_CATEGORY
        dtype = df[col].dtype
        read_as = f"Decimal(38, {dtype.scale})" if isinstance(dtype, pl.Decimal) else str(dtype).lower()
        columns.append({"name": col, "declared": declared_type(spec) if spec else "—",
                        "type": read_as if spec else "to confirm", "meaning": spec.desc if spec else "",
                        "role": role, "example": example[:40], "typed": spec is not None})
    return {"name": name, "rows": df.height, "columns": columns, "key": sorted(key)}


def diagram(tables, joins, highlight=None, extra=None):
    """Join graph of some tables, with the task's output as an extra box when given."""
    drawn = layout.graph(tables, joins)
    for n in drawn["nodes"]:
        n["highlight"] = n["id"] == highlight
    if extra:
        width = drawn["width"]
        drawn["nodes"].append({"id": extra["id"], "x": width, "y": layout.MARGIN, "w": 208, "h": 112, "output": True,
                               "lines": extra.get("lines", [])})
        drawn["width"] = width + 208 + layout.MARGIN
    return drawn


def switch(folder):
    """Make another folder the legacy data of the lab: the typed copies and the legacy profile are rebuilt."""
    import pathlib
    path = pathlib.Path(folder).expanduser()
    if not path.is_absolute():
        path = (paths.REPO / "lab" / path).resolve()
    if not path.is_dir() or not list(path.glob("NR*.csv")):
        raise ValueError(f"{path} has no NR*.csv files")
    if not (path / "NRDICT.csv").exists():
        raise ValueError(f"{path} has no NRDICT.csv: add a schema file to give the columns their types")
    if path.resolve() != paths.LEGACY.resolve():
        shutil.rmtree(paths.CACHE / "legacy", ignore_errors=True)
        (paths.CACHE / "profile_legacy.json").unlink(missing_ok=True)
    paths.LEGACY = path
    os.environ["NEURON_LEGACY"] = str(path)
    schema.dictionary.cache_clear()
    return overview()


def upload_folder():
    import datetime as dt
    folder = paths.CACHE / "uploads" / dt.datetime.now().strftime("%Y%m%dT%H%M%S")
    folder.mkdir(parents=True, exist_ok=True)
    return folder


SAFE_NAME = re.compile(r"^[A-Za-z0-9_.-]{1,80}$")


def receive(files):
    """Uploaded files {name: bytes} into a new folder: CSV tables as they are, a schema file as NRDICT.csv."""
    for name in files:
        base = os.path.basename(name)
        suffix = base.rsplit(".", 1)[-1].lower()
        if not SAFE_NAME.match(base):
            raise ValueError(f"file name not allowed: {name}")
        if suffix == "cpy":
            raise ValueError("COBOL copybooks are not read: export the dictionary as JSON or SQL DDL")
        if suffix not in ("csv", "json", "sql", "ddl"):
            raise ValueError(f"unexpected file {base}")
    folder = upload_folder()
    notes = []
    for name, data in files.items():
        base = os.path.basename(name)
        suffix = base.rsplit(".", 1)[-1].lower()
        if suffix == "csv":
            (folder / base).write_bytes(data)
        else:  # a schema file: JSON or SQL DDL
            rows = dictionary_from_schema(data.decode("utf-8"), suffix)
            write_dictionary(folder / "NRDICT.csv", rows)
            notes.append(f"{base}: {len(rows)} columns into NRDICT.csv")
    return folder, notes


DDL_TABLE = re.compile(r"create\s+table\s+[\"`\[]?(\w+)[\"`\]]?\s*\((.*?)\)\s*;", re.I | re.S)
DDL_COLUMN = re.compile(r"^\s*[\"`\[]?(\w+)[\"`\]]?\s+(\w+)\s*(?:\(\s*(\d+)\s*(?:,\s*(\d+))?\s*\))?", re.I)


def dictionary_from_schema(text, kind):
    """NRDICT rows (table, column, type, length, scale, description) from a JSON schema or SQL DDL.

    JSON: {"tables": {"NRPOLH": [{"name", "type": C|N|D|T, "length", "scale", "description"}, ...]}}.
    DDL: CHAR/VARCHAR -> C, DECIMAL/NUMERIC(p, s) -> N with scale s, INT -> N(0), DATE -> D (Neuron CYYMMDD),
    TIMESTAMP -> T.
    """
    rows = []
    if kind == "json":
        data = json.loads(text)
        for table, cols in (data.get("tables") or {}).items():
            for c in cols:
                rows.append((table, c["name"], c["type"], int(c.get("length") or 0), int(c.get("scale") or 0),
                             c.get("description", "")))
        return rows
    for table, body in DDL_TABLE.findall(text):
        for line in re.split(r",\s*(?![^()]*\))", body):
            m = DDL_COLUMN.match(line)
            if not m or m.group(1).lower() in ("primary", "foreign", "constraint", "unique", "key"):
                continue
            name, sql, n, s = m.group(1), m.group(2).lower(), int(m.group(3) or 0), int(m.group(4) or 0)
            if sql in ("char", "varchar", "nchar", "nvarchar", "text"):
                rows.append((table, name, "C", n, 0, ""))
            elif sql in ("decimal", "numeric", "number"):
                rows.append((table, name, "N", n, s, ""))
            elif sql in ("int", "integer", "smallint", "bigint"):
                rows.append((table, name, "N", n or 9, 0, ""))
            elif sql == "date":
                rows.append((table, name, "D", 7, 0, ""))
            elif sql in ("timestamp", "datetime"):
                rows.append((table, name, "T", 14, 0, ""))
    if not rows:
        raise ValueError("no column found in the schema file")
    return rows


def write_dictionary(path, rows):
    out = io.StringIO()
    writer = csv.writer(out, delimiter=";", lineterminator="\n")
    writer.writerow(["DC_TABLE", "DC_COLUMN", "DC_TYPE", "DC_LEN", "DC_SCALE", "DC_DESC"])
    writer.writerows(rows)
    path.write_text(out.getvalue(), encoding="utf-8")
