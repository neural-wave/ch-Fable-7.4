"""Freeze: the winning candidate becomes a function of submission.py, generated from deterministic templates.

The frame lineage says how every feature was reached (grain row -> plain or temporal joins -> column, maybe a
character position), so the code walks the same path with the stdlib helpers of `neuron.py`. Names come from the
table titles of SCHEMA.md and the column descriptions of NRDICT. After writing, `check.py` must give the same
score as the ledger: that is the regression test of the freeze.
"""
import json
import re
import subprocess
import sys

from . import frame as frames, paths, profile, schema
from .store import scoring

HEADING = re.compile(r"^### (NR\w{4}): ([^(\n]+)")
HEADER = '''"""Neuron migration challenge: the formulas found by the lab pipeline (clustering + optimal trees + exact score).

Each function gets the folder `legacy_dir` with the NR*.csv files and returns the calculated values.
Dates are `datetime.date`, amounts are `decimal.Decimal`. Every value is calculated from `legacy_dir`.
"""
'''


def titles():
    """{table: title} from the headings of SCHEMA.md, e.g. NRCOMR -> 'commission rates'."""
    found = {}
    for line in (paths.REPO / "SCHEMA.md").read_text(encoding="utf-8").splitlines():
        m = HEADING.match(line)
        if m:
            found[m.group(1)] = m.group(2).split(",")[0].strip()
    return found


def snake(text):
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def names(table):
    """(collection name, row name) for a table, e.g. NRBROK -> ('brokers', 'broker')."""
    title = titles().get(table, table.lower())
    if title.endswith("s"):
        return snake(title), snake(title[:-1])
    return snake(title + "s"), snake(title)


class Code:
    """Collects the setup lines (tables as dicts) and the per-row bindings of one task function."""

    def __init__(self, meta):
        self.meta, self.lineage = meta, meta["lineage"]
        self.setup, self.bindings, self.rows = [], [], {}
        self.grain_row = names(meta["grain"])[1]

    def collection(self, table, key, temporal):
        plural = names(table)[0]
        helper = "grouped" if temporal else "keyed"
        line = f'{plural} = {helper}(table(legacy_dir, "{table}"), "{key}")'
        if line not in self.setup:
            self.setup.append(line)
        return plural

    def row(self, step, source_expr, anchor_expr):
        """Variable of the row reached by one join step."""
        table, key = profile.split(step["to"])
        temporal = step["kind"] == "temporal"
        plural = self.collection(table, key, temporal)
        singular = names(table)[1]
        ident = (table, source_expr, anchor_expr if temporal else None)
        if ident in self.rows:
            return self.rows[ident]
        var = singular if singular not in self.rows.values() else f"{singular}_{len(self.rows)}"
        if not temporal:
            expr = f"{plural}[{source_expr}]"
        elif anchor_expr:
            expr = f'valid({plural}[{source_expr}], "{schema.alias(table)}", {anchor_expr})'
        else:
            expr = f'latest({plural}[{source_expr}], "{schema.alias(table)}")'
        self.bindings.append(f"{var} = {expr}")
        self.rows[ident] = var
        return var

    def column(self, name):
        """Expression of a frame column, adding the joins it needs."""
        info = self.lineage[name]
        holder = self.grain_row
        for step in info.get("path", []):
            source = step["from"]
            source_expr = self.column(source) if source in self.lineage and self.lineage[source].get("path") \
                else f'{self.grain_row}["{source}"]'
            anchor = step.get("anchor")
            holder = self.row(step, source_expr, f'{self.grain_row}["{anchor}"]' if anchor else None)
        expr = f'{holder}["{info["column"]}"]'
        if "position" in info:
            expr += f"[{info['position'] - 1}]"
        return expr


