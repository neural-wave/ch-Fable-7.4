"""Task definitions `lab/tasks/<id>.json` (schema "neuron-task/1"): what the pages of `lab serve` let a person declare.

A definition is optional: without it every step infers what it needs, as before. With it:
- the key and value columns of the target file are the declared ones (store.target_columns), and the target file
  can live anywhere (`examples.target_file.path`);
- the joins of the profile lose the rejected relationships and gain the ones added by hand (profile.profile);
- the frame only joins the tables in scope, casts the columns whose type was confirmed by hand, and gets the values
  of other tasks as inputs (frame.build);
- a declared rounding mode replaces the rounding variants of the pool;
- description and notes go to the language model of step 5 (suggest.context), features become `lab feature`;
- hand pairs are checked by `lab score` (acceptance) or added to the target rows (discovery).
Every field is checked by `check()`, whose list is the one the review page shows.
"""
import copy
import functools
import json
import re

from . import paths

SCHEMA = "neuron-task/1"
ID = re.compile(r"^[a-z][a-z0-9_]{1,62}$")
ROUNDINGS = ("discover", "ROUND_HALF_UP", "ROUND_HALF_EVEN", "ROUND_HALF_DOWN", "ROUND_DOWN", "ROUND_UP",
             "ROUND_FLOOR", "ROUND_CEILING")
TYPES = ("string", "int", "date", "decimal")  # confirmed types of untyped legacy columns, decimal as "decimal:2"
PAIRS_USE = ("acceptance", "discovery")
MILLION = 1_000_000


class Invalid(ValueError):
    pass


def folder():
    path = paths.REPO / "lab" / "tasks"
    path.mkdir(parents=True, exist_ok=True)
    return path


def path_of(task):
    return folder() / f"{task}.json"


def empty(task_id=""):
    """The skeleton the wizard starts from."""
    return {"schema": SCHEMA, "id": task_id, "title": "",
            "legacy": {"source": "folder", "path": str(paths.LEGACY), "tables": [], "joins": []},
            "task": {"description": "", "grain": "", "keys": [], "values": [],
                     "scope": {"tables": [], "noise": "NREXCP", "tasks": []}, "hints": []},
            "examples": {"target_file": {"path": f"{task_id}.csv" if task_id else "", "inputs": []},
                         "pairs": [], "pairs_use": "acceptance"},
            "run": {"steps": ["profile", "frame", "cluster", "tree", "pool", "iterate", "report"], "model": "",
                    "max_features": 3, "suggest": False}}


@functools.lru_cache(maxsize=32)
def _read(path, mtime):
    return json.loads(open(path, encoding="utf-8").read())


def find(task):
    """The definition of a task (a base task: `t0~llm` reads the one of t0), None if there is none."""
    if not task:
        return None
    path = folder() / f"{task.split('~')[0]}.json"
    if not path.exists():
        return None
    return copy.deepcopy(_read(str(path), path.stat().st_mtime_ns))


def all_definitions():
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(folder().glob("*.json"))]


def structure(definition):
    """Problems that make a definition unusable (the review page blocks saving on them)."""
    problems = []
    if definition.get("schema") != SCHEMA:
        problems.append(f"schema must be {SCHEMA}")
    if not ID.match(definition.get("id") or ""):
        problems.append("the task id must be lower case letters, digits and _, starting with a letter")
    task = definition.get("task", {})
    names = [k.get("name") for k in task.get("keys", [])] + [v.get("name") for v in task.get("values", [])]
    if not task.get("keys"):
        problems.append("at least one key column")
    if not task.get("values"):
        problems.append("at least one value column")
    if len(set(names)) != len(names) or not all(names):
        problems.append("every output column needs a distinct name")
    for v in task.get("values", []):
        if v.get("rounding", "discover") not in ROUNDINGS:
            problems.append(f"unknown rounding {v.get('rounding')} of {v.get('name')}")
    if definition.get("examples", {}).get("pairs_use", "acceptance") not in PAIRS_USE:
        problems.append("pairs_use is acceptance or discovery")
    for table in definition.get("legacy", {}).get("tables", []):
        for column, spec in (table.get("columns") or {}).items():
            if spec.get("type") and spec["type"].split(":")[0] not in TYPES:
                problems.append(f"unknown type {spec['type']} of {table['name']}.{column}")
    return problems


