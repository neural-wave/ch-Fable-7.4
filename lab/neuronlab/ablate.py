"""`lab ablate`: switch one rule off, score again, and keep where the rows it made right went wrong.

A rule card in `lab/rules/<task>.json` names one rule of the submission and the text replacements that switch it
off. They are made in a scratch copy of the submission folder in the lab cache, so the submission itself (and its
maintainability index) never changes. The copy is scored with `lab score --submission` into the run
`<task>~off-<card>`, and the unchanged submission into `<task>~on`, so both sides come from the same code.

Every card switches off one rule and keeps all the others, so the rows it breaks are the contribution of that rule
(leave one out). `runs/<task>/ablation.json` keeps per card the counts, the rows it breaks per value column, some
examples and what the optimal trees of `lab score` say about the wrong rows. `runs/<task>/ablation.parquet` has one
row per target row: the keys, whether the row is exact with every rule (`on`) and without the rule of a card
(`off:<card>`), the difference of the first value it breaks (`diff:<card>`) and the card's `where` feature, an
expression of the DSL of step 5 on the frame (`where:<card>`), which `lab viz` puts on the x axis.
"""
import json
import shutil

import polars as pl

from . import dsl, frame as frames, paths, score

EXAMPLES = 25


def cards(task):
    """The rule cards of a task, [] when it has none."""
    path = paths.RULES / f"{task}.json"
    return json.loads(path.read_text(encoding="utf-8"))["cards"] if path.exists() else []


def scratch(task, name, edits):
    """A copy of the submission folder with the `edits` made; each text to replace must be found exactly once."""
    folder = paths.CACHE / "ablate" / task / name
    shutil.rmtree(folder, ignore_errors=True)
    shutil.copytree(paths.SUBMISSION, folder, ignore=shutil.ignore_patterns("__pycache__", "tools"))
    for edit in edits:
        path = folder / edit["file"]
        source = path.read_text(encoding="utf-8")
        found = source.count(edit["old"])
        if found != 1:
            raise ValueError(f"card {name}: the text to replace is found {found} times in {edit['file']}: {edit['old']}")
        path.write_text(source.replace(edit["old"], edit["new"]), encoding="utf-8")
    return folder


def value_columns(diffs):
    return [c.split(":", 1)[1] for c in diffs.columns if c.startswith("diff:")]


def exact(diffs, value):
    """True where the computed value equals the target: a difference of exactly 0 (a missing value is wrong)."""
    return (pl.col(f"diff:{value}") == 0).fill_null(False)


def scored(task, run, folder):
    """diffs.parquet of `folder` scored into `run`, with the exact flag per value and per row, and the trees text."""
    text = score.score(task, folder=folder, run=run)
    diffs = pl.read_parquet(paths.run_dir(run) / "diffs.parquet")
    values = value_columns(diffs)
    diffs = diffs.with_columns(exact(diffs, v).alias(f"exact:{v}") for v in values)
    return diffs.with_columns(pl.all_horizontal([f"exact:{v}" for v in values]).alias("exact")), text


def trees(text):
    """{value: the lines of score.md that say where the function is wrong}."""
    found, value = {}, None
    for line in text.splitlines():
        if line.startswith("## "):
            value = line[3:]
        elif value and (line.startswith("Where it is wrong") or line.startswith("  ")):
            found.setdefault(value, []).append(line.strip())
    return found


def where(task, card, keys):
    """The card's `where` feature on the frame of the task, with its keys; None without a `where`."""
    if not card.get("where"):
        return None
    df, _ = frames.load(task)
    node = dsl.parse(card["where"], df.columns, df.columns)
    return df.select(keys).with_columns(dsl.evaluate(node, df, df).alias(f"where:{card['id']}"))


