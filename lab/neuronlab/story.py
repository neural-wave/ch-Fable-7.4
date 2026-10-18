"""`lab viz story`: the journey of 100 francs, on a real policy picked by the rules themselves.

S1 `build()` picks the policy automatically and writes `runs/story.json` with every number the story tells. The
policy must cross the system change of 2007-08-11, pay monthly by direct debit, have a premium in t1 that a public
holiday moves to the next bank working day, and be exact everywhere: every row of t0 to t4 in the diffs of
`lab score`, and every booking and diagnostic value of its timeline (`trace`). Among those the simplest one wins: CHF,
no customer orders, fewest funds, funds priced in CHF, a life cover that adds a sum insured to the value (so the risk
charge of chapter 5 is never 0), the lowest policy number.

S2 `view()` turns story.json into the story view of the atlas, in English with an Italian toggle; the words are in
`story_text`. Figures are plain HTML or token-colored Plotly, so they follow the light and dark theme.
"""
import datetime as dt
import html
import importlib
import json
import re
from decimal import Decimal

import polars as pl

from . import paths, store, trace, viz
from . import story_text as T

SYSTEM_CHANGE = dt.date(2007, 8, 11)
LAST_YEAR = 2025  # the last calendar year that is complete in the extract (t4)
VALUATION = dt.date(2025, 12, 31)
TASKS = trace.TASKS
EXAMPLE_TASK = "t0_commission"
NBSP = " "  # a date or an amount never breaks across two lines
COVER_ORDER = {"C": 0, "B": 1, "A": 2}  # RK_TARKEY[6]: value + sum insured always costs a risk charge, so C is told best


# ---------------------------------------------------------------- S1: the policy and its numbers

def exact_policies():
    """The policies whose every row is exact in the newest diffs of every scored task."""
    exact = None
    for task in TASKS:
        diffs = viz.load_diffs(task)
        if diffs is None:
            raise ValueError(f"{task} is not scored yet: lab score {task} (or lab ablate {task})")
        ok = pl.all_horizontal([(pl.col(f"diff:{v}") == 0).fill_null(False) for v in viz.value_columns(diffs)])
        per_policy = diffs.group_by("policy_id").agg(ok.all().alias("ok"))
        found = set(per_policy.filter("ok")["policy_id"]) - set(per_policy.filter(~pl.col("ok"))["policy_id"])
        exact = found if exact is None else exact & found
    return exact


def holiday_shifts():
    """t1 rows of direct debits that a holiday on a weekday moves: (policy_id, due date, collection date)."""
    t1 = store.target("t1_next_due_dates")
    return t1.filter((pl.col("collection_date") > pl.col("due_date")) & (pl.col("due_date").dt.weekday() <= 5))


def candidates():
    """The policies of the story in the order of preference (see the module docstring)."""
    offers = store.load("NRPOLH").sort("PH_VRSNR").group_by("PH_POLNR", maintain_order=True).first()
    shifted = holiday_shifts()
    offers = offers.filter((pl.col("PH_FREQ") == "M") & (pl.col("PH_PAYMT") == "LS")
                           & (pl.col("PH_BEGDT") < SYSTEM_CHANGE)
                           & pl.col("PH_POLNR").is_in(shifted["policy_id"].unique().to_list())
                           & pl.col("PH_POLNR").is_in(store.target("t3_booking")["policy_id"].unique().to_list())
                           & pl.col("PH_POLNR").is_in(sorted(exact_policies())))
    funds = store.load("NRALLO").join(store.load("NRFUND"), left_on="AL_FNDID", right_on="FD_FNDID").group_by(
        "AL_POLNR").agg(pl.col("AL_FNDID").n_unique().alias("funds"), (pl.col("FD_CCY") != "CHF").sum().alias("foreign"))
    orders = store.load("NREVNT").filter(pl.col("EV_EVTTP").is_in([200, 400, 410, 500]))["EV_POLNR"].unique().to_list()
    risks = store.load("NRRISK").select("RK_POLNR", pl.col("RK_TARKEY").str.slice(6, 1).alias("cover"), "RK_SUMIN")
    ranked = (offers.join(funds, left_on="PH_POLNR", right_on="AL_POLNR").join(risks, left_on="PH_POLNR", right_on="RK_POLNR")
              .with_columns(pl.col("PH_POLNR").is_in(orders).alias("orders"),
                            pl.col("cover").replace_strict(COVER_ORDER, default=len(COVER_ORDER)).alias("cover_order"))
              .sort([pl.col("PH_CCY") != "CHF", "orders", "funds", "foreign", "cover_order", "PH_POLNR"]))
    return ranked["PH_POLNR"].to_list()


