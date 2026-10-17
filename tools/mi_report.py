"""Maintainability harness: the radon maintainability index, file by file and term by term.

It computes the same index as starter_kit/scoring.py (radon mi_visit with multi=True, average of the files
weighted by source lines of code) and shows the four terms of the formula, to see which lever to pull:

    MI = (171 - 5.2 ln V - 0.23 G - 16.2 ln LLOC + 50 sin(sqrt(2.46 * C in radians))) * 100 / 171

    V     Halstead volume: grows with arithmetic and logical operators and operands (calls do not count)
    G     total cyclomatic complexity of the file: every if, for, while, and, or, except, comprehension
    LLOC  logical lines: the heaviest term, hence small and cohesive files
    C     comment lines (#) + lines of multi-line docstrings, in % of the code lines.
          One-line docstrings do not count. Best around 55 %, good between 35 % and 80 %,
          above 120 % the index goes down again.

Usage:  python -B tools/mi_report.py my_solution
"""
import math
import pathlib
import sys

from radon.complexity import cc_visit
from radon.metrics import mi_parameters, mi_visit
from radon.raw import analyze


def comment_term(percent):
    """The contribution (not normalised, at most 50) of the comment-to-code ratio."""
    return 50 * math.sin(math.sqrt(2.46 * math.radians(percent)))


def report(folder):
    rows, total_sloc, weighted = [], 0, 0.0
    for path in sorted(pathlib.Path(folder).rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        mi, sloc = mi_visit(source, multi=True), max(1, analyze(source).sloc)
        volume, complexity, lloc, comments = mi_parameters(source, count_multi=True)
        worst = max(cc_visit(source), key=lambda block: block.complexity, default=None)
        rows.append((path.relative_to(folder).as_posix(), mi, sloc, lloc, volume, complexity, comments,
                     f"{worst.name} ({worst.complexity})" if worst else "-"))
        total_sloc, weighted = total_sloc + sloc, weighted + mi * sloc
    print(f"{'file':28s} {'MI':>6s} {'SLOC':>5s} {'LLOC':>5s} {'V':>8s} {'G':>4s} {'C%':>6s} {'C-term':>7s}  most complex block")
    for name, mi, sloc, lloc, volume, complexity, comments, worst in rows:
        print(f"{name:28s} {mi:6.1f} {sloc:5d} {lloc:5d} {volume:8.1f} {complexity:4d} {comments:6.1f} "
              f"{comment_term(comments):7.1f}  {worst}")
    print(f"\nMI of the submission (average weighted by SLOC, as scoring.py): {weighted / total_sloc:.1f}")
    for name, mi, sloc, lloc, volume, complexity, comments, _ in rows:
        hints = []
        if comments < 35 and volume > 0:
            hints.append(f"comments/docstrings at {comments:.0f} %: bring them towards 55 %")
        if comments > 120:
            hints.append(f"comments at {comments:.0f} %: too many, the index goes down")
        if lloc > 60:
            hints.append(f"{lloc} logical lines: split into cohesive modules")
        if hints:
            print(f"  {name}: " + "; ".join(hints))


if __name__ == "__main__":
    report(pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "."))
