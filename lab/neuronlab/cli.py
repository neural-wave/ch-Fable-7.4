"""`lab`: the rule-discovery pipeline from the command line, one command per step.

    lab ingest                       typed Parquet copies of the legacy tables and targets
    lab audit                        data quality findings
    lab run <task>                   steps 1-4, 6, 7 and report.md in one go
    lab profile|frame|cluster|tree|pool|iterate|report <task>   one step
    lab pool show <task>             cards and candidates with their scores
    lab pool eval <task> <file.json> score a candidate written by hand or by the LLM
    lab freeze <task> [candidate]    generate the function in submission.py and check it
    lab score <task> [name=expr ...] exact score of the function in submission.py and where it is wrong
    lab ablate <task> [card ...]     switch each rule of lab/rules/<task>.json off in a scratch copy, score again
    lab suggest <task> [--ablate C]  step 5 in batch: JSON proposals of the open-weights model, validated, scored
    lab feature <task> <name> <expr> step 5 by hand: one feature in the DSL (e.g. "at(BR_TIER, PR_RCVDT)")
    lab llm ping                     check the endpoint and model of step 5
    lab t7check                      t7 without targets: the examples of such.pdf, consistency with NRTAXB
    lab show <table> [COL=VALUE ...] typed rows of a legacy table or target file, e.g. NRPOLH PH_POLNR=BL10000001
    lab viz [task ...]               runs/atlas.html: before / after, policy timelines and the story, offline
    lab viz policy <id> [id ...]     runs/policies/<id>.json: one policy month by month against the files
    lab viz story                    runs/story.json: the journey of 100 francs, on a policy picked by the rules
"""
import argparse
import json
import sys
import time

from . import paths


def _step(name, task):
    from . import cluster, frame, iterate, pool, profile, report, tree
    started = time.time()
    fn = {"profile": profile.profile, "frame": frame.build, "cluster": cluster.run, "tree": tree.run,
          "pool": pool.run, "iterate": iterate.run, "report": report.build}[name]
    fn(task)
    print(f"{name:8s} {task}  {time.time() - started:5.1f}s")


def run(task):
    for name in ("profile", "frame", "cluster", "tree", "pool", "iterate", "report"):
        _step(name, task)
    print((paths.run_dir(task) / "report.md").read_text())


def pool_show(task):
    data = json.loads((paths.run_dir(task) / "pool.json").read_text())
    for value, info in data["values"].items():
        print(f"## {value}  winner {info['best']}  ties {info['ties'][:5]}")
        for c in info["candidates"][:25]:
            s = c["score"]
            print(f"  {c['id']:44s} total {s['total'][0]:>8}/{s['total'][1]}  holdout {s['holdout'][0]:>7}/"
                  f"{s['holdout'][1]}  {c['rounding'].replace('ROUND_', ''):9s} {', '.join(c['features'])}")


def pool_eval(task, path):
    from . import evaluate, frame
    df, meta = frame.load(task)
    candidate = json.loads(open(path, encoding="utf-8").read())
    value = candidate.setdefault("value", meta["values"][0])
    result = evaluate.score(df, meta, candidate, value)
    print(json.dumps(evaluate.record(task, value, candidate, result), indent=1))


def show(name, filters, limit=40):
    """Rows of one table or target file that match every COL=VALUE filter (compared as text), at most `limit`."""
    import polars as pl
    from . import store
    df = store.target(name) if name in store.target_names() else store.load(name)
    for item in filters:
        column, value = item.split("=", 1)
        df = df.filter(pl.col(column).cast(pl.String) == value)
    with pl.Config(tbl_rows=limit, tbl_cols=-1, fmt_str_lengths=40, tbl_width_chars=250):
        print(df.head(limit))
    print(f"{df.height} rows")


def main(argv=None):
    paths.load_env()
    parser = argparse.ArgumentParser(prog="lab", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command")
    parser.add_argument("args", nargs="*")
    parser.add_argument("--ablate", default=None, help="suggest: drop frame columns matching this glob first")
    parser.add_argument("--dry-run", action="store_true", help="suggest: print the prompt, do not call the model")
    parser.add_argument("--submission", default=None, help="score: another submission folder (not recorded)")
    args = parser.parse_args(argv)
    cmd, rest = args.command, args.args
    if cmd == "ingest":
        from . import store
        for name, rows in store.ingest().items():
            print(f"{name:32s} {rows:>10,}")
    elif cmd == "audit":
        from . import audit
        print(audit.report())
    elif cmd == "run":
        run(rest[0])
    elif cmd in ("profile", "frame", "cluster", "tree", "iterate", "report"):
        _step(cmd, rest[0])
    elif cmd == "pool" and rest and rest[0] == "show":
        pool_show(rest[1])
    elif cmd == "pool" and rest and rest[0] == "eval":
        pool_eval(rest[1], rest[2])
    elif cmd == "pool":
        _step("pool", rest[0])
    elif cmd == "freeze":
        from . import freeze
        try:
            source, check = freeze.freeze(rest[0], rest[1] if len(rest) > 1 else None)
        except ValueError as e:
            print(f"refused: {e}")
            return 1
        print(source)
        print(check)
    elif cmd == "suggest":
        from . import suggest
        print(suggest.suggest(rest[0], ablate=args.ablate, dry_run=args.dry_run))
    elif cmd == "feature":
        from . import dsl, suggest
        try:
            print(suggest.add_feature(rest[0], rest[1], rest[2]))
        except dsl.Invalid as e:
            print(f"rejected: {e}")
            return 1
    elif cmd == "score":
        from . import score
        print(score.score(rest[0], dict(item.split("=", 1) for item in rest[1:]), args.submission))
    elif cmd == "ablate":
        from . import ablate
        ablate.ablate(rest[0], rest[1:])
    elif cmd == "show":
        show(rest[0], rest[1:])
    elif cmd == "t7check":
        from . import t7check
        print(t7check.check(args.submission))
    elif cmd == "viz" and rest[:1] == ["policy"]:
        from . import trace, viz
        for path in trace.build(rest[1:], args.submission or paths.SUBMISSION):
            print(path)
        print(viz.atlas())
    elif cmd == "viz" and rest[:1] == ["story"]:
        from . import story, viz
        print(story.build())
        print(viz.atlas())
    elif cmd == "viz":
        from . import viz
        print(viz.atlas(rest or None))
    elif cmd == "llm" and rest[:1] == ["ping"]:
        from . import llm
        print(llm.complete('Answer with the single word "pong".'))
    else:
        parser.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
