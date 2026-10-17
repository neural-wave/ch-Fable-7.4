"""Checks on the data of the hypotheses in the "Analysis and Strategy" document (Lifeware challenge, The Neuron Migration).

It reproduces the numbers quoted in ../PLAN.md by counting the EXACT rows against the train targets and the
diagnostic files. It is an analysis tool: it reads the targets, so it is NOT part of the submission
(submission.py may not read them, except in t5).

Usage (Python 3.14):
    pip install polars holidays
    python -B tools/data_checks.py --data /path/to/LifewareChallenge/participants
    LIFEWARE_DATA=/path/to/LifewareChallenge/participants python -B tools/data_checks.py --sample 0
Without --data it uses the variable LIFEWARE_DATA, then looks for a participants/ folder upwards from here and
from the current folder.
"""
import argparse
import bisect
import calendar
import datetime as dt
import os
import pathlib
import time
import warnings
from decimal import ROUND_DOWN, ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal as D

import holidays
import polars as pl

CONV = dt.date(2007, 8, 11)  # event 800 "system conversion" (user CONV2007): COBOL before, Java after
EXTRACT = dt.date(2026, 6, 30)
MONTHS = {"M": 1, "Q": 3, "H": 6, "J": 12}
CENT, UNIT6 = D("0.01"), D("0.000001")
TI = holidays.CH(subdiv="TI", years=range(1993, 2029))
warnings.filterwarnings("ignore", message="Sortedness of columns cannot be checked")  # join_asof by fund: input already sorted


def era_rounding(day):
    """Confirmed era convention: COBOL truncates, Neuron NG (Java) rounds half up."""
    return ROUND_DOWN if day < CONV else ROUND_HALF_UP


def is_business_day(day):
    """Ticino business day: Monday to Friday and not a Ticino holiday (Good Friday is NOT a holiday)."""
    return day.weekday() < 5 and day not in TI


def next_business_day(day, strictly_after=False):
    day = day + dt.timedelta(days=1) if strictly_after else day
    while not is_business_day(day):
        day += dt.timedelta(days=1)
    return day


def add_months(day, n, anchor_day=None):
    """Adds n months keeping the anchor day, clamped to the last day of the month."""
    y, m = divmod(day.month - 1 + n, 12)
    y, m = day.year + y, m + 1
    return dt.date(y, m, min(anchor_day or day.day, calendar.monthrange(y, m)[1]))