def pick(accounting, limit=60):
    """The first candidate with a risk charge in the month of chapter 5 whose timeline matches the files everywhere."""
    for policy_id in candidates()[:limit]:
        if not last_charge_run(accounting.replay(policy_id, []))[1]["RSK"]:
            continue
        found = trace.timeline(policy_id, accounting)
        if found["first_divergence"] is None and found["bookings"] and set(found["bookings"]) == {"same"}:
            return policy_id, found
    raise ValueError("no policy of the story matches the files everywhere")


def holiday_name(day_):
    """The key of a bank holiday of Ticino in story_text.HOLIDAYS, or None."""
    easter = importlib.import_module("policies.bank_calendar").easter(day_.year)  # of the loaded submission
    if (day_.month, day_.day) in T.HOLIDAYS:
        return [day_.month, day_.day]
    offset = (day_ - easter).days
    return offset if offset in T.HOLIDAYS else None


def row_of(task, policy_id, **keys):
    diffs = viz.load_diffs(task).filter(pl.col("policy_id") == policy_id)
    for name, value in keys.items():
        diffs = diffs.filter(pl.col(name) == value)
    return diffs.row(0, named=True) if diffs.height else None


def money_premium(accounting, policy, policy_id):
    """The last paid premium of the last complete year, with its bookings: the 100 francs of the story."""
    premiums = [p for p in accounting.premiums[policy_id] if p["PR_STATE"] == "P" and p["PR_RCVDT"] <= VALUATION]
    premium = max(premiums, key=lambda p: p["PR_RCVDT"])
    bought = [b for b in policy.log if b["type"] == "PRM" and b["event"] == premium["PR_EVTNR"]]
    net = sum(b["amount"] for b in bought)
    largest = max(bought, key=lambda b: b["amount"])
    scale = Decimal(100) / premium["PR_AMTRC"]
    commission = row_of(EXAMPLE_TASK, policy_id, due_nr=premium["PR_DUENR"])
    agreed = [a for a in accounting.agreements.get(policy_id, []) if a["AG_FEETP"] == "ENT"
              and a["AG_VLDFR"] <= premium["PR_RCVDT"] <= a["AG_VLDTO"]]
    return {
        "due": str(premium["PR_DUEDT"]), "received": str(premium["PR_RCVDT"]),
        "delay": (premium["PR_RCVDT"] - premium["PR_DUEDT"]).days, "traded": str(largest["day"]),
        "amount": str(premium["PR_AMTRC"]), "entry": str(((premium["PR_AMTRC"] - net) * scale).quantize(Decimal("0.01"))),
        "entry_agreed": bool(agreed), "net": str((net * scale).quantize(Decimal("0.01"))),
        "commission": str((Decimal(commission["computed:amount"]) * scale).quantize(Decimal("0.01"))),
        "funds": len(bought), "share": str((largest["amount"] * scale).quantize(Decimal("0.01"))),
        "split": [str((b["amount"] * scale).quantize(Decimal("0.01")))
                  for b in sorted(bought, key=lambda b: b["amount"], reverse=True)],
        "units": str((largest["units"] * scale).quantize(Decimal("0.0001"))),
        "price": str((largest["amount"] / largest["units"]).quantize(Decimal("0.01"))),
    }


def totals(accounting, policy_id, policy):
    """What happened to the money up to VALUATION: premiums due and paid, all charges, and what the prices did."""
    due = [p for p in accounting.premiums[policy_id] if p["PR_DUEDT"] <= VALUATION]
    paid = [p for p in due if p["PR_STATE"] == "P" and p["PR_RCVDT"] <= VALUATION]
    log = [b for b in policy.log if b["day"] <= VALUATION]
    charges = {kind: -sum((b["amount"] for b in log if b["type"] == kind), Decimal(0)) for kind in ("ADM", "AMC", "RSK")}
    invested = sum((b["amount"] for b in log if b["type"] == "PRM"), Decimal(0))
    entry = sum((p["PR_AMTRC"] for p in paid), Decimal(0)) - invested
    value = trace.worth(policy.account, policy.snapshots[VALUATION], VALUATION)
    risk_years = {}
    for b in log:
        if b["type"] == "RSK":
            risk_years[b["day"].year] = risk_years.get(b["day"].year, Decimal(0)) - b["amount"]
    first_year = min(y for y in risk_years if y > accounting.offer(policy_id)["PH_BEGDT"].year)
    odd = sum(p["PR_AMTRC"] != p["PR_AMTDU"] for p in paid)
    return {"due": len(due), "paid": len(paid), "odd": odd, "entry": str(entry), "admin": str(charges["ADM"]),
            "management": str(charges["AMC"]), "risk": str(charges["RSK"]), "charges": str(entry + sum(charges.values())),
            "market": str(value - (invested - sum(charges.values()))), "risk_first_year": first_year,
            "risk_first": str(risk_years[first_year]), "risk_last": str(risk_years[LAST_YEAR])}


