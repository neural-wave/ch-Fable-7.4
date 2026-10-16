"""Harness della manutenibilita': il maintainability index di radon scomposto file per file.

Calcola lo stesso indice di starter_kit/scoring.py (radon mi_visit con multi=True, media dei file pesata per
righe di codice) e mostra le quattro componenti della formula, per capire quale leva tirare:

    MI = (171 - 5.2 ln V - 0.23 G - 16.2 ln LLOC + 50 sin(sqrt(2.46 * C in radianti))) * 100 / 171

    V     volume di Halstead: cresce con operatori e operandi aritmetici/logici (le chiamate non contano)
    G     complessita' ciclomatica totale del file: ogni if, for, while, and, or, except, comprehension
    LLOC  righe logiche: il termine pesa piu' di tutti, quindi file piccoli e coesi
    C     righe di commento (#) + righe di docstring multi-riga, in % delle righe di codice.
          Le docstring di UNA riga non contano. Ottimo intorno al 55 %, buono tra 35 % e 80 %,
          oltre il 120 % l'indice torna a scendere.

Uso:  python mi_report.py ../esempio_consegna
"""
import math
import pathlib
import sys

from radon.complexity import cc_visit
from radon.metrics import mi_parameters, mi_visit
from radon.raw import analyze


def comment_term(percent):
    """Il contributo (non normalizzato, massimo 50) del rapporto commenti/codice."""
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
    print(f"{'file':28s} {'MI':>6s} {'SLOC':>5s} {'LLOC':>5s} {'V':>8s} {'G':>4s} {'C%':>6s} {'C-term':>7s}  blocco piu' complesso")
    for name, mi, sloc, lloc, volume, complexity, comments, worst in rows:
        print(f"{name:28s} {mi:6.1f} {sloc:5d} {lloc:5d} {volume:8.1f} {complexity:4d} {comments:6.1f} "
              f"{comment_term(comments):7.1f}  {worst}")
    print(f"\nMI della consegna (media pesata per SLOC, come scoring.py): {weighted / total_sloc:.1f}")
    for name, mi, sloc, lloc, volume, complexity, comments, _ in rows:
        hints = []
        if comments < 35 and volume > 0:
            hints.append(f"commenti/docstring al {comments:.0f} %: portarli verso il 55 %")
        if comments > 120:
            hints.append(f"commenti al {comments:.0f} %: troppi, l'indice scende")
        if lloc > 60:
            hints.append(f"{lloc} righe logiche: dividere in moduli coesi")
        if hints:
            print(f"  {name}: " + "; ".join(hints))


if __name__ == "__main__":
    report(pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "."))