class Export:
    """Generic loader driven by NRDICT: types, implied decimals, CYYMMDD dates (impossible ones too)."""

    def __init__(self, root):
        self.legacy, self.targets = root / "legacy", root / "targets"
        d = pl.read_csv(self.legacy / "NRDICT.csv", separator=";", infer_schema_length=0)
        self.types = {(r["DC_TABLE"].strip(), r["DC_COLUMN"].strip()): r["DC_TYPE"].strip() for r in d.iter_rows(named=True)}
        self.cache = {}

    def t(self, name):
        if name not in self.cache:
            df = pl.read_csv(self.legacy / f"{name}.csv", separator=";", infer_schema_length=0)
            self.cache[name] = df.select([e for col in df.columns for e in self._convert(name, col)])
        return self.cache[name]

    def _convert(self, table, col):
        kind, c = self.types.get((table, col), "C"), pl.col(col).str.strip_chars()
        if kind == "N":
            return [c.cast(pl.Int64).alias(col)]
        if kind == "D":
            n = c.cast(pl.Int64)
            iso = pl.concat_str([(1900 + n // 10000).cast(pl.Utf8), pl.lit("-"), (n // 100 % 100).cast(pl.Utf8).str.zfill(2),
                                 pl.lit("-"), (n % 100).cast(pl.Utf8).str.zfill(2)])
            day = pl.when(n == 0).then(None).when(n == 9999999).then(pl.date(2999, 12, 31)).otherwise(iso.str.to_date("%Y-%m-%d", strict=False))
            return [day.alias(col), n.alias(col + "_RAW")]
        if kind == "T":
            return [c.str.strptime(pl.Datetime, "%Y%m%d%H%M%S", strict=False).alias(col)]
        return [c.alias(col)]

    def target(self, name):
        key = "T:" + name
        if key not in self.cache:
            self.cache[key] = pl.read_csv(self.targets / f"{name}.csv", infer_schema_length=0)
        return self.cache[key]


def by_policy(df, key):
    out = {}
    for r in df.iter_rows(named=True):
        out.setdefault(r[key], []).append(r)
    return out


def valid_on(rows, day, lo, hi, version=None):
    """Row valid on `day` (both ends included); if several rows are valid, the highest version wins."""
    best = None
    for r in rows:
        if r[lo] <= day <= r[hi] and (best is None or (version and r[version] >= best[version])):
            best = r
    return best


def pct(ok, tot):
    return f"{ok:>9,} / {tot:<9,} = {ok / tot:9.4%}" if tot else "n/a"


# ----------------------------------------------------------------------------------------------- data

def check_data_traps(x):
    print("\n== Data: traps of the format")
    pers = x.t("NRPERS")
    bad = pers.filter(pl.col("PS_BIRTH").is_null())
    print(f"impossible birth dates in NRPERS: {bad.height}  {bad['PS_BIRTH_RAW'].to_list()}")
    print("PS_SMOKE (SCHEMA says Y/N):", dict(sorted(pers["PS_SMOKE"].value_counts().iter_rows())))
    ev = x.t("NREVNT").filter(pl.col("EV_EVTTP") == 800)
    print("event 800 (system conversion), (date, user, policies):",
          [(str(a), b, c) for a, b, c in ev.group_by("EV_EFFDT", "EV_USRID").len().iter_rows()])
    users = x.t("NREVNT").filter(pl.col("EV_SRC") == "B").group_by("EV_USRID").agg(
        pl.col("EV_CHGTS").min().alias("first"), pl.col("EV_CHGTS").max().alias("last"))
    for u, a, b in users.sort("first").iter_rows():
        print(f"batch user {u:9s} from {a} to {b}")
    print("tables in the export:", len(list(x.legacy.glob("NR*.csv"))), "(the document lists 23: NRHOLD, NRADDR, NRTAXR, NRTAXB are missing)")


# ------------------------------------------------------------------------------------------------- t0

def check_t0(x):
    print("\n== t0 commissions")
    vers = by_policy(x.t("NRPOLH").sort("PH_VRSNR"), "PH_POLNR")
    tier = dict(zip(x.t("NRBROK")["BR_BRKNR"], x.t("NRBROK")["BR_TIER"]))
    ptype = {r["RK_POLNR"]: r["RK_TARKEY"][5] for r in x.t("NRRISK").iter_rows(named=True)}
    comr = by_policy(x.t("NRCOMR").with_columns(pl.concat_str(["CR_TIER", "CR_PAYTP"]).alias("K")), "K")
    tgt = {(r["policy_id"], int(r["due_nr"])): D(r["amount"]) for r in x.target("t0_commission").iter_rows(named=True)}
    prem = x.t("NRPREM").filter(pl.col("PR_STATE") == "P")
    print("premium items with PR_STATE='P' of the train policies:", prem.filter(pl.col("PR_POLNR").is_in(list({p for p, _ in tgt}))).height,
          " target rows:", len(tgt))
    bases = {"broker on PR_RCVDT": lambda p, r: valid_on(vers[p], r["PR_RCVDT"], "PH_VLDFR", "PH_VLDTO", "PH_VRSNR"),
             "broker on PR_DUEDT": lambda p, r: valid_on(vers[p], r["PR_DUEDT"], "PH_VLDFR", "PH_VLDTO", "PH_VRSNR"),
             "first broker": lambda p, r: vers[p][0], "current broker": lambda p, r: vers[p][-1]}
    modes = {"half-up": ROUND_HALF_UP, "half-even": ROUND_HALF_EVEN, "truncation": ROUND_DOWN}
    score, residuals = {}, []
    for r in prem.iter_rows(named=True):
        key = (r["PR_POLNR"], r["PR_DUENR"])
        if key not in tgt:
            continue
        amount = D(r["PR_AMTRC"]) / 100
        for bname, basis in bases.items():
            v = basis(r["PR_POLNR"], r)
            row = valid_on(comr[tier[v["PH_BRKNR"]] + ptype[r["PR_POLNR"]]], r["PR_RCVDT"], "CR_VLDFR", "CR_VLDTO")
            for mname, mode in modes.items():
                hit = (amount * D(row["CR_RATE"]) / 10**6).quantize(CENT, rounding=mode) == tgt[key]
                score[(bname, mname)] = score.get((bname, mname), 0) + hit
                if not hit and bname == "broker on PR_RCVDT" and mname == "half-up":
                    residuals.append((*key, str(amount), str(tgt[key])))
    for k, v in sorted(score.items(), key=lambda kv: -kv[1]):
        print(f"  {k[0]:22s} {k[1]:12s} {pct(v, len(tgt))}")
    listed = set(x.t("NREXCP").filter(pl.col("EX_TARGET").str.starts_with("t0"))["EX_POLNR"])
    print(f"residuals of the best rule: {len(residuals)}  (in NREXCP: {sum(r[0] in listed for r in residuals)})")
    for r in residuals:
        print("   ", r, "NREXCP" if r[0] in listed else "")
    return {r[0] for r in residuals}


# ------------------------------------------------------------------------------------------------- t1

def schedule(v, rule):
    """Due dates after the extract. 'hybrid': COBOL chain with drift until the switch, then a fixed anchor (Java)."""
    step, begin, end = MONTHS[v["PH_FREQ"]], v["PH_BEGDT"], EXTRACT.replace(year=EXTRACT.year + 1)
    anchor = begin
    if rule == "hybrid" and begin < CONV:
        while add_months(anchor, step) < CONV:
            anchor = add_months(anchor, step)  # COBOL: previous due date + period, the day can only go down
    out, k, day = [], 0, anchor
    while day < v["PH_ENDDT"] and day <= end:
        if day > EXTRACT:
            out.append(day)
        k += 1
        day = add_months(day, step) if rule.startswith("chain") else add_months(anchor, k * step, anchor.day)
    return out


def check_t1(x):
    print("\n== t1 next due dates")
    cur = {p: rows[-1] for p, rows in by_policy(x.t("NRPOLH").sort("PH_VRSNR"), "PH_POLNR").items()}
    tgt = {(r["policy_id"], int(r["n"])): (dt.date.fromisoformat(r["due_date"]), dt.date.fromisoformat(r["collection_date"]))
           for r in x.target("t1_next_due_dates").iter_rows(named=True)}
    keys = {}
    for k in tgt:
        keys.setdefault(k[0], []).append(k)
    for rule in ("anchor at PH_BEGDT", "chain from PH_BEGDT", "hybrid"):
        ok = 0
        for p, ks in keys.items():
            v = cur[p]
            dates = schedule(v, rule)
            pred = {(p, i + 1): (d, next_business_day(d) if v["PH_PAYMT"] == "LS" else d) for i, d in enumerate(dates)}
            ok += sum(pred.get(k) == tgt[k] for k in ks)
        print(f"  {rule:20s} {pct(ok, len(tgt))}")
    good_friday = [k for k, v in tgt.items() if v[0] == dt.date(2027, 3, 26) and cur[k[0]]["PH_PAYMT"] == "LS"]
    print(f"  LS due on Good Friday 26.3.2027: {len(good_friday)}, collected on the same day: "
          f"{sum(tgt[k][1] == tgt[k][0] for k in good_friday)}")


# ------------------------------------------------------------------------------------------------- t3

def fx_table(x, upper=True):
    """Rates by currency. CAREFUL: NRFXRT has 80 rows with the code in lower case ('usd', 'chf', ...) on the days
    without the upper-case row: Neuron uses them. upper=False reproduces the error of a case-sensitive lookup."""
    rates = {}
    for c, d, r in x.t("NRFXRT").select("FX_CCY", "FX_RATDT", "FX_RATE").iter_rows():
        rates.setdefault(c.upper() if upper else c, []).append((d, D(r) / 10**6))
    for c in rates:
        rates[c].sort()
    return {c: ([d for d, _ in v], [r for _, r in v]) for c, v in rates.items()}


def fx_on(fx, ccy, day):
    """Last rate published on `day` or before (CHF per unit of the currency)."""
    days, values = fx[ccy]
    return values[bisect.bisect_right(days, day) - 1]


def check_t3_bookings(x, sample):
    print("\n== t3 diagnostic bookings (t3_booking)")
    tb = x.target("t3_booking").with_columns(pl.col("booking_id").cast(pl.Int64))
    bk = x.t("NRBOOK")
    j = tb.join(bk, left_on="booking_id", right_on="BK_BOOKID")
    print("t3_booking rows:", dict(sorted(tb.group_by("booking_type").len().iter_rows())))
    prices = x.t("NRFPRC").sort("FP_CHGTS").group_by("FP_FNDID", "FP_PRCDT").last()  # the latest publication counts
    jp = j.join(prices, left_on=["BK_FNDID", "BK_PRCDT"], right_on=["FP_FNDID", "FP_PRCDT"], how="left").with_columns(
        (pl.col("price").cast(pl.Float64) * 1e6).round(0).cast(pl.Int64).alias("P6"))
    for t, col in (("PRM", "FP_ASKPR"), ("ADM", "FP_BIDPR"), ("AMC", "FP_BIDPR"), ("RSK", "FP_BIDPR")):
        s = jp.filter(pl.col("booking_type") == t)
        print(f"  price {t} = {col[3:6].lower():3s} {pct(s.filter(pl.col('P6') == pl.col(col)).height, s.height)}")
    # price date of the charges = last price date <= trade date (as-of lookup)
    pd_ = prices.select(pl.col("FP_FNDID").alias("BK_FNDID"), pl.col("FP_PRCDT").alias("ASOF")).sort("ASOF")
    adm = bk.filter(pl.col("BK_BKTYP") == "ADM").select("BK_FNDID", "BK_TRDDT", "BK_PRCDT").sort("BK_TRDDT")
    a = adm.join_asof(pd_, left_on="BK_TRDDT", right_on="ASOF", by="BK_FNDID", strategy="backward")
    print(f"  ADM price date = last price <= trade date {pct(a.filter(pl.col('ASOF') == pl.col('BK_PRCDT')).height, a.height)}")
    prm_all = bk.filter(pl.col("BK_BKTYP") == "PRM").select("BK_FNDID", "BK_RCVDT", "BK_TRDDT").with_columns(
        (pl.col("BK_RCVDT") + pl.duration(days=1)).alias("AFTER")).sort("AFTER")
    ok = sum(next_business_day(r, strictly_after=True) == t for _, r, t, _ in prm_all.iter_rows())
    print(f"  PRM trade date = next TI business day after the money date         {pct(ok, prm_all.height)}")
    price_days = prices.select(pl.col("FP_FNDID").alias("BK_FNDID"), pl.col("FP_PRCDT").alias("NEXT")).sort("NEXT")
    nxt = prm_all.join_asof(price_days, left_on="AFTER", right_on="NEXT", by="BK_FNDID", strategy="forward")
    print(f"  PRM trade date = first day with a price OF THE FUND after the money date "
          f"{pct(nxt.filter(pl.col('NEXT') == pl.col('BK_TRDDT')).height, nxt.height)}")
    check_prm_amount(x, j.filter(pl.col("booking_type") == "PRM"), sample)
    check_units(x, j, sample)


def check_prm_amount(x, prm, sample):
    vers = by_policy(x.t("NRPOLH").sort("PH_VRSNR"), "PH_POLNR")
    tier = dict(zip(x.t("NRBROK")["BR_BRKNR"], x.t("NRBROK")["BR_TIER"]))
    entc, alloc = by_policy(x.t("NRENTC"), "EC_TIER"), by_policy(x.t("NRALLO"), "AL_POLNR")
    agree = by_policy(x.t("NRAGRE").filter(pl.col("AG_FEETP") == "ENT"), "AG_POLNR")
    prem = x.t("NRPREM").select("PR_POLNR", "PR_EVTNR", "PR_AMTRC")
    rows = prm.join(prem, left_on=["BK_POLNR", "BK_EVTNR"], right_on=["PR_POLNR", "PR_EVTNR"])
    rows = rows if sample <= 0 else rows.sample(n=min(sample, rows.height), seed=1)
    score = {}
    for r in rows.iter_rows(named=True):
        p, money = r["BK_POLNR"], r["BK_RCVDT"]
        v = valid_on(vers[p], money, "PH_VLDFR", "PH_VLDTO", "PH_VRSNR")
        rate = D(valid_on(entc[tier[v["PH_BRKNR"]]], money, "EC_VLDFR", "EC_VLDTO")["EC_RATE"]) / 10**6
        ag = valid_on(agree.get(p, []), money, "AG_VLDFR", "AG_VLDTO")
        rate = D(ag["AG_RATE"]) / 10**6 if ag else rate  # the individual agreement replaces the tariff
        share = max((a for a in alloc[p] if a["AL_FNDID"] == r["BK_FNDID"] and a["AL_VLDFR"] <= money <= a["AL_VLDTO"]),
                    key=lambda a: a["AL_VRSNR"])["AL_PCTG"]
        exact = D(r["PR_AMTRC"]) / 100 * D(share) / 10**6 * (1 - rate)
        era = "COBOL" if r["BK_TRDDT"] < CONV else "Java"
        for mname, mode in (("truncation", ROUND_DOWN), ("half-up", ROUND_HALF_UP)):
            k = (era, mname)
            score[k] = score.get(k, 0) + (exact.quantize(CENT, rounding=mode) == D(r["amount_pc"]))
        score[(era, "n")] = score.get((era, "n"), 0) + 1
    for era in ("COBOL", "Java"):
        for mname in ("truncation", "half-up"):
            print(f"  PRM amount {era:5s} {mname:12s} {pct(score.get((era, mname), 0), score.get((era, 'n'), 0))}")


def check_units(x, j, sample):
    """Units = amount x rate / price to 6 decimals, rounding of the era. Rate: charges on the trade date,
    premiums (PRM) on the day before the trade date; cross rate via CHF, NOT rounded."""
    tables = {"upper-case rates": fx_table(x, upper=True), "rates as written": fx_table(x, upper=False)}
    pccy = dict(zip(x.t("NRPOLH")["PH_POLNR"], x.t("NRPOLH")["PH_CCY"]))
    fccy = dict(zip(x.t("NRFUND")["FD_FNDID"], x.t("NRFUND")["FD_CCY"]))
    rows = j if sample <= 0 else j.sample(n=min(sample, j.height), seed=2)
    score, missed = {}, {}
    for r in rows.iter_rows(named=True):
        cp, cf = pccy[r["BK_POLNR"]], fccy[r["BK_FNDID"]]
        prm = r["booking_type"] == "PRM"
        units, mode = D(r["units"]), era_rounding(r["BK_TRDDT"])
        sign = -1 if units < 0 else 1
        for label, day in (("trade date", r["BK_TRDDT"]), ("trade date - 1", r["BK_TRDDT"] - dt.timedelta(days=1))):
            for tname, fx in tables.items():
                cross = fx_on(fx, cp, day) / fx_on(fx, cf, day)  # fund currency per policy currency, via CHF
                hit = (sign * D(r["amount_pc"]) * cross / D(r["price"])).quantize(UNIT6, rounding=mode) == units
                key = (prm, cp == cf, label, tname)
                score[key] = score.get(key, 0) + hit
                if not hit and label == ("trade date - 1" if prm else "trade date"):
                    missed.setdefault(tname, set()).add(r["BK_POLNR"])
        score[(prm, cp == cf, "n")] = score.get((prm, cp == cf, "n"), 0) + 1
    for prm in (True, False):
        for same in (True, False):
            n = score.get((prm, same, "n"), 0)
            for label in ("trade date", "trade date - 1"):
                for tname in tables:
                    print(f"  units {'PRM    ' if prm else 'charges'} {'same currency ' if same else 'other currency'} "
                          f"rate {label:15s} {tname:17s}{pct(score.get((prm, same, label, tname), 0), n)}")
    for tname in tables:
        print(f"  policies with at least one wrong unit ({tname}, right date rule): {len(missed.get(tname, ()))}")


def check_surrender(x):
    print("\n== t3 surrender value from the policy value (diagnostic)")
    vers = by_policy(x.t("NRPOLH").sort("PH_VRSNR"), "PH_POLNR")
    scale = dict(zip(x.t("NRPROD")["PD_PRDCD"], x.t("NRPROD")["PD_SRPSCL"]))
    surr = {(s, y): D(r) / 10**6 for s, y, r in x.t("NRSURR").iter_rows()}
    waiv = [(a, b) for a, b in x.t("NRWAIV").select("WV_VLDFR", "WV_VLDTO").iter_rows()]
    listed = set(x.t("NREXCP").filter(pl.col("EX_TARGET").str.starts_with("t3"))["EX_POLNR"])
    by_date, residuals = {}, []
    for r in x.target("t3_surrender_value").iter_rows(named=True):
        pv, sv, day = D(r["policy_value"]), D(r["surrender_value"]), dt.date.fromisoformat(r["valuation_date"])
        if pv == 0:
            continue
        begin = vers[r["policy_id"]][0]["PH_BEGDT"]
        years = day.year - begin.year - ((day.month, day.day) < (begin.month, begin.day))  # completed years
        rate = D(0) if any(a <= day <= b for a, b in waiv) else surr.get((scale[vers[r["policy_id"]][-1]["PH_PRDCD"]], years), D(0))
        pred = max(D(0), (pv * (1 - rate)).quantize(CENT, rounding=era_rounding(day)))
        tot, ok = by_date.get(day, (0, 0))
        by_date[day] = (tot + 1, ok + (pred == sv))
        if pred != sv:
            residuals.append((r["policy_id"], str(day), str(sv - pred)))
    for day, (tot, ok) in sorted(by_date.items()):
        print(f"  {day}  {pct(ok, tot)}")
    tot, ok = sum(t for t, _ in by_date.values()), sum(o for _, o in by_date.values())
    print(f"  total       {pct(ok, tot)}")
    integer = [r for r in residuals if D(r[2]) == D(r[2]).to_integral_value()]
    print(f"  residuals: {len(residuals)}, with a whole delta: {len(integer)}, in NREXCP: {sum(r[0] in listed for r in residuals)}")
    return {r[0] for r in residuals}


# ------------------------------------------------------------------------------------------------- t4

def check_t4(x):
    print("\n== t4 annual statement as the sum of the bookings")
    cents = lambda c: (pl.col(c).cast(pl.Float64) * 100).round(0).cast(pl.Int64)
    cols = ["premiums", "entry_charges", "admin_fees", "management_fees", "risk_charges", "total_charges"]
    t4 = x.target("t4_annual_statement").select(pl.col("policy_id"), pl.col("year").cast(pl.Int32), *[cents(c).alias(c) for c in cols])
    prem = x.t("NRPREM").filter(pl.col("PR_STATE") == "P")
    premiums = prem.group_by(pl.col("PR_POLNR").alias("policy_id"), pl.col("PR_RCVDT").dt.year().alias("year")).agg(
        pl.col("PR_AMTRC").sum().alias("c_premiums"))
    tb = x.target("t3_booking").with_columns(pl.col("booking_id").cast(pl.Int64), cents("amount_pc").alias("amt"))
    j = tb.join(x.t("NRBOOK").select("BK_BOOKID", "BK_EVTNR", "BK_TRDDT"), left_on="booking_id", right_on="BK_BOOKID")
    charges = j.filter(pl.col("booking_type") != "PRM").group_by("policy_id", pl.col("BK_TRDDT").dt.year().alias("year")).agg(
        *[pl.col("amt").filter(pl.col("booking_type") == t).sum().alias(n) for t, n in
          (("ADM", "c_admin_fees"), ("AMC", "c_management_fees"), ("RSK", "c_risk_charges"))])
    # entry charge of each PRM booking = gross premium share of that fund - invested amount, counted in the year
    # of ITS trade date (the funds of one premium can trade in different years)
    alloc = by_policy(x.t("NRALLO"), "AL_POLNR")
    prm = j.filter(pl.col("booking_type") == "PRM").join(x.t("NRBOOK").select("BK_BOOKID", "BK_FNDID", "BK_RCVDT"),
                                                         left_on="booking_id", right_on="BK_BOOKID")
    prm = prm.join(prem.select(pl.col("PR_POLNR").alias("policy_id"), pl.col("PR_EVTNR").alias("BK_EVTNR"), "PR_AMTRC"),
                   on=["policy_id", "BK_EVTNR"])
    sums = {}
    for p, fund, money, trade, amt, net in prm.select("policy_id", "BK_FNDID", "BK_RCVDT", "BK_TRDDT", "PR_AMTRC", "amt").iter_rows():
        share = max((a for a in alloc[p] if a["AL_FNDID"] == fund and a["AL_VLDFR"] <= money <= a["AL_VLDTO"]),
                    key=lambda a: a["AL_VRSNR"])["AL_PCTG"]
        sums[(p, trade.year)] = sums.get((p, trade.year), D(0)) + D(amt) * D(share) / 10**6 - net
    entry = pl.DataFrame([(p, y, int(v.quantize(D(1), rounding=ROUND_HALF_UP))) for (p, y), v in sums.items()],
                         schema={"policy_id": pl.Utf8, "year": pl.Int32, "c_entry_charges": pl.Int64}, orient="row")
    calc = t4.join(premiums, on=["policy_id", "year"], how="left").join(entry, on=["policy_id", "year"], how="left").join(
        charges, on=["policy_id", "year"], how="left").fill_null(0)
    calc = calc.with_columns((pl.col("c_entry_charges") + pl.col("c_admin_fees") + pl.col("c_management_fees")
                              + pl.col("c_risk_charges")).alias("c_total_charges"))
    for c in cols:
        print(f"  {c:16s} {pct(calc.filter(pl.col(c) == pl.col('c_' + c)).height, calc.height)}")
    full = calc.filter(pl.all_horizontal([pl.col(c) == pl.col("c_" + c) for c in cols]))
    print(f"  whole row        {pct(full.height, calc.height)}")
    bad = calc.join(full.select("policy_id", "year"), on=["policy_id", "year"], how="anti")
    listed = set(x.t("NREXCP").filter(pl.col("EX_TARGET").str.starts_with("t4"))["EX_POLNR"])
    print(f"  rows that differ: {bad.height}, policies: {bad['policy_id'].n_unique()}, of which in NREXCP: "
          f"{len(set(bad['policy_id']) & listed)}; columns involved:",
          {c: bad.filter(pl.col(c) != pl.col('c_' + c)).height for c in cols})
    return set(bad["policy_id"])


# ------------------------------------------------------------------------------------------------- t2

def check_t2(x):
    print("\n== t2 projected value")
    years = x.target("t2_projection_year").with_columns(pl.col("policy_year").cast(pl.Int64))
    final = x.target("t2_projected_maturity_value")
    last = years.sort("policy_year").group_by("policy_id").last().join(final, on="policy_id")
    odd = last.filter(pl.col("value") != pl.col("maturity_value"))
    listed = set(x.t("NREXCP").filter(pl.col("EX_TARGET").str.starts_with("t2"))["EX_POLNR"])
    print(f"  final value = last year of the projection: {pct(last.height - odd.height, last.height)}")
    for p, _, v, m in odd.iter_rows():
        print(f"    {p}  last year {v:>12s}  final {m:>12s}  delta {D(m) - D(v):>10}  {'NREXCP' if p in listed else ''}")
    first = x.t("NRPOLH").sort("PH_VRSNR").group_by("PH_POLNR").first()
    illu = [(a, b, D(r) / 10**6) for a, b, r in x.t("NRILLU").select("IL_VLDFR", "IL_VLDTO", "IL_RATE").iter_rows()]
    rate = lambda d: next(r for a, b, r in illu if a <= d <= b)
    y12 = years.filter(pl.col("policy_year") <= 2).pivot(on="policy_year", index="policy_id", values="value")
    sp = first.filter(pl.col("PH_PRDCD") == "FLSP").join(y12, left_on="PH_POLNR", right_on="policy_id")
    rows = [(rate(a), rate(b), D(v2) / D(v1)) for a, b, v1, v2 in sp.select("PH_APPDT", "PH_BEGDT", "1", "2").iter_rows()]
    for ra in sorted({r[0] for r in rows}):
        same = sorted(g for a, b, g in rows if a == ra and b == ra)
        print(f"  single premium, NRILLU rate {ra:.3f}: median growth in year 2 {same[len(same) // 2]:.4f} (n={len(same)})")
    for a, b, g in rows:
        if a != b:
            print(f"    across a change: rate on the application {a:.3f}, at the start {b:.3f} -> growth {g:.4f}")
    return set(odd["policy_id"])


def find_data():
    """The participants/ folder of the challenge: from LIFEWARE_DATA, or upwards from here or from the current folder."""
    if os.environ.get("LIFEWARE_DATA"):
        return pathlib.Path(os.environ["LIFEWARE_DATA"])
    starts = (pathlib.Path(__file__).resolve().parent, pathlib.Path.cwd())
    found = (d / "participants" for start in starts for d in (start, *start.parents) if (d / "participants" / "legacy").is_dir())
    return next(found, None)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data", type=pathlib.Path, default=find_data(),
                        help="participants/ folder of the challenge (with legacy/ and targets/)")
    parser.add_argument("--sample", type=int, default=60000, help="rows sampled for the row-by-row checks of t3 (0 = all)")
    args = parser.parse_args()
    if args.data is None or not (args.data / "legacy").is_dir():
        parser.error("data folder not found: pass --data /path/to/LifewareChallenge/participants")
    started, x = time.time(), Export(args.data)
    check_data_traps(x)
    t0_bad = check_t0(x)
    check_t1(x)
    t2_bad = check_t2(x)
    check_t3_bookings(x, args.sample)
    t3_bad = check_surrender(x)
    t4_bad = check_t4(x)
    print("\n== t5: policies with residuals (candidates for a manual correction)")
    for task, bad in (("t0", t0_bad), ("t2", t2_bad), ("t3", t3_bad), ("t4", t4_bad)):
        listed = set(x.t("NREXCP").filter(pl.col("EX_TARGET").str.starts_with(task))["EX_POLNR"])
        train_listed = listed & set(x.target("t2_projected_maturity_value")["policy_id"])
        print(f"  {task}: policies with residuals {len(bad):3d} | NREXCP (train) {len(train_listed):3d} | "
              f"NREXCP covered by the residuals {len(train_listed & bad):3d}")
    print(f"\ndone in {time.time() - started:.0f}s")


if __name__ == "__main__":
    main()