def first_broken(on, off, values):
    """The difference of the first value column that the rule makes right and the card gets wrong, per row."""
    frame = pl.DataFrame({**{f"broken{i}": on[f"exact:{v}"] & ~off[f"exact:{v}"] for i, v in enumerate(values)},
                          **{f"diff{i}": off[f"diff:{v}"] for i, v in enumerate(values)}})
    first = pl.coalesce([pl.when(pl.col(f"broken{i}")).then(pl.col(f"diff{i}")) for i in range(len(values))])
    return frame.select(first.alias("diff"))["diff"]


def summary(card, run, on, off, keys, text):
    """The ablation.json entry of one card."""
    values = value_columns(on)
    broken = on["exact"] & ~off["exact"]
    rows = off.filter(broken).head(EXAMPLES)
    examples = [{**{k: str(r[k]) for k in keys},
                 **{v: {"target": r[f"target:{v}"], "off": r[f"computed:{v}"]} for v in values if not r[f"exact:{v}"]}}
                for r in rows.iter_rows(named=True)]
    return {
        "id": card["id"], "rule": card["rule"], "off": card["off"], "where": card.get("where"),
        "where_label": card.get("where_label", card.get("where")), "edits": card["edits"],
        "run": run, "wrong_on": int((~on["exact"]).sum()), "wrong_off": int((~off["exact"]).sum()),
        "broken": int(broken.sum()), "fixed": int((~on["exact"] & off["exact"]).sum()),
        "broken_by_value": {v: int((on[f"exact:{v}"] & ~off[f"exact:{v}"]).sum()) for v in values},
        "examples": examples, "trees": trees(text),
    }


def ablate(task, ids=()):
    """Score the submission with every rule on and with each chosen card off; write ablation.json and .parquet."""
    chosen = [c for c in cards(task) if not ids or c["id"] in ids]
    if not chosen:
        raise ValueError(f"no rule cards for {task}{' with the ids ' + ', '.join(ids) if ids else ''} in {paths.RULES}")
    on, _ = scored(task, f"{task}~on", paths.SUBMISSION)
    keys = [c for c in on.columns if ":" not in c and c != "exact"]
    values = value_columns(on)
    folder = paths.run_dir(task)
    old_json = folder / "ablation.json"
    entries = {c["id"]: c for c in json.loads(old_json.read_text())["cards"]} if old_json.exists() else {}
    table = on.select(keys + [pl.col("exact").alias("on")])
    old_table = folder / "ablation.parquet"
    if old_table.exists():  # the columns of the cards that are not scored again
        kept = [c for c in pl.read_parquet(old_table).columns if ":" in c and c.split(":", 1)[1] in entries
                and c.split(":", 1)[1] not in {card["id"] for card in chosen}]
        table = table.join(pl.read_parquet(old_table).select(keys + kept), on=keys, how="left")
    for card in chosen:
        run = f"{task}~off-{card['id']}"
        off, text = scored(task, run, scratch(task, card["id"], card["edits"]))
        if not off.select(keys).equals(on.select(keys)):
            raise ValueError(f"{run}: the rows are not in the order of the target file")
        entries[card["id"]] = summary(card, run, on, off, keys, text)
        table = table.with_columns(off["exact"].alias(f"off:{card['id']}"),
                                   first_broken(on, off, values).alias(f"diff:{card['id']}"))
        feature = where(task, card, keys)
        if feature is not None:
            table = table.drop(f"where:{card['id']}", strict=False).join(feature, on=keys, how="left")
        print(f"{task} {card['id']:28s} wrong {entries[card['id']]['wrong_on']:>6} with the rule, "
              f"{entries[card['id']]['wrong_off']:>6} without it: {entries[card['id']]['broken']} broken, "
              f"{entries[card['id']]['fixed']} fixed")
    order = [c["id"] for c in cards(task) if c["id"] in entries]
    result = {"task": task, "keys": keys, "values": values, "rows": on.height, "wrong": int((~on["exact"]).sum()),
              "cards": [entries[i] for i in order]}
    old_json.write_text(json.dumps(result, indent=1, default=str), encoding="utf-8")
    table.write_parquet(old_table)
    return result
