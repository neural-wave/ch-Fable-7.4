"""The bookings of one policy as the submission books them, next to the diagnostic files: `lab viz policy <id>`.

`tracer(folder)` subclasses the FundAccounting of a submission folder. Its replay is the submission's own code; the
subclass only wraps the fund account of the replayed policy, which writes down every booking with its day, event,
type (the NRBOOK codes), fund, pot, amount and units. The submission is not changed, and a scratch copy of
`lab ablate` can be traced the same way.

The diagnostic side is NRBOOK, whose blank amounts and units of the PRM/ADM/AMC/RSK bookings come from
t3_booking, and t3_holding for the units on the valuation dates. NRBOOK keeps the bookings of reversed events, so
they are left out as the submission leaves them out, and so are bookings of nothing (no amount, no units), which
NRBOOK has for some switches only. Bookings are matched on (event, type, fund, pot); amounts are signed by the
direction of the money: into units (PRM, SWI) positive, out of units negative.

`timeline` adds what the other files say about the policy: its rows in the diffs.parquet of every task, the units
of t3_holding, the policy values of t3_surrender_value and the projection of the offer against t2_projection_year.
The first of them that differs is the first divergence.
"""
import datetime as dt
import functools
import importlib
import json
from decimal import Decimal

import polars as pl

from . import paths, score, store

CHARGE_TYPES = {"admin": "ADM", "management": "AMC", "risk": "RSK"}  # ChargeRules.monthly_charges -> NRBOOK
SALE_TYPES = {400: "WDR", 410: "SUR", 500: "DTH"}  # EVTTP of the sales -> NRBOOK
OUTFLOWS = {"ADM", "AMC", "RSK", "SWO", "WDR", "SUR", "DTH"}
COUNTED = {"PRM", "ADM", "AMC", "RSK"}  # the booking types whose amounts NRBOOK leaves blank (t3_booking has them)
REVERSAL = 900  # EVTTP; EV_REVNR is the event it reverses
MATCH = ["event", "type", "fund", "pot", "seq"]
TASKS = ("t0_commission", "t1_next_due_dates", "t2_projected_maturity_value", "t3_surrender_value",
         "t4_annual_statement")
SHOWN = 30  # differences kept per policy


def tracer(folder=paths.SUBMISSION):
    """The Traced subclass of the submission's FundAccounting, loaded from `folder` like check.py loads it."""
    score.load_submission(folder)
    FundAccounting = importlib.import_module("funds.accounting").FundAccounting
    PolicyAccounting = importlib.import_module("funds.replay").PolicyAccounting
    FundAccount = importlib.import_module("funds.account").FundAccount

    class TracedAccount(FundAccount):
        """The fund account of one policy that tells its policy about every change of units."""

        def __init__(self, market, currency, policy):
            super().__init__(market, currency)
            self.policy = policy

        def book(self, key, amount, day_, **price):
            before = self.units[key]
            super().book(key, amount, day_, **price)
            self.policy.booked(key, amount, self.units[key] - before, day_)

        def sell(self, key, share, day_):
            before = self.units[key]
            amount = super().sell(key, share, day_)
            self.policy.booked(key, -amount, self.units[key] - before, day_, selling=True)
            return amount

    class TracedPolicy(PolicyAccounting):
        """The replay of the submission, with the booking being processed known to the account."""

        def __init__(self, accounting, policy_id):
            super().__init__(accounting, policy_id)
            self.account = TracedAccount(accounting.market, self.account.prices.currency, self)
            self.log, self.current, self.pending_charges = [], None, []
            compute = self.rules.monthly_charges

            def monthly_charges(*args):  # charge_run cancels them holding by holding, in this order
                charges = compute(*args)
                self.pending_charges = [(CHARGE_TYPES[name], key) for key in self.account.holdings() for name in charges]
                return charges
            self.rules.monthly_charges = monthly_charges

        def bookings(self):
            return [booking._replace(apply=functools.partial(self.processing, booking)) for booking in super().bookings()]

        def processing(self, booking, day_):
            self.current = booking
            booking.apply(day_)

        def booked(self, key, amount, units, day_, selling=False):
            handler, args = self.current.apply.func.__name__, self.current.apply.args
            if handler == "charge_run":
                kind, charged = self.pending_charges.pop(0)
                assert charged == key, (charged, key)
            elif handler == "invest":
                kind = "PRM"
            elif handler == "switch":
                kind = "SWO" if selling else "SWI"
            else:
                kind = SALE_TYPES[args[0]["EV_EVTTP"]]
            self.log.append({"day": day_, "event": self.current.event, "type": kind, "fund": key[0], "pot": key[1],
                             "amount": abs(Decimal(amount)) * (-1 if kind in OUTFLOWS else 1), "units": units})

    class Traced(FundAccounting):
        """The FundAccounting of the submission whose replays keep the log of their bookings."""

        def replay(self, policy_id, days):
            policy = TracedPolicy(self, policy_id)
            policy.replay(days)
            return policy

    return Traced