def last_charge_run(policy):
    """(day, {ADM, AMC, RSK: amount}) of the last charge run of the last complete year of a traced replay."""
    runs = [b for b in policy.log if b["type"] in {"ADM", "AMC", "RSK"} and b["day"] <= VALUATION]
    day_ = max(b["day"] for b in runs)
    return day_, {kind: -sum((b["amount"] for b in runs if b["day"] == day_ and b["type"] == kind), Decimal(0))
                  for kind in ("ADM", "AMC", "RSK")}


def charges_of_month(policy, values, months):
    """The three charges of the last charge run of the last complete year, and the yearly rate they make."""
    day_, amounts = last_charge_run(policy)
    value = values[months.index(str(day_.replace(day=1) - dt.timedelta(days=1)))]  # value at the end of the month before
    return {"month": str(day_), "admin": str(amounts["ADM"]), "management": str(amounts["AMC"]), "risk": str(amounts["RSK"]),
            "management_rate": f"{float(amounts['AMC']) * 12 / value:.4f}" if value else "0"}


def paid_in(accounting, policy_id, months):
    """The premiums paid up to the end of each month."""
    received = sorted((p["PR_RCVDT"], p["PR_AMTRC"]) for p in accounting.premiums[policy_id] if p["PR_STATE"] == "P")
    out, total, i = [], Decimal(0), 0
    for month in months:
        while i < len(received) and str(received[i][0]) <= month:
            total += received[i][1]
            i += 1
        out.append(float(total))
    return out


def rules_found():
    """Exact rows over all tasks, the policies, and the rule cards the story tells about."""
    rows = exact = 0
    policies = set()
    for task in TASKS:
        diffs = viz.load_diffs(task)
        rows, exact = rows + diffs.height, exact + viz.exact_rows(diffs)
        policies |= set(diffs["policy_id"])
    examples = []
    for (task, card), _ in T.RULE_EXAMPLES.items():
        found = viz.load_ablation(task)
        entry = next((c for c in found[0]["cards"] if c["id"] == card), None) if found else None
        if entry and entry["broken"]:
            examples.append({"task": task, "card": card, "broken": entry["broken"], "of": found[0]["rows"]})
    return {"rows": rows, "exact": exact, "policies": len(policies), "examples": examples}


def corrections():
    """The wrong rows of all tasks, and one commission that differs by whole francs."""
    wrong, example = 0, None
    for task in TASKS:
        diffs = viz.load_diffs(task)
        wrong += diffs.height - viz.exact_rows(diffs)
        if task == EXAMPLE_TASK:
            whole = diffs.filter((pl.col("diff:amount") != 0) & (pl.col("diff:amount") % 1 == 0)).sort(
                pl.col("diff:amount").abs(), "policy_id", "due_nr")
            if whole.height:
                r = whole.row(0, named=True)
                example = {"policy": r["policy_id"], "due_nr": r["due_nr"], "neuron": r["target:amount"],
                           "rules": r["computed:amount"], "gap": f"{abs(r['diff:amount']):.2f}"}
    return {"wrong": wrong, "example": example}


