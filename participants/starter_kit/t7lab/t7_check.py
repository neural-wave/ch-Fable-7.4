"""The checks of t7 to pass before an upload, on the real tax tables: run them with an open-weights model only.

The task PDF asks for custom or open-weights models on the tax data, so this tool prints PASS or FAIL, seconds and
gigabytes, and never a tax value. `--debug` adds the counts of the failed checks and the tracebacks, for the
person or the open model that runs it.

    NEURON_DATA=<participants> POLARS_MAX_THREADS=2 PYTHONPATH="$PWD:$PWD/tools:$PWD/.." python -B -m t7lab.t7_check

It runs like the evaluator: t0 to t4 and then the two t7 functions in one process, which has 5 minutes and 5 GB.
Then it checks:

- the two examples of the task PDF, to the cent and to the day;
- the format of every row: a country, four amounts to the cent, a date or None, None exactly when no tax is due;
- that every tax booking of NRTAXB gets an amount: nothing dropped or zeroed silently;
- that the labels agree with the bases: a tax booked exactly where the calculated base says it was due
  (`due_against_booked`, with no contradiction).

It also reports, as INFO, what the rules handle but a person should look at: the payouts without a country, those
whose residence disagrees with the taxes Neuron booked (the country follows the taxes), and the thresholds.
"""
import argparse
import datetime as dt
import ctypes
import platform
import sys
import time
import traceback
from decimal import Decimal

import polars as pl

import submission
from conventions import TAXES
from legacy import table
from neuron.load import LEGACY
from neuron.targets import TARGETS, scoring
from payouts import payouts
from taxes import tax_bookings

SECONDS, GIGABYTES = 300, 5  # the limits of the evaluator for t0 - t4 and t7 together
EXAMPLES = {  # task PDF, section 4
    "t7_tax_payout": (("BL10000086", 121), ("DE", Decimal("5628.16"), Decimal("1407.04"), Decimal("77.38"),
                                            Decimal("0.00"), dt.date(2006, 8, 10))),
    "t7_tax_annual": (("BL10000044", 2019), (*[Decimal("0.00")] * 3, Decimal("616.11"), *[Decimal("0.00")] * 3)),
}


def run_tasks(debug: bool) -> dict:
    """{task: result} of t0 - t4 and t7 run one after the other, as the evaluator does; None for a task that failed."""
    official, results = scoring(), {}
    for task in [*official.TASKS, *EXAMPLES]:
        arguments = official.arguments(task, official.read_targets(TARGETS, task)) if task in official.TASKS else ()
        started = time.time()
        try:
            results[task] = getattr(submission, task)(str(LEGACY), *arguments)
        except Exception as error:  # the evaluator scores a failed task 0 and goes on
            results[task] = None
            print(f"FAIL  {task}: {type(error).__name__}")
            if debug:
                traceback.print_exc()
        print(f"      {task:30s} {time.time() - started:6.1f} s")
    return results


class MemoryCounters(ctypes.Structure):  # PROCESS_MEMORY_COUNTERS of the Windows API, up to the peak working set
    _fields_ = [("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong), ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t), ("rest", ctypes.c_size_t * 6)]


def peak_gigabytes() -> float:
    """The peak memory of this process: macOS counts it in bytes, Linux in kilobytes, Windows by its API."""
    if platform.system() == "Windows":
        kernel = ctypes.windll.kernel32
        kernel.GetCurrentProcess.restype = ctypes.c_void_p  # a handle: 64 bits, not the default int
        kernel.K32GetProcessMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.POINTER(MemoryCounters), ctypes.c_ulong]
        counters = MemoryCounters(cb=ctypes.sizeof(MemoryCounters))
        kernel.K32GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb)
        return counters.PeakWorkingSetSize / 1024**3
    import resource  # Unix only
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return peak / 1024**3 if platform.system() == "Darwin" else peak / 1024**2


def is_amount(value) -> bool:
    return isinstance(value, Decimal) and value == value.quantize(Decimal("0.01"))


def payout_row_ok(value) -> bool:
    country, *amounts, remittance = value
    no_tax = not any(amounts[1:3])  # nothing withheld: no withholding, no surcharges (the stamp duty is collected)
    return (isinstance(country, str) and all(map(is_amount, amounts)) and (remittance is None) == no_tax
            and (remittance is None or isinstance(remittance, dt.date)))