def computed(log):
    """The bookings of a traced replay as a DataFrame, numbered within (event, type, fund, pot)."""
    schema = {"day": pl.Date, "event": pl.Int64, "type": pl.String, "fund": pl.String, "pot": pl.String,
              "amount": pl.Decimal(38, 2), "units": pl.Decimal(38, 6)}
    return numbered(pl.DataFrame(log, schema=schema) if log else pl.DataFrame(schema=schema))


def numbered(df):
    """Bookings that move something, numbered within (event, type, fund, pot) in processing order."""
    df = df.filter((pl.col("amount") != 0) | (pl.col("units") != 0))
    return df.with_columns(pl.int_range(pl.len()).over(["event", "type", "fund", "pot"]).alias("seq"))


def diagnostic(policy_id):
    """NRBOOK of the policy with the amounts and units of t3_booking, without reversed events; None if absent."""
    found = store.target("t3_booking").filter(pl.col("policy_id") == policy_id)
    if found.is_empty():
        return None
    events = store.load("NREVNT").filter(pl.col("EV_POLNR") == policy_id)
    reversed_events = events.filter(pl.col("EV_EVTTP") == REVERSAL)["EV_REVNR"].to_list()
    books = store.load("NRBOOK").filter(pl.col("BK_POLNR") == policy_id).join(
        found.select("booking_id", "amount_pc", "units"), left_on="BK_BOOKID", right_on="booking_id", how="left")
    books = books.filter(~pl.col("BK_EVTNR").is_in(reversed_events)
                         & (~pl.col("BK_BKTYP").is_in(list(COUNTED)) | pl.col("amount_pc").is_not_null()))
    amount = pl.coalesce("BK_AMTPC", "amount_pc").abs()
    return books.sort("BK_BOOKID").select(
        pl.col("BK_TRDDT").alias("day"), pl.col("BK_EVTNR").alias("event"), pl.col("BK_BKTYP").alias("type"),
        pl.col("BK_FNDID").alias("fund"), pl.col("BK_POTCD").alias("pot"),
        pl.when(pl.col("BK_BKTYP").is_in(list(OUTFLOWS))).then(-amount).otherwise(amount).alias("amount"),
        pl.coalesce("BK_UNITS", "units").alias("units"), pl.col("BK_BOOKID").alias("booking_id"),
    ).pipe(numbered)


def matched(ours, theirs):
    """Both sides joined on (event, type, fund, pot, seq), with the status of every booking.

    same: same day, amount and units; differs: one of them is not the same; only computed / only in NRBOOK.
    """
    joined = ours.join(theirs, on=MATCH, how="full", coalesce=True, suffix="_nrbook")
    same = ((pl.col("day") == pl.col("day_nrbook")) & (pl.col("amount") == pl.col("amount_nrbook"))
            & (pl.col("units") == pl.col("units_nrbook")))
    status = (pl.when(pl.col("day").is_null()).then(pl.lit("only in NRBOOK"))
              .when(pl.col("day_nrbook").is_null()).then(pl.lit("only computed"))
              .when(same).then(pl.lit("same")).otherwise(pl.lit("differs")))
    return joined.with_columns(status.alias("status"), pl.coalesce("day", "day_nrbook").alias("when")).sort("when")


def task_diffs(task, policy_id):
    """The rows of one policy in the newest diffs.parquet of a task (`lab score` or `lab ablate`), or None."""
    found = [f for f in (paths.RUNS / task / "diffs.parquet", paths.RUNS / f"{task}~on" / "diffs.parquet") if f.exists()]
    if not found:
        return None
    return pl.read_parquet(max(found, key=lambda f: f.stat().st_mtime)).filter(pl.col("policy_id") == policy_id)


