"""How many rows of t7 each open convention changes: the size of the bet of every leaderboard probe.

The t7 leaderboard scores a handful of rows that the actuary picks, every two hours, so a probe should flip the
convention that changes the most rows and keep the others. Every VARIANT flips conventions of `conventions.py`
(in every module that imported them) and runs the two t7 functions in a fresh process; the table counts the rows
that differ from the submission as it is, per column and per country.

    NEURON_DATA=<participants> PYTHONPATH="$PWD:$PWD/tools" python -B -m neuron.t7_variants [--variant NAME ...]
"""
import argparse
import collections
import pickle
import subprocess
import sys
import tempfile
import pathlib

from conventions import CALENDAR
from neuron.load import LEGACY

NEURON_CALENDAR = dict(CALENDAR, years=list(CALENDAR["years"]))  # Neuron's own calendar, as a literal for the worker
VARIANTS = {  # name -> {convention: value} to flip
    "base as calculated without withholding": {"BASE_WITHOUT_TAX": True},
    "no remittance for stamp duty alone": {"STAMP_DUTY_REMITTED": False},
    "remittance on a business day of the tax office": {"REMITTANCE_SHIFTED": ["DE", "IT", "CH"]},
    "remittance on a business day of Neuron": {
        "REMITTANCE_SHIFTED": ["DE", "IT", "CH"],
        "REMITTANCE_CALENDARS": dict.fromkeys(["DE", "IT", "CH"], NEURON_CALENDAR)},
    "remittance on the 10th everywhere": {"REMITTANCE": {"DE": 9, "IT": 9, "CH": 9}},
    "rounding by system, not by country": {"ROUNDED_BY_SYSTEM": True},
    "HEV not in the withholding": {"HALF_INCOME_WITHHELD": False},
}
COLUMNS = {"t7_tax_payout": ["country", "taxable_base", "withholding", "surcharges", "stamp_duty", "remittance"],
           "t7_tax_annual": ["ch_stp", "ch_vst", "it_sos", "it_bol", "de_kst", "de_sol", "de_kis"]}


def run(flips: dict, out: str):
    """Worker: the two t7 results with the conventions `flips`, pickled to `out`."""
    import submission  # imports every module of the submission, so the flips reach all copies
    for module in list(sys.modules.values()):
        for name, value in flips.items():
            if hasattr(module, name) and getattr(module, "__file__", "") and "site-packages" not in module.__file__:
                setattr(module, name, value)
    results = {task: getattr(submission, task)(str(LEGACY)) for task in COLUMNS}
    pathlib.Path(out).write_bytes(pickle.dumps(results))


def results_of(flips: dict) -> dict:
    with tempfile.TemporaryDirectory() as folder:
        out = str(pathlib.Path(folder, "results.pkl"))
        subprocess.run([sys.executable, "-B", "-m", "neuron.t7_variants", "--worker", repr(flips), out], check=True,
                       stdin=subprocess.DEVNULL)
        return pickle.loads(pathlib.Path(out).read_bytes())


def differences(base: dict, other: dict, columns: list[str]) -> collections.Counter:
    """Rows of `base` that differ in `other` (missing rows count), per column, per country and in all."""
    counts = collections.Counter()
    for key, value in base.items():
        changed = other.get(key)
        if changed == value:
            continue
        counts["rows"] += 1
        counts.update(name for i, name in enumerate(columns) if changed is None or changed[i] != value[i])
        if columns[0] == "country":
            counts[f"in {value[0]}"] += 1
    counts["new rows"] += len(other.keys() - base.keys())
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--variant", choices=VARIANTS, action="append", help="only these variants")
    parser.add_argument("--worker", nargs=2, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        import ast
        return run(ast.literal_eval(args.worker[0]), args.worker[1])
    base = results_of({})
    print({task: len(rows) for task, rows in base.items()}, "rows as submitted")
    for name in args.variant or VARIANTS:
        other = results_of(VARIANTS[name])
        print(f"\n{name}: {VARIANTS[name]}")
        for task, columns in COLUMNS.items():
            counts = differences(base[task], other[task], columns)
            print(f"  {task}: " + (", ".join(f"{label} {n}" for label, n in counts.items() if n) or "no change"))


if __name__ == "__main__":
    main()