def build():
    """S1: pick the policy, write runs/story.json (and its timeline in runs/policies/); return the path."""
    accounting = trace.tracer()(str(paths.LEGACY))
    policy_id, timeline = pick(accounting)
    (paths.RUNS / "policies").mkdir(exist_ok=True)
    (paths.RUNS / "policies" / f"{policy_id}.json").write_text(json.dumps(timeline, indent=1), encoding="utf-8")
    offer = accounting.offer(policy_id)
    risk = accounting.risks[policy_id]
    insured = accounting.insured(policy_id)
    neuron = importlib.import_module("neuron")
    policy = accounting.replay(policy_id, [VALUATION])
    in_year = [p for p in accounting.premiums[policy_id] if p["PR_DUEDT"].year == LAST_YEAR]
    shift = holiday_shifts().filter(pl.col("policy_id") == policy_id).row(0, named=True)
    months, values = timeline["months"], timeline["computed"]["value"]
    statement = row_of("t4_annual_statement", policy_id, year=LAST_YEAR)
    surrender = store.target("t3_surrender_value").filter(
        (pl.col("policy_id") == policy_id) & (pl.col("valuation_date") == VALUATION)).row(0, named=True)
    projected = [p for p in timeline["projection"] if p["date"] <= str(VALUATION)]
    end_month = months.index(str(VALUATION))
    rates = store.load("NRILLU").filter((pl.col("IL_VLDFR") <= offer["PH_APPDT"]) & (pl.col("IL_VLDTO") >= offer["PH_APPDT"]))
    story = {
        "policy": {"id": policy_id, "applied": str(offer["PH_APPDT"]), "begin": str(offer["PH_BEGDT"]),
                   "end": str(offer["PH_ENDDT"]), "years": neuron.months_between(offer["PH_BEGDT"], offer["PH_ENDDT"]) // 12,
                   "age": neuron.age(insured.birth, offer["PH_BEGDT"]), "premium": str(offer["PH_PREMI"]),
                   "currency": offer["PH_CCY"], "cover": risk["RK_TARKEY"][6], "sum_insured": str(risk["RK_SUMIN"]),
                   "growth": str(rates["IL_RATE"][0]), "maturity": row_of("t2_projected_maturity_value", policy_id)[
                       "target:maturity_value"], "start_year": offer["PH_BEGDT"].year, "last_year": LAST_YEAR,
                   "age_now": neuron.age(insured.birth, VALUATION)},
        "totals": totals(accounting, policy_id, policy),
        "due": {"due": str(shift["due_date"]), "collected": str(shift["collection_date"]),
                "holiday": holiday_name(shift["due_date"]), "day": shift["due_date"].day},
        "hundred": money_premium(accounting, policy, policy_id),
        "charges": charges_of_month(policy, values, months),
        "value": {"months": months[:end_month + 1], "value": values[:end_month + 1],
                  "paid": paid_in(accounting, policy_id, months[:end_month + 1]),
                  "projected": projected[-1]["target"] if projected else None},
        "change": {"date": str(SYSTEM_CHANGE),
                   "old_months": sum(1 for p in accounting.premiums[policy_id]
                                     if p["PR_STATE"] == "P" and p["PR_RCVDT"] < SYSTEM_CHANGE),
                   "first_year": store.load("NRPOLH")["PH_BEGDT"].min().year},
        "statement": {"year": LAST_YEAR, "due": len(in_year), "paid": sum(p["PR_STATE"] == "P" for p in in_year),
                      **{k: statement[f"target:{k}"] for k in ("premiums", "entry_charges", "admin_fees",
                                                               "management_fees", "risk_charges", "total_charges")}},
        "surrender": {"date": str(VALUATION), "value": str(surrender["policy_value"]),
                      "surrender": str(surrender["surrender_value"])},
        "rules": rules_found(),
        "corrections": corrections(),
    }
    path = paths.RUNS / "story.json"
    path.write_text(json.dumps(story, indent=1, default=str), encoding="utf-8")
    return path


# ---------------------------------------------------------------- S2: the story view

def number(value, decimals, lang):
    """1,234.50 in English, 1'234.50 in Italian (the Swiss way of writing francs)."""
    text = f"{float(value):,.{decimals}f}"
    return text.replace(",", "'") if lang == "it" else text


def money(value, lang, currency="CHF"):
    return f"{currency}{NBSP}{number(value, 2, lang)}"


def date(text, lang):
    """26 March 2007; in Italian the first of the month is 1° (1° agosto 1998)."""
    day_ = dt.date.fromisoformat(str(text)[:10])
    first = "1°" if lang == "it" and day_.day == 1 else str(day_.day)
    return f"{first}{NBSP}{T.MONTHS[lang][day_.month - 1]}{NBSP}{day_.year}"


ELIDED = {"il": "l'", "dal": "dall'", "al": "all'", "del": "dell'"}
VOWEL_NUMBER = r"(11|8\d?|1)(?![\d°])"  # undici, otto, ottanta..., uno (not 1°, read "primo")


def italian(text):
    """The Italian elisions before a number or a month read with a vowel: il 8 -> l'8, Il 11 -> L'11,
    del 1% -> dell'1%, a agosto -> ad agosto."""
    def elide(match):
        word = ELIDED[match.group(1).lower()]
        return (word.capitalize() if match.group(1)[0].isupper() else word) + match.group(2)
    text = re.sub(r"\b([Ii]l|[Dd]al|[Aa]l|[Dd]el) " + VOWEL_NUMBER, elide, text)
    return re.sub(r"\b([Aa]) (aprile|agosto|ottobre)\b", r"\1d \2", text)


def month(text, lang):
    day_ = dt.date.fromisoformat(str(text)[:10])
    return f"{T.MONTHS[lang][day_.month - 1]} {day_.year}"


def percent(value, lang):
    return f"{number(float(value) * 100, 1, lang).rstrip('0').rstrip('.')}%"


