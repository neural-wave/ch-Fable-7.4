"""Score a submission locally against the train targets for t7 task.

    python check_t7.py
    python check_t7.py --submission path/to/your/solution

Usage: t7_tax_payout and t7_tax_annual have no targets to read, but the scoring
module can validate format and structure.
"""
import argparse
import pathlib
import sys

import scoring
from scoring import read_targets, normalize, accuracy


def load_submission(folder):
    sys.path.insert(0, str(folder))
    import importlib.util
    spec = importlib.util.spec_from_file_location("submission", pathlib.Path(folder) / "submission.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def score_task(submission, legacy_dir, targets_dir, task):
    task_func = getattr(submission, task, None)
    if task_func is None:
        print(f"{task:30s}  SKIP (no function)")
        return

    # Load targets if available
    targets_path = pathlib.Path(targets_dir) / f"{task}.csv"
    targets = None
    if targets_path.exists():
        targets = read_targets(targets_dir, task)

    # Run the function
    predictions = task_func(str(legacy_dir))
    normalized = scoring.normalize(task, predictions)

    # Score against targets if available
    if targets is not None and len(targets) > 0:
        correct, total = scoring.accuracy(task, predictions, targets)
        print(f"{task:30s} {correct:8d} / {total:8d} = {correct / total:8.4%}")
    else:
        print(f"{task:30s} {len(normalized):8d} results  (no targets)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", default=pathlib.Path(__file__).resolve().parent / "my_solution")
    parser.add_argument("--legacy", default=pathlib.Path(__file__).resolve().parent.parent / "legacy")
    parser.add_argument("--targets", default=pathlib.Path(__file__).resolve().parent.parent / "targets")
    parser.add_argument("--tasks", nargs="*", default=["t7_tax_payout", "t7_tax_annual"])
    args = parser.parse_args()

    submission = load_submission(args.submission)
    for task in args.tasks:
        score_task(submission, args.legacy, args.targets, task)


if __name__ == "__main__":
    main()
