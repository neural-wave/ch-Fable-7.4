"""Evaluator check: the tasks run the way the evaluator runs them, timed, and their results kept.

Every task runs in a fresh Python process, as on the evaluator, so that no cache of another task helps it:
the time counts the imports, the reading of the export and the calculation. The peak memory of the process
is shown too. A task slower than the budget fails the check: t4 once ran out of the evaluator's time limit,
the guard against it happening again.

With --save the results are written to a folder; with --compare they are compared row by row with the results
saved there before: an optimization must not change a single value, on any policy of the export (train and
public), not only on the train rows that check.py scores. With --one-process all tasks run one after the other
in a single process, like starter_kit/check.py, to see what the shared caches save.

Usage (from the repository root, Python 3.14):
    python -B tools/evaluator_check.py --data /path/to/participants --save /tmp/before
    python -B tools/evaluator_check.py --data /path/to/participants --compare /tmp/before [--budget 20]
"""
import argparse
import csv
import datetime as dt
import importlib.util
import pathlib
import pickle
import resource
import subprocess
import sys
import tempfile
import time

TASKS = ("t0_commission", "t1_next_due_dates", "t2_projected_maturity_value", "t3_surrender_value",
         "t4_annual_statement")
EXTRACT_DATE = dt.date(2026, 6, 30)  # the extract date of t1, as in starter_kit/scoring.py
MEGABYTE = 1024 * 1024 if sys.platform == "darwin" else 1024  # ru_maxrss: bytes on macOS, kilobytes on Linux


def load_submission(folder):
    """The submission module, loaded the way check.py loads it."""
    sys.path.insert(0, str(folder))
    spec = importlib.util.spec_from_file_location("submission", pathlib.Path(folder) / "submission.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def arguments(task, data):
    """The arguments of a task besides the legacy folder, as scoring.arguments gives them."""
    if task == "t1_next_due_dates":
        return (EXTRACT_DATE,)
    if task == "t3_surrender_value":
        with open(data / "targets" / "t3_surrender_value.csv", encoding="utf-8") as targets:
            return (sorted({dt.date.fromisoformat(row[1]) for row in list(csv.reader(targets))[1:]}),)
    if task == "t5_outlier_detection":
        return (str(data / "targets"),)
    return ()


def run_tasks(tasks, data, submission_folder):
    """{task: (result, seconds)} of the tasks run one after the other in this process."""
    started = time.perf_counter()
    submission = load_submission(submission_folder)
    out, previous = {}, started
    for task in tasks:
        result = getattr(submission, task)(str(data / "legacy"), *arguments(task, data))
        now = time.perf_counter()
        out[task], previous = (result, now - previous), now
    return out


def child(args):
    """Run the tasks in this process and pickle their results, times and the peak memory."""
    results = run_tasks(args.child, args.data, args.submission)
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / MEGABYTE
    with open(args.out, "wb") as out:
        pickle.dump({"results": results, "peak": peak}, out)


def spawn(tasks, args, out):
    """Run `tasks` in a fresh process; (its results, its peak memory in MB, its wall time)."""
    started = time.perf_counter()
    command = [sys.executable, "-B", __file__, "--data", str(args.data), "--submission", str(args.submission),
               "--out", str(out), "--child", *tasks]
    subprocess.run(command, check=True)
    with open(out, "rb") as run:
        report = pickle.load(run)
    return report["results"], report["peak"], time.perf_counter() - started


def as_dict(result):
    """A task result as {key: value}; the set of t5 as {key: True}."""
    return dict.fromkeys(result, True) if isinstance(result, set) else result


def differences(reference, result):
    """(keys only in the reference, keys only in the result, keys with another value)."""
    old, new = as_dict(reference), as_dict(result)
    changed = sum(1 for key in old.keys() & new.keys() if old[key] != new[key])
    return len(old.keys() - new.keys()), len(new.keys() - old.keys()), changed


def compare(task, result, folder):
    """A short text on how `result` differs from the one saved in `folder`, and whether it is identical."""
    path = folder / f"{task}.pickle"
    if not path.exists():
        return "no reference", True
    with open(path, "rb") as saved:
        missing, extra, changed = differences(pickle.load(saved), result)
    if missing or extra or changed:
        return f"DIFFERENT: {missing} missing, {extra} extra, {changed} changed", False
    return "identical", True


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data", type=pathlib.Path, required=True, help="the participants folder")
    parser.add_argument("--submission", type=pathlib.Path, default=pathlib.Path("my_solution"))
    parser.add_argument("--tasks", nargs="*", default=list(TASKS))
    parser.add_argument("--budget", type=float, default=20.0, help="seconds per task")
    parser.add_argument("--save", type=pathlib.Path, help="folder to write the results to")
    parser.add_argument("--compare", type=pathlib.Path, help="folder of results saved before")
    parser.add_argument("--one-process", action="store_true", help="all tasks in one process, like check.py")
    parser.add_argument("--child", nargs="*", help=argparse.SUPPRESS)
    parser.add_argument("--out", type=pathlib.Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    args.data, args.submission = args.data.resolve(), args.submission.resolve()
    if args.child:
        return child(args)
    scratch = pathlib.Path(tempfile.mkdtemp()) / "run.pickle"
    if args.save:
        args.save.mkdir(parents=True, exist_ok=True)
    groups = [args.tasks] if args.one_process else [[task] for task in args.tasks]
    ok, total = True, 0.0
    print(f"{'task':30s} {'call s':>7s} {'process s':>9s} {'peak MB':>8s} {'rows':>8s}  budget  results")
    for group in groups:
        results, peak, wall = spawn(group, args, scratch)
        for task, (result, seconds) in results.items():
            within = seconds <= args.budget
            text, same = compare(task, result, args.compare) if args.compare else ("not compared", True)
            ok, total = ok and within and same, total + seconds
            print(f"{task:30s} {seconds:7.1f} {wall:9.1f} {peak:8.0f} {len(result):8d}  {'ok  ' if within else 'OVER'}    {text}")
            if args.save:
                with open(args.save / f"{task}.pickle", "wb") as out:
                    pickle.dump(result, out)
    scratch.unlink(missing_ok=True)
    scratch.parent.rmdir()
    print(f"\ntotal of the calls: {total:.1f}s (budget {args.budget:.0f}s per task); {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