def values(story, lang):
    """Every placeholder of the chapters, formatted for `lang`."""
    p, h, c, d = story["policy"], story["hundred"], story["charges"], story["due"]
    cur = p["currency"]
    s, st, r, k = story["surrender"], story["statement"], story["rules"], story["corrections"]
    holiday = d["holiday"]
    name = T.HOLIDAYS[tuple(holiday) if isinstance(holiday, list) else holiday][lang] if holiday is not None else None
    penalty = Decimal(s["value"]) - Decimal(s["surrender"])
    surrender_text = T.SURRENDER["penalty" if penalty else "none"][lang].format(
        penalty=money(penalty, lang, cur), surrender=money(s["surrender"], lang, cur))
    bought = (T.BOUGHT if h["funds"] == 1 else T.BOUGHT_SPLIT)[lang].format(
        net=money(h["net"], lang, cur), share=money(h["share"], lang, cur), units=number(h["units"], 4, lang),
        price=money(h["price"], lang, cur), split=T.SPLIT_AND[lang].join(money(x, lang, cur) for x in h["split"]),
        shares=T.SPLIT_AND[lang].join(percent(Decimal(x) / Decimal(h["net"]), lang) for x in h["split"]))
    examples = "".join(f"<li>{T.RULE_EXAMPLES[(e['task'], e['card'])][lang].format(n=number(e['broken'], 0, lang), of=number(e['of'], 0, lang))}</li>"
                       for e in r["examples"])
    example = k["example"] or {}
    t = story["totals"]
    market = Decimal(t["market"])
    why = T.WHY["loss" if market < 0 else "gain"][lang].format(
        charges=money(t["charges"], lang, cur), market=money(abs(market), lang, cur),
        projected=money(story["value"]["projected"], lang, cur) if story["value"]["projected"] else "–")
    rate = Decimal(h["entry"]) / 100  # the entry charge of 100 francs
    expected = (Decimal(st["premiums"]) * rate).quantize(Decimal("0.01"))
    gap = Decimal(st["entry_charges"]) - expected
    entry_cents = (T.ENTRY_CENTS[lang].format(rate=percent(rate, lang), premiums=money(st["premiums"], lang, cur),
                                              gap=money(abs(gap), lang, cur), direction=T.DIRECTION[lang][gap > 0])
                   if gap else "")
    days = T.DAYS[lang][0] if h["delay"] == 1 else T.DAYS[lang][1].format(n=h["delay"])
    return {
        "applied": date(p["applied"], lang), "age": p["age"], "premium": money(p["premium"], lang, cur),
        "begin": date(p["begin"], lang), "end": date(p["end"], lang), "years": p["years"],
        "start_year": p["start_year"], "age_now": p["age_now"],
        "agreed": T.AGREED[lang] if h["entry_agreed"] else "", "premium_due": date(h["due"], lang), "delay": days,
        "paid_count": number(t["paid"], 0, lang), "due_count": number(t["due"], 0, lang),
        "unpaid_count": number(t["due"] - t["paid"], 0, lang),
        "odd_amounts": T.ODD_AMOUNTS[lang].format(n=t["odd"], premium=money(p["premium"], lang, cur)) if t["odd"] else "",
        "why": why, "risk_first_year": t["risk_first_year"], "risk_first": money(t["risk_first"], lang, cur),
        "risk_last": money(t["risk_last"], lang, cur), "year_paid": st["paid"], "year_due": st["due"],
        "entry_cents": entry_cents,
        "cover": T.COVER[p["cover"]][lang].format(sum_insured=money(p["sum_insured"], lang, cur)),
        "maturity": money(p["maturity"], lang, cur), "growth": percent(p["growth"], lang),
        "day": T.ORDINAL[lang](d["day"]), "due": date(d["due"], lang), "collected": date(d["collected"], lang),
        "holiday": T.A_HOLIDAY[lang].format(name=name) if name else "",
        "entry": money(h["entry"], lang, cur), "net": money(h["net"], lang, cur),
        "commission": money(h["commission"], lang, cur),
        "funds": T.FUNDS[lang][0] if h["funds"] == 1 else T.FUNDS[lang][1].format(n=h["funds"]),
        "received": date(h["received"], lang), "traded": date(h["traded"], lang), "bought": bought,
        "last_year": story["statement"]["year"], "paid": money(story["value"]["paid"][-1], lang, cur),
        "value": money(story["value"]["value"][-1], lang, cur),
        "projected": money(story["value"]["projected"], lang, cur) if story["value"]["projected"] else "–",
        "month": month(c["month"], lang), "admin": money(c["admin"], lang, cur),
        "management": money(c["management"], lang, cur), "risk": money(c["risk"], lang, cur),
        "management_rate": percent(c["management_rate"], lang),
        "change": date(story["change"]["date"], lang), "old_months": story["change"]["old_months"],
        "first_year": story["change"]["first_year"],
        "year": st["year"], "premiums": money(st["premiums"], lang, cur), "total": money(st["total_charges"], lang, cur),
        "surrender_date": date(s["date"], lang), "surrender_worth": money(s["value"], lang, cur),
        "surrender_text": surrender_text,
        "policies": number(r["policies"], 0, lang), "rows": number(r["rows"], 0, lang),
        "exact": number(r["exact"], 0, lang), "examples": examples, "wrong": number(k["wrong"], 0, lang),
        "example_policy": example.get("policy", "–"), "example_neuron": money(example.get("neuron", 0), lang, cur),
        "example_rules": money(example.get("rules", 0), lang, cur), "example_gap": money(example.get("gap", 0), lang, cur),
        "statement_entry": money(st["entry_charges"], lang, cur), "statement_admin": money(st["admin_fees"], lang, cur),
        "statement_management": money(st["management_fees"], lang, cur), "statement_risk": money(st["risk_charges"], lang, cur),
    }


