"""Findings: what one round of the discovery loop found, written for people and for the LLM.

A report (`reports/<target>/<round>.md` and `.json`) holds the residual summary, the most common differences of
the wrong rows, the conditions of the decision tree and the change points. Every finding has an id such as
`t0_commission/r1/T1`; the code written from a finding cites it, so every rule can be traced to its evidence.
"""
import json
import pathlib

import polars as pl

from detective.residuals import DIFF, summary
from detective.spec import TaskSpec

REPORTS = pathlib.Path(__file__).resolve().parent / "reports"
COMMON = 8  # the most common differences shown per value


def differences(table: pl.DataFrame, spec: TaskSpec) -> dict[str, list[dict]]:
    """{value: the most common differences rule minus target of the wrong rows, with their rows}."""
    wrong = table.filter(pl.col("STATUS").eq("wrong"))
    return {value: wrong.group_by(f"{value}{DIFF}").len().sort("len", descending=True).head(COMMON).rename(
        {f"{value}{DIFF}": "DIFF", "len": "ROWS"}).to_dicts() for value in spec.values}


def findings(spec: TaskSpec, round_name: str, rules: list[dict], changes: list[dict]) -> list[dict]:
    """The conditions and change points as findings with ids."""
    prefix = f"{spec.target}/{round_name}"
    tree_findings = [{"ID": f"{prefix}/T{number}", "METHOD": "decision tree", **rule}
                     for number, rule in enumerate(rules, 1)]
    change_findings = [{"ID": f"{prefix}/C{number}", "METHOD": "change point", **change}
                       for number, change in enumerate(changes, 1)]
    return [*tree_findings, *change_findings]


def markdown(spec: TaskSpec, round_name: str, counts: dict, diffs: dict, found: list[dict], notes: str) -> str:
    """The report as markdown."""
    lines = [f"# {spec.target}, {round_name}", "", notes, "", "## Rows", "",
             ", ".join(f"{status}: {rows}" for status, rows in counts.items()), "", "## Most common differences", ""]
    for value, rows in diffs.items():
        lines.append(f"- {value}: " + ", ".join(f"{row['DIFF']} ({row['ROWS']})" for row in rows))
    lines += ["", "## Conditions (decision tree on the wrong rows)", ""]
    lines += [f"- **{item['ID']}** {' and '.join(item['CONDITIONS'])}: {item['WRONG']} of {item['ROWS']} wrong "
              f"({item['SHARE']:.1%})" for item in found if item["METHOD"] == "decision tree"]
    lines += ["", "## Change points", ""]
    lines += [f"- **{item['ID']}** {item['COLUMN']} between {item['BEFORE']} and {item['AFTER']}: wrong "
              f"{item['RATE_BEFORE']:.1%} before, {item['RATE_AFTER']:.1%} after (explains {item['EXPLAINED']:.1%})"
              for item in found if item["METHOD"] == "change point"]
    return "\n".join(lines) + "\n"


def write(spec: TaskSpec, round_name: str, table: pl.DataFrame, rules: list[dict], changes: list[dict],
          notes: str = "") -> pathlib.Path:
    """Write the report of a round and return the path of its markdown."""
    folder = REPORTS / spec.target
    folder.mkdir(parents=True, exist_ok=True)
    counts, diffs = summary(table), differences(table, spec)
    found = findings(spec, round_name, rules, changes)
    (folder / f"{round_name}.json").write_text(json.dumps(
        {"rows": counts, "differences": diffs, "findings": found}, indent=1, default=str))
    path = folder / f"{round_name}.md"
    path.write_text(markdown(spec, round_name, counts, diffs, found, notes))
    return path


def write_search(spec: TaskSpec, round_name: str, results: list[dict], notes: str = "") -> pathlib.Path:
    """Write the results of a search (`formulas.fill_holes`) as findings S1, S2, ... and return the path."""
    folder = REPORTS / spec.target
    folder.mkdir(parents=True, exist_ok=True)
    prefix = f"{spec.target}/{round_name}"
    found = [{"ID": f"{prefix}/S{number}", "METHOD": "search", **result} for number, result in enumerate(results, 1)]
    (folder / f"{round_name}.json").write_text(json.dumps({"findings": found}, indent=1, default=str))
    lines = [f"# {spec.target}, {round_name}", "", notes, "", "| Finding | Holes | Right (80 %) | Right (held out) |",
             "| --- | --- | --- | --- |"]
    lines += [f"| {item['ID']} | {item['HOLES']} | {item['RIGHT']} / {item['TOTAL']} | "
              f"{item['RIGHT_HELD_OUT']} / {item['TOTAL_HELD_OUT']} |" for item in found]
    path = folder / f"{round_name}.md"
    path.write_text("\n".join(lines) + "\n")
    return path
