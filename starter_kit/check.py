"""Score a submission locally against the train targets.

    python check.py
    python check.py --submission path/to/your/solution --tasks t0_commission t2_projected_maturity_value

The train targets contain the manually corrected values too (finding them is task t5), so a perfect rule set
scores slightly below 100% here. t5 gets the train targets as `targets_dir`, like it gets the targets of the
evaluated policies later. There is no list of the train corrections, so only the number of outliers it reports is
shown.

t7 (the tax module) has no train targets: a t7 task is scored only if its target file is in `--targets`, otherwise
the rows that pass the format check of scoring are counted.
"""
import argparse
import collections
import importlib.util
import pathlib
import sys
import time

import scoring

DEFAULT = pathlib.Path(__file__).resolve().parent


def load_submission(folder):
    sys.path.insert(0, str(folder))  # so that submission.py can import its helper modules
    spec = importlib.util.spec_from_file_location("submission", pathlib.Path(folder) / "submission.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_outliers(submission, legacy, targets):
    started = time.time()
    outliers = scoring.normalize_outliers(submission.t5_outlier_detection(str(legacy), str(targets)))
    per_task = collections.Counter(task for task, _ in outliers)
    print(f"{scoring.OUTLIER_TASK:30s} {len(outliers):8d} outliers   {time.time() - started:6.1f}s   {dict(per_task)}")


def check_t7(submission, legacy, targets, task):
    if not hasattr(submission, task):
        print(f"{task:30s} SKIP (no function)")
        return
    started = time.time()
    predictions = getattr(submission, task)(str(legacy))
    if (pathlib.Path(targets) / f"{task}.csv").exists():
        correct, total = scoring.accuracy(task, predictions, scoring.read_targets(targets, task))
        print(f"{task:30s} {correct:8d} / {total:8d} = {correct / total:8.4%}   {time.time() - started:6.1f}s")
        return
    rows, total = len(scoring.normalize(task, predictions)), len(predictions or {})
    print(f"{task:30s} {rows:8d} / {total:8d} well formed   {time.time() - started:6.1f}s   (no targets)")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--submission", default=DEFAULT / "my_solution")
    parser.add_argument("--legacy", default=DEFAULT.parent / "legacy")
    parser.add_argument("--targets", default=DEFAULT.parent / "targets")
    tasks = list(scoring.TASKS) + [scoring.OUTLIER_TASK] + list(scoring.T7_TASKS)
    parser.add_argument("--tasks", nargs="*", default=tasks)
    args = parser.parse_args()
    submission = load_submission(args.submission)
    for task in args.tasks:
        if task == scoring.OUTLIER_TASK:
            check_outliers(submission, args.legacy, args.targets)
            continue
        if task in scoring.T7_TASKS:
            check_t7(submission, args.legacy, args.targets, task)
            continue
        targets = scoring.read_targets(args.targets, task)
        started = time.time()
        predictions = getattr(submission, task)(str(args.legacy), *scoring.arguments(task, targets))
        correct, total = scoring.accuracy(task, predictions, targets)
        print(f"{task:30s} {correct:8d} / {total:8d} = {correct / total:8.4%}   {time.time() - started:6.1f}s")
    print()
    scoring.print_maintainability(scoring.maintainability(args.submission))


if __name__ == "__main__":
    main()