def chapter_text(chapter, story, lang, formatted):
    text = chapter["body"][lang]
    if chapter["id"] == "letter":  # the statement uses its own charges, not those of one month
        formatted = dict(formatted, entry=formatted["statement_entry"], admin=formatted["statement_admin"],
                         management=formatted["statement_management"], risk=formatted["statement_risk"])
    text = text.format(**formatted)
    return italian(text) if lang == "it" else text


def hundred_figure(story, lang):
    entry = float(story["hundred"]["entry"])
    label = T.FIGURES
    return (f'<figure class="hundred" aria-label="100 = {entry:.2f} + {100 - entry:.2f}">'
            f'<div class="hundred-bar"><span class="hundred-entry" style="flex: {entry}"></span>'
            f'<span class="hundred-net" style="flex: {100 - entry}"></span></div>'
            f'<figcaption><span><i class="key key-entry"></i>{label["hundred_entry"][lang]} '
            f'{number(entry, 2, lang)}</span><span><i class="key key-net"></i>{label["hundred_net"][lang]} '
            f'{number(100 - entry, 2, lang)}</span></figcaption></figure>')


def week_figure(story, lang):
    """The days from the Monday of the due date to the day the money is taken."""
    due, taken = (dt.date.fromisoformat(story["due"][k]) for k in ("due", "collected"))
    first = due - dt.timedelta(days=due.weekday())
    last = taken + dt.timedelta(days=6 - taken.weekday())
    cells = []
    for i in range((last - first).days + 1):
        day_ = first + dt.timedelta(days=i)
        closed = day_.weekday() >= 5 or day_ == due  # the due date of the story is a holiday
        tag = (T.FIGURES["week_due"][lang] if day_ == due else T.FIGURES["week_paid"][lang] if day_ == taken
               else T.FIGURES["week_off"][lang] if closed else "")
        kind = " ".join(k for k, on in (("closed", closed), ("due", day_ == due), ("taken", day_ == taken)) if on)
        cells.append(f'<div class="day {kind}"><span class="dow">{T.FIGURES["weekdays"][lang][day_.weekday()]}</span>'
                     f'<span class="dom">{day_.day}</span><span class="tag">{tag}</span></div>')
    names = sorted({(d.year, d.month) for d in (first, last)})
    months = " – ".join(f"{T.MONTHS[lang][m - 1]} {y}" for y, m in names)
    return (f'<figure class="week-figure"><div class="week" aria-label="{date(due, lang)} → {date(taken, lang)}">'
            f'{"".join(cells)}</div><figcaption>{T.FIGURES["week_caption"][lang].format(months=months)}</figcaption>'
            "</figure>")


def charges_figure(story, lang):
    c = story["charges"]
    parts = [("admin", c["admin"]), ("management", c["management"]), ("risk", c["risk"])]
    top = max(float(v) for _, v in parts) or 1
    rows = "".join(f'<div class="charge"><span class="charge-name">{T.FIGURES["charges_" + k][lang]}</span>'
                   f'<span class="charge-bar"><i style="width: {100 * float(v) / top:.1f}%"></i></span>'
                   f'<span class="charge-value">{money(v, lang, story["policy"]["currency"])}</span></div>'
                   for k, v in parts)
    return f'<figure class="charges">{rows}</figure>'