def month_ends(first, last):
    """The last day of every month from the month of `first` to the month of `last`."""
    days, day_ = [], dt.date(first.year, first.month, 1)
    while day_ <= last:
        following = dt.date(day_.year + day_.month // 12, day_.month % 12 + 1, 1)
        days.append(following - dt.timedelta(days=1))
        day_ = following
    return days


def comparable(value):
    """An amount as a Decimal (3.7 == 3.70), anything else (a date) as its text."""
    try:
        return Decimal(str(value))
    except ArithmeticError:
        return str(value)


def check(day_, source, what, target, value):
    """One value of a file about the policy against the value the rules compute."""
    same = target is not None and value is not None and comparable(target) == comparable(value)
    return {"date": str(day_), "source": source, "what": what, "target": None if target is None else str(target),
            "computed": None if value is None else str(value), "ok": same}


def row_day(task, row, received, offer):
    """(the day a target row belongs to, what it is) for the timeline."""
    if task == "t0_commission":
        return received.get(row["due_nr"]), f"commission of premium {row['due_nr']}"
    if task == "t1_next_due_dates":
        return dt.date.fromisoformat(row["target:due_date"]), f"next due date {row['n']}"
    if task == "t2_projected_maturity_value":
        return offer["PH_ENDDT"], "projected maturity value"
    if task == "t3_surrender_value":
        return row["valuation_date"], "surrender value"
    return dt.date(row["year"], 12, 31), f"annual statement {row['year']}"


def task_checks(policy_id, premiums, offer):
    """The rows of the policy in the five scored targets, from the diffs.parquet of `lab score`."""
    received = {p["PR_DUENR"]: p["PR_RCVDT"] for p in premiums}
    out = []
    for task in TASKS:
        diffs = task_diffs(task, policy_id)
        values = [c.split(":", 1)[1] for c in diffs.columns if c.startswith("diff:")] if diffs is not None else []
        for row in diffs.iter_rows(named=True) if diffs is not None else []:
            day_, what = row_day(task, row, received, offer)
            out += [check(day_, task, f"{what}: {v}" if len(values) > 1 else what, row[f"target:{v}"],
                          row[f"computed:{v}"]) for v in values]
    return out


def projection(accounting, policy_id):
    """[(policy year, anniversary, value)] of the offer projection, with the code of the submission."""
    neuron = importlib.import_module("neuron")
    next_month = importlib.import_module("policies.projection_month").next_month
    offer = importlib.import_module("policies.projection").Projection(
        accounting, policy_id, neuron.table(str(paths.LEGACY), "NRILLU"))
    total, value, years = neuron.months_between(offer.start, offer.offer["PH_ENDDT"]), Decimal(0), []
    for month in range(total):
        value = next_month(offer, value, month)
        if month % 12 == 11 or month == total - 1:
            years.append((month // 12 + 1, neuron.add_months(offer.start, month + 1), value))
    return years


def holdings_checks(policy, policy_id):
    """The units of each (fund, pot) on the valuation dates of t3_holding against the replay."""
    found = store.target("t3_holding").filter(pl.col("policy_id") == policy_id)
    out = []
    for r in found.iter_rows(named=True):
        units = policy.snapshots.get(r["valuation_date"], {}).get((r["fund_id"], str(r["pot"])))
        out.append(check(r["valuation_date"], "t3_holding", f"units of {r['fund_id']} pot {r['pot']}", r["units"], units))
    return out


def worth(account, units, day_):
    """The value of {(fund, pot): units} on `day_` with the bid prices and exchange rates of the account."""
    return sum((account.prices.worth(fund, n, day_) for (fund, _), n in units.items() if n), Decimal(0))


def diagnostic_units(theirs, days):
    """{day: {(fund, pot): units}} of the NRBOOK bookings up to the end of each of the sorted `days`."""
    units, out, rows = {}, {}, theirs.sort(["day", "booking_id"]).iter_rows(named=True)
    pending = next(rows, None)
    for day_ in days:
        while pending is not None and pending["day"] <= day_:
            key = (pending["fund"], pending["pot"])
            units[key] = units.get(key, Decimal(0)) + pending["units"]
            pending = next(rows, None)
        out[day_] = dict(units)
    return out


def monthly(df, days, kinds):
    """The amounts of the booking types `kinds` summed per month of `days` (month ends)."""
    sums = df.filter(pl.col("type").is_in(list(kinds))).group_by(pl.col("day").dt.month_end().alias("month")).agg(
        pl.col("amount").sum())
    found = dict(sums.iter_rows())
    return [float(found.get(day_, 0)) for day_ in days]


def series(bookings, units, account, days):
    """The monthly premiums, charges and month-end value of one side, for the charts."""
    return {"premiums": monthly(bookings, days, {"PRM"}), "charges": monthly(bookings, days, {"ADM", "AMC", "RSK"}),
            "value": [float(worth(account, units.get(d, {}), d)) for d in days]}


def booking_differences(bookings):
    """The bookings that are not the same on both sides, as rows of the difference table."""
    return [{"date": str(r["when"]), "source": "NRBOOK", "status": r["status"],
             "what": f"{r['type']} of event {r['event']}, {r['fund']} pot {r['pot']}",
             "target": f"{r['amount_nrbook']} ({r['units_nrbook']} units)",
             "computed": f"{r['amount']} ({r['units']} units)"}
            for r in bookings.filter(pl.col("status") != "same").iter_rows(named=True)]


def timeline(policy_id, accounting):
    """Everything `lab viz` draws for one policy, as data for JSON (see the module docstring)."""
    offer, versions = accounting.offer(policy_id), accounting.policies[policy_id]
    valuations = store.target("t3_surrender_value").filter(pl.col("policy_id") == policy_id)
    valuation_days = [d for d in sorted(store.target("t3_surrender_value")["valuation_date"].unique())
                      if d >= offer["PH_BEGDT"]]
    last = max([b["day"] for b in accounting.replay(policy_id, []).log] + valuation_days + [offer["PH_BEGDT"]])
    days = month_ends(offer["PH_BEGDT"], last)
    policy = accounting.replay(policy_id, sorted(set(days) | set(valuation_days)))
    ours, theirs = computed(policy.log), diagnostic(policy_id)
    bookings = matched(ours, theirs) if theirs is not None else None
    projected = projection(accounting, policy_id)
    targets = dict(store.target("t2_projection_year").filter(pl.col("policy_id") == policy_id)
                   .select("policy_year", "value").iter_rows())
    checks = [*task_checks(policy_id, accounting.premiums.get(policy_id, []), offer),
              *holdings_checks(policy, policy_id),
              *[check(r["valuation_date"], "t3_surrender_value", "policy value", r["policy_value"],
                      worth(policy.account, policy.snapshots.get(r["valuation_date"], {}), r["valuation_date"]))
                for r in valuations.iter_rows(named=True)],
              *[check(day_, "t2_projection_year", f"projected value at the end of policy year {year}", targets[year],
                      value) for year, day_, value in projected if year in targets]]
    differing = sorted([*(booking_differences(bookings) if bookings is not None else []),
                        *[dict(c, status="differs") for c in checks if not c["ok"]]], key=lambda d: d["date"])
    return {
        "policy": policy_id, "currency": versions[-1]["PH_CCY"], "begin": str(offer["PH_BEGDT"]),
        "end": str(offer["PH_ENDDT"]), "applied": str(offer["PH_APPDT"]), "frequency": offer["PH_FREQ"],
        "payment": offer["PH_PAYMT"], "product": offer["PH_PRDCD"], "funds": sorted({k[0] for k in policy.account.units}),
        "months": [str(d) for d in days],
        "computed": series(ours, policy.snapshots, policy.account, days),
        "nrbook": None if theirs is None else series(theirs, diagnostic_units(theirs, days), policy.account, days),
        "differing_per_month": [sum(1 for x in differing if x["date"][:7] == str(d)[:7]) for d in days],
        "bookings": None if bookings is None else dict(sorted(bookings.group_by("status").len().iter_rows())),
        "projection": [{"year": y, "date": str(d), "computed": float(v),
                        "target": float(targets[y]) if y in targets else None} for y, d, v in projected],
        "valuations": [{"date": str(r["valuation_date"]), "policy_value": float(r["policy_value"]),
                        "surrender_value": float(r["surrender_value"])} for r in valuations.iter_rows(named=True)],
        "checks": {"total": len(checks), "ok": sum(c["ok"] for c in checks),
                   "sources": sorted({c["source"] for c in checks})},
        "first_divergence": differing[0] if differing else None,
        "differences": differing[:SHOWN], "differences_total": len(differing),
    }


def build(policy_ids, folder=paths.SUBMISSION):
    """runs/policies/<id>.json of every policy, with one load of the tables; returns their paths."""
    accounting = tracer(folder)(str(paths.LEGACY))
    out = paths.RUNS / "policies"
    out.mkdir(exist_ok=True)
    written = []
    for policy_id in policy_ids:
        path = out / f"{policy_id}.json"
        path.write_text(json.dumps(timeline(policy_id, accounting), indent=1), encoding="utf-8")
        written.append(path)
    return written