def constant_expr(code, candidate):
    """Expression of the constant of the candidate for the current row (lookup or rule constants)."""
    lookup = candidate.get("lookup")
    if lookup:
        table, keys = lookup["table"], lookup["keys"]
        unique = any(set(u) == set(keys) for u in profile.legacy_profile()["uccs"].get(table, []))
        plural = names(table)[0]
        key_list = ", ".join(f'"{k}"' for k in keys)
        helper = "keyed" if unique else "grouped"
        code.setup.append(f'{plural} = {helper}(table(legacy_dir, "{table}"), {key_list})')
        args = ", ".join(code.column(f) for f in keys.values())
        found = f"{plural}[{args}]"
        if not unique:
            anchor = lookup.get("anchor")
            found = (f'valid({found}, "{schema.alias(table)}", {code.grain_row}["{anchor}"])' if anchor
                     else f'latest({found}, "{schema.alias(table)}")')
        return f'{found}["{lookup["column"]}"]'
    branches = []
    for rule in candidate["rules"]:
        cond = " and ".join(f'{code.column(c)} {"==" if op == "=" else "!="} "{v}"' for c, op, v in rule["when"])
        branches.append((cond or "True", rule["then"]))
    return branches


def render(task, candidate):
    """Source of the task function for a candidate."""
    df, meta = frames.load(task)
    code = Code(meta)
    value = candidate["value"]
    relation = candidate["relation"]
    grain_row, grain = code.grain_row, meta["grain"]
    rows_name = names(grain)[0]
    constant = constant_expr(code, candidate)
    x = code.column(relation["input"]) if relation.get("input") else None
    lines = []
    if isinstance(constant, list):
        lines.append("rate = None")
        for i, (cond, then) in enumerate(constant):
            lines.append(f"{'if' if i == 0 else 'elif'} {cond}:")
            lines.append(f'    rate = Decimal("{then}")')
        constant = "rate"
    else:
        lines.append(f"{snake(schema.column(candidate['lookup']['table'], candidate['lookup']['column']).desc)}"
                     f" = {constant}")
        constant = lines[-1].split(" = ")[0]
    scale = df[value].dtype.scale if hasattr(df[value].dtype, "scale") else 0
    rounding = candidate.get("rounding", "ROUND_HALF_UP")
    if relation["kind"] == "ratio":
        computed = (f"cents({x} * {constant})" if scale == 2 and rounding == "ROUND_HALF_UP"
                    else f'({x} * {constant}).quantize(Decimal("1e-{scale}"), {rounding})')
    elif relation["kind"] == "diff":
        computed = f"{x} + {constant}"
    elif relation["kind"] == "days":
        computed = f"{x} + dt.timedelta(days=int({constant}))"
    elif relation["kind"] == "months":
        computed = f"add_months({x}, int({constant}))"
    else:
        computed = constant
    key = ", ".join(f'{grain_row}["{meta["mapping"][k]}"]' for k in meta["keys"])
    flt = meta.get("filter")
    body = code.bindings + lines + [f"result[{key}] = {computed}"]
    loop = [f'for {grain_row} in table(legacy_dir, "{grain}"):']
    if flt and flt.get("errors", 1) == 0 and " is null" not in flt["column"]:
        keep = flt["keep"]
        test = f'== "{keep[0]}"' if len(keep) == 1 else f"in {tuple(keep)}"
        loop.append(f'    if {grain_row}["{flt["column"]}"] {test}:')
        body = ["        " + b for b in body]
    else:
        body = ["    " + b for b in body]
    rule = _describe(candidate)
    score = candidate["score"]
    doc = [f'    """{value} = {rule}.', "",
           f"    Lab candidate {candidate['id']}: {score['total'][0]} / {score['total'][1]} train rows exact"
           f" (holdout {score['holdout'][0]} / {score['holdout'][1]}).", '    """']
    src = [f"def {task}(legacy_dir):", *doc, *("    " + s for s in code.setup), "    result = {}",
           *("    " + s for s in loop), *("    " + b for b in body), "    return result"]
    return "\n".join(src) + "\n", rows_name


def _describe(candidate):
    relation = candidate["relation"]
    if candidate.get("lookup"):
        lk = candidate["lookup"]
        keys = ", ".join(f"{k} = {v}" for k, v in lk["keys"].items())
        const = f"{lk['table']}.{lk['column']}[{keys}]"
    else:
        const = f"constants of {len(candidate['rules'])} rules"
    op = {"ratio": "x", "diff": "+", "days": "+ days", "months": "+ months", "const": ""}[relation["kind"]]
    rounding = f", {candidate.get('rounding', 'ROUND_HALF_UP')}" if relation["kind"] == "ratio" else ""
    return f"{relation.get('input') or ''} {op} {const}{rounding}".strip()


