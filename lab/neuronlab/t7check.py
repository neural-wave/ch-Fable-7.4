"""`lab t7check`: what can be measured of t7 without target values.

t7 (such.pdf) has no target files. The functions of submission.py are checked against what the lab does have,
and every number is exact:
- NRTAXB, the tax bookings of Neuron without amounts, on every payout and every year: a payout is taxed when Neuron
  booked a tax on it, in the country of the booked tax types; a policy and year has an annual amount for each tax
  type booked in that year. This is the measure to improve.
- the two examples of the task description: two rows only, a sanity check of the amounts, never a rule to fit.
This is consistency with Neuron's own bookings, not the official score.
"""
import collections
import traceback
import datetime as dt
from decimal import Decimal

import polars as pl

from . import derived, paths, store
from .score import firewall, load_submission
from .store import scoring

EXAMPLES = {  # such.pdf, section 4
    "t7_tax_payout": {("BL10000086", 121): ("DE", Decimal("5628.16"), Decimal("1407.04"), Decimal("77.38"),
                                            Decimal("0.00"), dt.date(2006, 8, 10))},
    "t7_tax_annual": {("BL10000044", 2019): tuple(Decimal(v) for v in
                                                  ("0.00", "0.00", "0.00", "616.11", "0.00", "0.00", "0.00"))},
}
COUNTRY = {"KST": "DE", "SOL": "DE", "KIS": "DE", "VST": "CH", "SOS": "IT", "BOL": "IT", "BOC": "IT"}
ANNUAL = ["STP", "VST", "SOS", "BOL", "KST", "SOL", "KIS"]  # ch_stp, ch_vst, it_sos, it_bol, de_kst, de_sol, de_kis
SHOWN = 8


def dropped(task, raw):
    """Rows that scoring.normalize drops silently, with the reason: they count as wrong in the official score.

    A remittance date may be empty (None), but the tuple must still have all its values: a shorter tuple (the last
    value left out) or an empty amount ("" or None instead of 0.00) loses the whole row.
    """
    spec = scoring.spec(task)
    reasons, examples = collections.Counter(), {}
    for key, value in (raw or {}).items():
        try:
            spec.make_key(key)
            spec.make_value(value)
        except (TypeError, ValueError, ArithmeticError) as e:
            parts = value if isinstance(value, (tuple, list)) else (value,)
            reason = (f"{len(parts)} values instead of {len(spec.value)}" if len(parts) != len(spec.value)
                      else f"{type(e).__name__} on a value")
            reasons[reason] += 1
            examples.setdefault(reason, (key, value))
    if not reasons:
        return [f"  rows the scoring drops (wrong format): 0 of {len(raw or {})}"]
    lines = [f"  rows the scoring drops (wrong format, they count as wrong): {sum(reasons.values())} of {len(raw)}"]
    return lines + [f"    {n} x {r}, e.g. {examples[r]}" for r, n in reasons.most_common()]


def examples(task, predictions):
    lines = []
    for key, expected in EXAMPLES[task].items():
        got = predictions.get(key)
        mark = "ok" if got == expected else "WRONG"
        lines.append(f"  example {key}: {mark}; expected {tuple(map(str, expected))}, computed "
                     f"{tuple(map(str, got)) if got else 'missing'}")
    return lines


def payouts(predictions):
    """Taxed or not, and the country, of every payout event, against the tax types NRTAXB books on it."""
    booked = store.target("t7_payout_taxes")
    counts, wrong = collections.Counter(), []
    for row in booked.iter_rows(named=True):
        key = (row["policy_id"], row["event_nr"])
        types = {t for t in derived.PAYOUT_TAXES if row[t] == "yes"}
        got = predictions.get(key)
        if got is None:
            counts["missing"] += 1
            wrong.append(f"{key} missing, NRTAXB books {sorted(types) or 'nothing'}")
            continue
        country, _, withholding, surcharges, stamp, remitted = got
        taxed = withholding + surcharges + stamp > 0
        counts["taxed agrees"] += taxed == bool(types)
        if taxed != bool(types):
            wrong.append(f"{key} computed {'taxed' if taxed else 'not taxed'} {country}, NRTAXB books "
                         f"{sorted(types) or 'nothing'}")
        countries = {COUNTRY[t] for t in types}
        if taxed and len(countries) == 1:
            counts["country checked"] += 1
            counts["country agrees"] += country == next(iter(countries))
            if country != next(iter(countries)) and taxed == bool(types):
                wrong.append(f"{key} country {country}, NRTAXB books {sorted(types)}")
        counts["remittance date iff withheld"] += (remitted is not None) == taxed
    extra = len(set(predictions) - set(zip(booked["policy_id"], booked["event_nr"])))
    lines = [f"Payouts (NRTAXB, {booked.height} payout events): computed {booked.height - counts['missing']}, "
             f"missing {counts['missing']}, not payouts {extra}",
             f"  taxed or not as NRTAXB: {counts['taxed agrees']} / {booked.height}",
             f"  country of the booked taxes: {counts['country agrees']} / {counts['country checked']}",
             f"  remittance date exactly when something is withheld: {counts['remittance date iff withheld']}"
             f" / {booked.height - counts['missing']}"]
    return lines + [f"  {w}" for w in wrong[:SHOWN]]


def annual(predictions):
    """Per policy and year: the tax types with an amount, against the types NRTAXB books in that year."""
    tb = store.load("NRTAXB").filter(pl.col("TB_TAXTP").is_in(ANNUAL))
    booked = collections.defaultdict(set)
    for p, d, t in tb.select("TB_POLNR", "TB_EFFDT", "TB_TAXTP").iter_rows():
        if d is not None:
            booked[(p, d.year)].add(t)
    computed = {k: {t for t, v in zip(ANNUAL, values) if v != 0} for k, values in predictions.items()}
    keys = set(booked) | set(computed)
    agree = sum(computed.get(k, set()) == booked.get(k, set()) for k in keys)
    wrong = [f"{k} computed {sorted(computed.get(k, set()))}, NRTAXB books {sorted(booked.get(k, set()))}"
             for k in sorted(keys) if computed.get(k, set()) != booked.get(k, set())]
    lines = [f"Annual (policy, year): same tax types as NRTAXB on {agree} / {len(keys)} keys "
             f"(computed {len(computed)}, booked {len(booked)}; BOC is left out)"]
    return lines + [f"  {w}" for w in wrong[:SHOWN]]


def check(folder=None):
    module = load_submission(folder or paths.SUBMISSION)
    lines = ["# t7check (no targets: examples of such.pdf and consistency with NRTAXB)", ""]
    for task, compare in (("t7_tax_payout", payouts), ("t7_tax_annual", annual)):
        if not hasattr(module, task):
            lines.append(f"{task}: no function in submission.py")
            continue
        try:
            with firewall():
                raw = getattr(module, task)(str(paths.LEGACY))
            predictions = scoring.normalize(task, raw)
        except Exception as e:  # the agent must see the error of one function and still the check of the other
            lines += [f"## {task}", "", f"  the function fails: {type(e).__name__}: {e}",
                      f"  at {traceback.extract_tb(e.__traceback__)[-1]}", ""]
            continue
        lines += [f"## {task}", ""] + dropped(task, raw) + compare(predictions)
        lines += ["  examples of such.pdf (2 rows, a sanity check only):"] + examples(task, predictions) + [""]
    text = "\n".join(lines)
    (paths.run_dir("t7_payout_taxes") / "t7check.md").write_text(text)
    return text