def failures(name: str, count: int, debug: bool) -> bool:
    """Print the check `name` as PASS when `count` (rows that break it) is 0; the count only with `debug`."""
    print(f"{'PASS' if count == 0 else 'FAIL'}  {name}" + (f" ({count} rows)" if debug and count else ""))
    return count == 0


def info(name: str, count: int, debug: bool):
    """Print `name` as INFO: the rules handle it, a person looks at it; the count of rows only with `debug`."""
    print(f"INFO  {name}: {'none' if count == 0 else 'some'}" + (f" ({count} rows)" if debug and count else ""))


def label_checks(debug: bool) -> list[bool]:
    """Every booking has an amount; the payouts without a country or against the booked taxes as INFO."""
    booked = table(LEGACY, "NRTAXB")
    amounts = tax_bookings(str(LEGACY))
    rows = payouts(str(LEGACY))
    disagree = rows.filter(pl.col("BOOKED_CNTRY").is_not_null() & pl.col("BOOKED_CNTRY").ne_missing(pl.col("AD_CNTRY")))
    countries = booked.filter(pl.col("TB_TAXTP").is_in(["VST", "SOS", "KST"])).group_by("TB_POLNR", "TB_EVTNR").agg(
        pl.col("TB_TAXTP").replace_strict(TAXES).n_unique().alias("countries"))
    thresholds = table(LEGACY, "NRTAXR").filter(pl.col("TX_THRSH").fill_null(0).ne(0))["TX_TAXTP"].unique().sort()
    print(f"INFO  TX_THRSH is set for the tax types: {', '.join(thresholds) or 'none'} (no rule reads it)")
    info("payouts without a country (no tax booked, no address known)", rows["COUNTRY"].null_count(), debug)
    info("payouts whose residence disagrees with the booked taxes (the country follows the taxes)", disagree.height,
         debug)
    return [failures("every NRTAXB booking of a known type gets a row",
                     booked.filter(pl.col("TB_TAXTP").is_in(list(TAXES))).height - amounts.height, debug),
            failures("no NRTAXB booking of a type without a rule",
                     booked.filter(pl.col("TB_TAXTP").is_in(list(TAXES)).not_()).height, debug),
            failures("no tax booking with a null amount", amounts["TB_AMOUNT"].null_count(), debug),
            failures("no payout with taxes of two countries", countries.filter(pl.col("countries").gt(1)).height,
                     debug)]