def value_chart(story, lang):
    v, cur = story["value"], story["policy"]["currency"]
    fig = dict(data=[
        dict(type="scatter", mode="lines", x=v["months"], y=v["paid"], name=T.FIGURES["paid"][lang],
             line=dict(color="@series-2", width=2), hovertemplate=f"%{{y:,.2f}} {cur}<extra>{T.FIGURES['paid'][lang]}</extra>"),
        dict(type="scatter", mode="lines", x=v["months"], y=v["value"], name=T.FIGURES["value"][lang],
             line=dict(color="@series-1", width=2), hovertemplate=f"%{{y:,.2f}} {cur}<extra>{T.FIGURES['value'][lang]}</extra>"),
    ], layout=viz.layout(height=300, showlegend=True, hovermode="x unified",
                         legend=dict(orientation="h", y=-0.15, x=0, font=dict(color="@ink2")),
                         yaxis=dict(rangemode="tozero", tickformat=",.0f",
                                    title=dict(text=cur, font=dict(color="@muted"))),
                         xaxis=dict(type="date"), separators=".'" if lang == "it" else ".,"))
    return figure(fig, f"story-value-{lang}", T.FIGURES["chart_value"][lang], lang,
                  [(m, number(p, 2, lang), number(x, 2, lang)) for m, p, x in zip(v["months"], v["paid"], v["value"])][-12:],
                  ["", T.FIGURES["paid"][lang], T.FIGURES["value"][lang]])


def letter_chart(story, lang):
    s, cur = story["statement"], story["policy"]["currency"]
    names = [T.FIGURES["letter_paid"][lang], T.FIGURES["letter_entry"][lang], T.FIGURES["charges_admin"][lang],
             T.FIGURES["charges_management"][lang], T.FIGURES["charges_risk"][lang], T.FIGURES["letter_left"][lang]]
    amounts = [float(s["premiums"]), -float(s["entry_charges"]), -float(s["admin_fees"]), -float(s["management_fees"]),
               -float(s["risk_charges"]), float(s["premiums"]) - float(s["total_charges"])]
    fig = dict(data=[dict(type="waterfall", orientation="v", x=names, y=amounts,
                          measure=["absolute", "relative", "relative", "relative", "relative", "total"],
                          text=[number(a, 2, lang) for a in amounts], textposition="outside",
                          textfont=dict(color="@ink2"), cliponaxis=False,
                          connector=dict(line=dict(color="@axis", width=1)),
                          increasing=dict(marker=dict(color="@series-1")), decreasing=dict(marker=dict(color="@series-2")),
                          totals=dict(marker=dict(color="@series-1")),
                          hovertemplate=f"%{{x}}: %{{y:,.2f}} {cur}<extra></extra>")],
               layout=viz.layout(height=320, margin=dict(l=8, r=16, t=24, b=8), separators=".'" if lang == "it" else ".,",
                                 yaxis=dict(rangemode="tozero", tickformat=",.0f",
                                            title=dict(text=cur, font=dict(color="@muted"))),
                                 xaxis=dict(type="category", tickangle=0)))
    title = T.FIGURES["chart_letter"][lang].format(year=s["year"])
    return figure(fig, f"story-letter-{lang}", title, lang, [(n, number(a, 2, lang)) for n, a in zip(names, amounts)],
                  ["", cur])


def figure(fig, name, caption, lang, rows, head):
    table = ("<table><thead><tr>" + "".join(f"<th>{html.escape(h)}</th>" for h in head) + "</tr></thead><tbody>"
             + "".join("<tr>" + "".join(f"<td>{html.escape(str(c))}</td>" for c in r) + "</tr>" for r in rows)
             + "</tbody></table>")
    return (f'<figure class="story-chart"><figcaption>{html.escape(caption)}</figcaption>{viz.chart(fig, name)}'
            f'<details class="data"><summary>{T.FIGURES["data"][lang]}</summary><div class="scroll">{table}</div>'
            "</details></figure>")


FIGURE_OF = {"hundred": hundred_figure, "due": week_figure, "charges": charges_figure, "units": value_chart,
             "letter": letter_chart}


def language(story, lang):
    formatted = values(story, lang)
    chapters = []
    for i, chapter in enumerate(T.CHAPTERS, start=1):
        figure_html = FIGURE_OF[chapter["id"]](story, lang) if chapter["id"] in FIGURE_OF else ""
        chapters.append(f'<section class="chapter" id="story-{chapter["id"]}-{lang}"><p class="chapter-number">'
                        f'{T.FIGURES["chapter"][lang]} {i}</p><h2>{chapter["title"][lang]}</h2>'
                        f'{chapter_text(chapter, story, lang, formatted)}{figure_html}</section>')
    glossary = "".join(f"<dt>{term[lang]}</dt><dd>{text[lang]}</dd>" for term, text in T.GLOSSARY)
    return (f'<div class="story-lang" lang="{lang}"><header class="story-head"><h1>{T.TITLE[lang]}</h1>'
            f'<p class="story-sub">{T.SUBTITLE[lang].format(**formatted)}</p><p class="story-neuron">{T.NEURON[lang]}</p>'
            f'</header>{"".join(chapters)}<section class="chapter glossary"><h2>{T.FIGURES["glossary"][lang]}</h2>'
            f"<dl>{glossary}</dl></section></div>")