def save(definition):
    problems = structure(definition)
    if problems:
        raise Invalid("; ".join(problems))
    path = path_of(definition["id"])
    path.write_text(json.dumps(definition, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


# --- what the steps read ---------------------------------------------------------------------------------------

def target_path(task):
    """The target file of a defined task (absolute, or relative to NEURON_TARGETS), None without a definition."""
    definition = find(task)
    path = ((definition or {}).get("examples", {}).get("target_file") or {}).get("path")
    if not path:
        return None
    import pathlib
    p = pathlib.Path(path)
    return p if p.is_absolute() else paths.TARGETS / p


def columns(task):
    """(keys, values) declared for a task, None without a definition."""
    definition = find(task)
    if not definition or not definition["task"].get("keys") or not definition["task"].get("values"):
        return None
    return [k["name"] for k in definition["task"]["keys"]], [v["name"] for v in definition["task"]["values"]]


def rounding(task, value):
    """The declared rounding mode of a value, None when it is to be discovered."""
    definition = find(task)
    for v in (definition or {}).get("task", {}).get("values", []):
        if v.get("name") == value and v.get("rounding", "discover") != "discover":
            return v["rounding"]
    return None


def scope_tables(task):
    tables = ((find(task) or {}).get("task", {}).get("scope") or {}).get("tables") or []
    return set(tables) or None


def scope_tasks(task):
    return ((find(task) or {}).get("task", {}).get("scope") or {}).get("tasks") or []


def join_overrides(task):
    """(rejected {(from, to)}, added [join]) of the relationships confirmed in the definition."""
    joins = (find(task) or {}).get("legacy", {}).get("joins", [])
    rejected = {(j["from"], j["to"]) for j in joins if j.get("keep") is False}
    added = [{"from": j["from"], "to": j["to"], "kind": j.get("kind", "plain"), "evidence": "added by hand"}
             for j in joins if j.get("keep") is not False and j.get("origin") == "hand"]
    return rejected, added


def column_types(task):
    """{column: type} confirmed by hand for legacy columns without a type in NRDICT."""
    found = {}
    for table in (find(task) or {}).get("legacy", {}).get("tables", []):
        for column, spec in (table.get("columns") or {}).items():
            if spec.get("type"):
                found[column] = spec["type"]
    return found


def pairs(task, use=None):
    """Hand pairs of a task, optionally only when they are meant for `use` (acceptance or discovery)."""
    examples = (find(task) or {}).get("examples", {})
    if use and examples.get("pairs_use", "acceptance") != use:
        return []
    return examples.get("pairs", [])


def features(task):
    return [{"name": h["feature"], "expr": h["expr"]} for h in (find(task) or {}).get("task", {}).get("hints", [])
            if h.get("feature") and h.get("expr")]


# --- checks of the review page ---------------------------------------------------------------------------------

def check(definition):
    """[{level: ok|warning|info|error, title, detail}] of a definition, from cheap reads only."""
    from . import dsl, schema, store
    checks = [{"level": "error", "title": p, "detail": "Fix it before saving."} for p in structure(definition)]
    task = definition.get("task", {})
    task_id = definition.get("id") or "?"
    target = target_file(definition)
    header = []
    if target and target.exists():
        header = target.read_text(encoding="utf-8").splitlines()[0].split(",")
        rows = sum(1 for _ in open(target, encoding="utf-8")) - 1
        names = [k["name"] for k in task.get("keys", [])] + [v["name"] for v in task.get("values", [])]
        missing = [n for n in names if n not in header]
        checks.append({"level": "error" if missing else "ok", "title": "Output columns are in the target file",
                       "detail": f"missing: {', '.join(missing)}" if missing else f"{target.name}: {rows} rows"})
        if rows > MILLION:
            checks.append({"level": "info", "title": "Large target files are sampled",
                           "detail": "Above one million rows, a fixed fifth of the policies is used."})
    else:
        checks.append({"level": "warning", "title": "No target file",
                       "detail": "Without examples the task is unscored: only step 5 can run."})
    tables = (task.get("scope") or {}).get("tables") or []
    legacy = set(store.tables()) if paths.LEGACY.exists() else set()
    unknown = [t for t in tables if t not in legacy]
    if unknown:
        checks.append({"level": "error", "title": "Tables in scope exist", "detail": f"unknown: {', '.join(unknown)}"})
    typed = schema.dictionary() if (paths.LEGACY / "NRDICT.csv").exists() else {}
    confirmed = column_types_of(definition)
    untyped = []
    for t in tables:
        if t in legacy and t in typed:
            declared = {c.name for c in typed[t]}
            header_cols = (paths.LEGACY / f"{t}.csv").open(encoding="utf-8").readline().strip().split(";")
            untyped += [f"{t}.{c}" for c in header_cols if c not in declared and c not in confirmed]
    checks.append({"level": "warning" if untyped else "ok",
                   "title": f"{', '.join(untyped[:4])} {'have' if len(untyped) > 1 else 'has'} no type" if untyped
                   else "Every column in scope has a type",
                   "detail": "Read as text until you confirm a type. Not blocking." if untyped else "From NRDICT."})
    prof = paths.RUNS / task_id / "profile.json"
    if prof.exists():
        grain = (json.loads(prof.read_text()).get("grain") or {}).get("best") or {}
        mapping = ", ".join(f"{k} → {grain.get('table')}.{v}" for k, v in (grain.get("columns") or {}).items())
        checks.append({"level": "ok" if grain else "warning", "title": "Output keys reach the legacy data",
                       "detail": mapping or "No legacy table contains the target keys."})
    else:
        checks.append({"level": "info", "title": "Output keys reach the legacy data",
                       "detail": "Found by profiling in step 1."})
    checks.append({"level": "ok" if task.get("description") else "warning", "title": "Description is written",
                   "detail": "Passed to the language model in step 5 only."})
    text = [v["name"] for v in task.get("values", []) if str(v.get("type", "")).lower() in ("string", "text", "str")]
    if text:
        checks.append({"level": "warning", "title": f"Text value{'s' if len(text) > 1 else ''}: {', '.join(text)}",
                       "detail": "The relations of steps 2 to 4 compute numbers and dates: the pipeline skips "
                                 "a text value and finds the rules of the others. Write its function by hand."})
    frame_meta = paths.RUNS / task_id / "frame.json"
    columns_known = list(json.loads(frame_meta.read_text())["lineage"]) if frame_meta.exists() else None
    for hint in task.get("hints", []):
        if hint.get("feature"):
            try:
                dsl.parse(hint["expr"], columns_known or [], columns_known or [])
                checks.append({"level": "ok", "title": f"Feature {hint['feature']} parses in the DSL",
                               "detail": hint["expr"]})
            except dsl.Invalid as e:
                unknown_column = str(e).startswith("unknown column") or "not versioned" in str(e)
                level = "info" if unknown_column and columns_known is None else "error"
                checks.append({"level": level, "title": f"Feature {hint['feature']} parses in the DSL",
                               "detail": f"{e}" + (" (checked again on the frame of step 1)" if level == "info" else "")})
    hand = definition.get("examples", {}).get("pairs", [])
    if hand:
        listed = sum(bool(p.get("noise")) for p in hand)
        checks.append({"level": "ok", "title": f"{len(hand)} hand pair{'s' if len(hand) > 1 else ''}",
                       "detail": f"{listed} marked as typed by hand, kept out of discovery." if listed else
                       f"Used for {definition['examples'].get('pairs_use', 'acceptance')}."})
    from .store import scoring
    if task_id not in scoring.TASKS:
        checks.append({"level": "info", "title": "Lab-only task",
                       "detail": "The official scoring and check.py know t0–t4: this task is scored by the lab "
                                 "(discovery, holdout, pairs), and freeze writes only functions the submission has."})
    return checks


def target_file(definition):
    import pathlib
    path = ((definition.get("examples") or {}).get("target_file") or {}).get("path")
    if not path:
        return None
    p = pathlib.Path(path)
    return p if p.is_absolute() else paths.TARGETS / p


def column_types_of(definition):
    return {c for t in definition.get("legacy", {}).get("tables", []) for c, s in (t.get("columns") or {}).items()
            if s.get("type")}


# --- a definition from the artifacts of a task -----------------------------------------------------------------

def init(task):
    """The definition that describes what the pipeline inferred for an existing task (profile, frame, target)."""
    from . import schema, store
    definition = empty(task)
    folder_ = paths.RUNS / task
    prof = json.loads((folder_ / "profile.json").read_text()) if (folder_ / "profile.json").exists() else {}
    meta = json.loads((folder_ / "frame.json").read_text()) if (folder_ / "frame.json").exists() else {}
    keys, values = store.target_columns(task)
    target = store.target(task)
    tables = sorted({info["table"] for info in meta.get("lineage", {}).values()
                     if info.get("table") and info["table"].startswith("NR")})
    grain = ((prof.get("grain") or {}).get("best") or {})
    definition["title"] = task.replace("_", " ").capitalize()
    definition["task"].update(
        grain=f"one row per {' × '.join(keys)}",
        keys=[{"name": k, "type": dtype_name(target[k].dtype), "meaning": ""} for k in keys],
        values=[{"name": v, "type": dtype_name(target[v].dtype), "rounding": "discover", "meaning": ""}
                for v in values])
    definition["task"]["scope"]["tables"] = tables
    uccs = prof.get("keys", {})
    definition["legacy"]["tables"] = [{"name": t, "key": schema.key_of(t, uccs.get(t)) or [], "columns": {}}
                                      for t in tables]
    definition["legacy"]["joins"] = [{"from": j["from"], "to": j["to"], "kind": j["kind"], "keep": True,
                                      "origin": "profile"} for j in prof.get("joins", [])
                                     if j["from"].split(".")[0] in tables and j["to"].split(".")[0] in tables]
    if grain and grain.get("table") not in tables:
        definition["task"]["scope"]["tables"].insert(0, grain["table"])
    return definition


def dtype_name(dtype):
    import polars as pl
    if isinstance(dtype, pl.Decimal):
        return f"Decimal(38, {dtype.scale})"
    return {pl.Date: "date", pl.Int64: "int", pl.String: "string"}.get(dtype, str(dtype))


def command(rest):
    """`lab task init|show|check <task>`, `lab task add <file.json>`."""
    if len(rest) < 2 or rest[0] not in ("init", "show", "check", "add"):
        print("usage: lab task init|show|check <task> | lab task add <file.json>")
        return 2
    verb, name = rest[0], rest[1]
    if verb == "init":
        definition = init(name)
        print(save(definition))
        return 0
    if verb == "add":
        definition = json.loads(open(name, encoding="utf-8").read())
    else:
        definition = find(name)
        if definition is None:
            print(f"no definition {path_of(name)}: `lab task init {name}` writes one from the artifacts")
            return 1
    if verb == "show":
        print(json.dumps(definition, indent=1, ensure_ascii=False))
        return 0
    results = check(definition)
    for c in results:
        print(f"{c['level']:8s} {c['title']}: {c['detail']}")
    if verb == "add":
        if any(c["level"] == "error" for c in results):
            print("not saved: fix the errors first")
            return 1
        print(save(definition))
    return 1 if any(c["level"] == "error" for c in results) else 0