def due_against_booked(debug: bool) -> list[bool]:
    """The labels against the bases: where the calculated base says a tax was due, NRTAXB must book it, and nowhere
    else. Every rule must have no contradiction:

    - CH: VST exactly when the holder objected to the reporting (AD_TAXST E) and the base is above TX_THRSH;
    - IT: SOS exactly when the gain is above 0 and the payout is no death claim;
    - DE: KST exactly when the base is above 0, from the first KST that Neuron booked on (death claims left out);
    - DE: KIS exactly with a KST, for a church member (AD_CHURCH J), from the first KIS rate on;
    - IT: a BOC on a withdrawal only after a BOL of the policy.
    """
    booked, rates = table(LEGACY, "NRTAXB"), table(LEGACY, "NRTAXR")
    flags = booked.group_by("TB_POLNR", "TB_EVTNR").agg(
        *[pl.col("TB_TAXTP").eq(tax).any().alias(tax) for tax in ["VST", "SOS", "KST", "KIS"]])
    events = table(LEGACY, "NREVNT").select(TB_POLNR="EV_POLNR", TB_EVTNR="EV_EVTNR", EVENT_TYPE="EV_EVTTP")
    vst = rates.filter(pl.col("TX_TAXTP").eq("VST")).select("TX_VLDFR", "TX_VLDTO", "TX_THRSH")
    rows = payouts(str(LEGACY)).join(events, on=["TB_POLNR", "TB_EVTNR"], how="left")
    limits = rows.select("TB_POLNR", "TB_EVTNR", "TB_EFFDT").join(vst, how="cross").filter(
        pl.col("TB_EFFDT").is_between(pl.col("TX_VLDFR"), pl.col("TX_VLDTO"))).group_by("TB_POLNR", "TB_EVTNR").agg(
        THRESHOLD=pl.col("TX_THRSH").max())
    rows = rows.join(flags, on=["TB_POLNR", "TB_EVTNR"], how="left").join(
        limits, on=["TB_POLNR", "TB_EVTNR"], how="left").with_columns(pl.col("VST", "SOS", "KST", "KIS").fill_null(False))
    first_kst = booked.filter(pl.col("TB_TAXTP").eq("KST"))["TB_EFFDT"].min()
    first_kis = rates.filter(pl.col("TX_TAXTP").eq("KIS"))["TX_VLDFR"].min()
    base, country, death = pl.col("TAXABLE_BASE"), pl.col("COUNTRY"), pl.col("EVENT_TYPE").eq(500)
    rules = {"CH VST <=> objection and base above TX_THRSH": (country.eq("CH"), pl.col("AD_TAXST").eq("E").and_(
                 base.gt(pl.col("THRESHOLD"))), "VST"),
             "IT SOS <=> gain above 0, no death claim": (country.eq("IT"), base.gt(0).and_(death.not_()), "SOS"),
             "DE KST <=> base above 0 (from the first KST)": (country.eq("DE").and_(death.not_()).and_(
                 pl.col("TB_EFFDT").ge(first_kst)), base.gt(0), "KST"),
             "DE KIS <=> KST and church member (from the KIS rate)": (country.eq("DE").and_(pl.col("KST")).and_(
                 pl.col("TB_EFFDT").ge(first_kis)), pl.col("AD_CHURCH").eq("J"), "KIS")}
    oks = [failures(f"labels: {name}", rows.filter(scope).filter(due.fill_null(False).ne(pl.col(tax))).height, debug)
           for name, (scope, due, tax) in rules.items()]
    accrued = booked.filter(pl.col("TB_TAXTP").eq("BOL")).select("TB_POLNR", BOL_CHGTS="TB_CHGTS")
    collected = booked.filter(pl.col("TB_TAXTP").eq("BOC")).join(events, on=["TB_POLNR", "TB_EVTNR"]).filter(
        pl.col("EVENT_TYPE").eq(400))
    unaccrued = collected.join(accrued, on="TB_POLNR", how="left").group_by("TB_BOOKID").agg(
        AFTER_BOL=pl.col("BOL_CHGTS").lt(pl.col("TB_CHGTS")).fill_null(False).any()).filter(pl.col("AFTER_BOL").not_())
    return [*oks, failures("labels: a BOC on a withdrawal only after a BOL", unaccrued.height, debug)]


def result_checks(results: dict, debug: bool) -> list[bool]:
    """The format of the two t7 results and the two examples of the task PDF."""
    payout, annual = results["t7_tax_payout"], results["t7_tax_annual"]
    if payout is None or annual is None:
        return [False]
    oks = [failures("payout rows: country, 4 amounts to the cent, a date or None (None exactly when nothing was withheld)",
                    sum(not payout_row_ok(value) for value in payout.values()), debug),
           failures("annual rows: 7 amounts to the cent, at least one not 0",
                    sum(not (all(map(is_amount, value)) and any(value)) for value in annual.values()), debug)]
    for task, (key, expected) in EXAMPLES.items():
        got = results[task].get(key)
        oks.append(failures(f"PDF example {task} {key}", int(got != expected), debug))
    return oks


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--debug", action="store_true", help="counts of the failed checks and tracebacks")
    debug = parser.parse_args().debug
    started = time.time()
    results = run_tasks(debug)
    seconds, gigabytes = time.time() - started, peak_gigabytes()
    oks = [failures(f"t0 - t4 and t7 in {seconds:.0f} s: under half of {SECONDS} s (the evaluator has 2 slow CPUs)",
                    int(seconds > SECONDS / 2), debug),
           failures(f"peak memory {gigabytes:.2f} GB: under 80 % of {GIGABYTES} GB", int(gigabytes > GIGABYTES * 0.8),
                    debug),
           *result_checks(results, debug), *label_checks(debug), *due_against_booked(debug)]
    print("\nALL PASS: ready to upload" if all(oks) else "\nSOMETHING FAILED: do not upload yet")
    sys.exit(0 if all(oks) else 1)


if __name__ == "__main__":
    main()