def view():
    """The story view of the atlas from runs/story.json, or "" before `lab viz story`."""
    path = paths.RUNS / "story.json"
    if not path.exists():
        return ""
    story = json.loads(path.read_text(encoding="utf-8"))
    switch = "".join(f'<button type="button" class="lang-switch" data-to="{"it" if lang == "en" else "en"}" lang="{lang}" '
                     f'aria-label="{T.SWITCH_LABEL[lang]}">{T.SWITCH[lang]}</button>' for lang in T.LANGUAGES)
    return (f'<article class="story" data-lang="en"><div class="story-bar">{switch}</div>'
            + "".join(language(story, lang) for lang in T.LANGUAGES) + "</article>")


def text_of(story):
    """The visible words of the story in both languages, without the tags: for the checks of the glossary."""
    def words(page):
        page = re.sub(r"<script.*?</script>", " ", page, flags=re.S)  # the chart data is not read
        return re.sub(r"<[^>]+>", " ", page)
    return {lang: words(language(story, lang).split('<section class="chapter glossary">')[0]) for lang in T.LANGUAGES}


CSS = """
.story { max-width: 680px; margin: 0 auto; font-size: 18px; line-height: 1.65; }
.story-bar { display: flex; justify-content: flex-end; margin: 16px 0 0; }
.story [lang="it"] { display: none; }
.story[data-lang="it"] [lang="en"] { display: none; }
.story[data-lang="it"] [lang="it"] { display: revert; }
.story[data-lang="it"] .story-lang[lang="it"] { display: block; }
.story-head h1 { font-size: 34px; line-height: 1.15; margin: 24px 0 12px; }
.story-sub { color: var(--ink2); font-size: 19px; }
.story-neuron { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 12px 16px; }
.chapter { margin: 48px 0; }
.chapter h2 { font-size: 26px; margin: 0 0 12px; }
.chapter-number { color: var(--muted); font-size: 14px; text-transform: uppercase; letter-spacing: 0.06em; margin: 0; }
.chapter li { margin: 6px 0; }
.story figure { margin: 20px 0; }
.hundred-bar { display: flex; gap: 2px; height: 28px; }
.hundred-bar span { border-radius: 4px; }
.hundred-entry { background: var(--series-2); } .hundred-net { background: var(--series-1); }
.hundred figcaption, .story-chart figcaption { display: flex; gap: 16px; flex-wrap: wrap; font-size: 15px; color: var(--ink2);
  margin-top: 8px; }
.key { display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 6px; }
.key-entry { background: var(--series-2); } .key-net { background: var(--series-1); }
.week { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: 4px; }
.day { background: var(--surface); border: 1px solid var(--border); border-radius: 6px; padding: 6px 4px; text-align: center;
  display: flex; flex-direction: column; min-height: 76px; }
.day .dow { color: var(--muted); font-size: 12px; } .day .dom { font-size: 20px; font-weight: 600; }
.day .tag { font-size: 11px; color: var(--ink2); line-height: 1.2; overflow-wrap: anywhere; hyphens: auto; }
.day.closed { background: var(--page); color: var(--muted); }
.day.due { border: 2px solid var(--series-2); } .day.taken { border: 2px solid var(--series-1); background: var(--wash); }
.week-figure figcaption { font-size: 14px; color: var(--ink2); margin-top: 8px; }
.charge { display: grid; grid-template-columns: minmax(90px, 30%) 1fr auto; gap: 10px; align-items: center; margin: 6px 0;
  font-size: 15px; }
.charge-bar { height: 14px; } .charge-bar i { display: block; height: 100%; background: var(--series-2); border-radius: 0 4px 4px 0; }
.charge-value { font-variant-numeric: tabular-nums; }
.story-chart figcaption { font-weight: 600; color: var(--ink); }
.glossary dt { font-weight: 650; margin-top: 10px; } .glossary dd { margin: 0; color: var(--ink2); }
@media (max-width: 520px) { .story { font-size: 17px; } .story-head h1 { font-size: 28px; } .day .tag { font-size: 10px; } }
"""

JS = """
document.querySelectorAll(".lang-switch").forEach(b => b.addEventListener("click", () => {
  const story = b.closest(".story");
  story.dataset.lang = b.dataset.to;
  try { localStorage.setItem("story-lang", b.dataset.to); } catch (e) {}
  render(false);
}));
try {
  const asked = new URLSearchParams(location.search).get("lang");  // atlas.html?lang=it#story
  const saved = ["en", "it"].includes(asked) ? asked : localStorage.getItem("story-lang");
  if (saved) document.querySelectorAll(".story").forEach(s => s.dataset.lang = saved);
} catch (e) {}
"""