HELPERS = ("add_months", "cents", "grouped", "keyed", "latest", "read_targets", "table", "valid")


def replace_function(source, name, new):
    """Replace the top-level function `name` in a module source (up to the next top-level def or constant)."""
    pattern = re.compile(rf"^def {name}\(.*?(?=^def |^[A-Z_]+ = |\Z)", re.S | re.M)
    if not pattern.search(source):
        source = source.rstrip("\n") + "\n\n\n" + new
    else:
        source = pattern.sub(lambda _: new + "\n\n", source, count=1)
    used = [h for h in HELPERS if re.search(rf"\b{h}\(", source)]
    return re.sub(r"^from neuron import .*$", f"from neuron import {', '.join(used)}", source, count=1, flags=re.M)


def check_score(task):
    """(exact rows, output) of check.py for one task, run with the Python of the lab."""
    result = subprocess.run([sys.executable, "check.py", "--tasks", task, "--legacy", str(paths.LEGACY),
                             "--targets", str(paths.TARGETS)], cwd=paths.STARTER_KIT, capture_output=True, text=True)
    output = result.stdout + result.stderr
    found = re.search(rf"^{task}\s+(\d+) /", output, re.M)
    return (int(found.group(1)) if found else -1), output


def refusal(run, candidate_id=None):
    """Why `freeze` has no code template for this run and candidate, or None: the checks of freeze, nothing written."""
    task = run.split("~")[0]
    if run.endswith("~ablate"):
        return "no code template for an ablation run: it tests step 5 with columns removed, it is not a rule"
    if task not in scoring.TASKS:
        return (f"{task} has no function in submission.py: the official scoring and check.py know "
                f"{', '.join(scoring.TASKS)}")
    meta = json.loads((paths.run_dir(run) / "frame.json").read_text())
    if len(meta["values"]) > 1:
        return (f"no code template for a task with {len(meta['values'])} value columns: write the function "
                f"in submission.py and score it with `lab score {task}`")
    pool = json.loads((paths.run_dir(run) / "pool.json").read_text())
    info = next(iter(pool["values"].values()))
    wanted = candidate_id or info["best"]
    candidate = next(c for c in info["candidates"] if c["id"] == wanted)
    used = candidate["features"] + [candidate["relation"].get("input")]
    missing = [f for f in used if f and "path" not in meta["lineage"].get(f, {})]
    if missing:  # previous(...) or a calendar feature: no join path that a template can follow
        return (f"no code template for the features {missing}: write the function in submission.py and "
                f"score it with `lab score {task}`")
    return None


def freeze(run, candidate_id=None, write=True, check=True):
    """Render the winner (or `candidate_id`) of a run, write it into submission.py and verify it with check.py.

    `run` is a task or a variant run `<task>~llm` with features added in step 5; the function keeps the task name.
    The file is restored when the new function scores fewer rows than the one it replaces: an agent can try a
    freeze without risk.
    """
    task = run.split("~")[0]
    reason = refusal(run, candidate_id)
    if reason:
        raise ValueError(reason)
    pool = json.loads((paths.run_dir(run) / "pool.json").read_text())
    info = next(iter(pool["values"].values()))
    wanted = candidate_id or info["best"]
    candidate = next(c for c in info["candidates"] if c["id"] == wanted)
    source, _ = render(run, candidate)
    source = source.replace(f"def {run}(", f"def {task}(", 1)
    if not write:
        return source, None
    target = paths.SUBMISSION / "submission.py"
    text = target.read_text(encoding="utf-8").replace("\r\n", "\n")
    before = check_score(task)[0] if check else -1
    target.write_text(replace_function(text, task, source), encoding="utf-8")
    if not check:
        return source, None
    after, output = check_score(task)
    if before < 0 or after < 0:  # check.py failed: nothing says the new function is not worse
        target.write_text(text, encoding="utf-8")
        raise ValueError(f"check.py did not score {task}, submission.py is unchanged:\n{output[-2000:]}")
    if after < before:
        target.write_text(text, encoding="utf-8")
        raise ValueError(f"the new function scores {after} rows, the current one {before}: submission.py is unchanged")
    return source, output
