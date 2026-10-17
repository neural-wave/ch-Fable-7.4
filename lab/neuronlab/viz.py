"""`lab viz`: the Neuron Rule Atlas, one offline page with three views fed by the lab artifacts only.

1. Rules: the before / after of every rule card of `lab ablate` (`runs/<task>/ablation.json` and `.parquet`):
   how many rows the rule makes right, where they are, what the optimal trees say about them, and the
   contribution of each rule of a task (leave one out).
2. Policy: one policy month by month against the diagnostic files, with the first divergence
   (`runs/policies/<id>.json` of `lab viz policy <id>`, see `trace`).
3. Story: the journey of 100 francs, for a reader who knows nothing about computers or insurance
   (`runs/story.json` of `lab viz story`, see `story`).

The index has the exact rows of every task and every difference that is left. Figures are plain Plotly JSON whose
colors are tokens such as `@series-1` or `@surface`; the page replaces them with the values of the light or the
dark theme, so both themes are designed, not inverted. Plotly.js is embedded once, gzip-compressed (the browser
unpacks it with DecompressionStream), so the page opens offline and the hand-in stays small.
"""
import base64
import gzip
import html
import json
import math

import polars as pl

from . import paths
from .store import scoring

THEMES = {
    "light": {"surface": "#fcfcfb", "page": "#f9f9f7", "ink": "#0b0b0b", "ink2": "#52514e", "muted": "#898781",
              "grid": "#e1e0d9", "axis": "#c3c2b7", "border": "rgba(11,11,11,0.10)", "wash": "rgba(42,120,214,0.10)",
              "series-1": "#2a78d6", "series-2": "#eb6834", "series-3": "#1baf7a", "series-4": "#eda100",
              "neutral": "#c3c2b7", "critical": "#d03b3b", "good": "#006300"},
    "dark": {"surface": "#1a1a19", "page": "#0d0d0d", "ink": "#f0efec", "ink2": "#c3c2b7", "muted": "#898781",
             "grid": "#2c2c2a", "axis": "#383835", "border": "rgba(255,255,255,0.10)", "wash": "rgba(57,135,229,0.16)",
             "series-1": "#3987e5", "series-2": "#d95926", "series-3": "#199e70", "series-4": "#c98500",
             "neutral": "#52514e", "critical": "#d03b3b", "good": "#0ca30c"},
}
FONT = 'system-ui, -apple-system, "Segoe UI", sans-serif'
SMALL = 12  # a card that breaks at most this many rows shows them as a table instead of a chart
BINS = 40
TOP_CATEGORIES = 12


def esc(value):
    return html.escape(str(value))


def axis(**extra):
    return dict(gridcolor="@grid", linecolor="@axis", zerolinecolor="@axis", tickfont=dict(color="@muted"),
                automargin=True, **extra)


def layout(**extra):
    """The common layout: recessive grid and axes, text in ink tokens, hover label on the surface."""
    base = dict(paper_bgcolor="@surface", plot_bgcolor="@surface", font=dict(family=FONT, size=13, color="@ink2"),
                margin=dict(l=8, r=16, t=8, b=8), showlegend=False, xaxis=axis(), yaxis=axis(),
                hoverlabel=dict(bgcolor="@surface", bordercolor="@axis", font=dict(family=FONT, color="@ink")))
    for key, value in extra.items():
        base[key] = dict(base[key], **value) if isinstance(value, dict) and key in base else value
    return base


def panel_title(text, y):
    """The title of one panel of small multiples, top left, in secondary ink."""
    return dict(text=f"<b>{esc(text)}</b>", x=0, xref="paper", y=y, yref="paper", xanchor="left", yanchor="bottom",
                showarrow=False, font=dict(color="@ink2", size=13))


# ---------------------------------------------------------------- artifacts

def diffs_path(task):
    """The newest diffs.parquet of a task: of `lab score <task>` or of the `~on` run of `lab ablate`."""
    found = [f for f in (paths.RUNS / task / "diffs.parquet", paths.RUNS / f"{task}~on" / "diffs.parquet")
             if f.exists()]
    return max(found, key=lambda f: f.stat().st_mtime) if found else None


def load_diffs(task):
    path = diffs_path(task)
    return pl.read_parquet(path) if path else None


def value_columns(diffs):
    return [c.split(":", 1)[1] for c in diffs.columns if c.startswith("diff:")]


def exact_rows(diffs):
    """Rows whose every value equals the target (a difference of exactly 0), as scoring.accuracy counts them."""
    same = pl.all_horizontal([(pl.col(f"diff:{v}") == 0).fill_null(False) for v in value_columns(diffs)])
    return int(diffs.select(same.sum()).item())


def load_ablation(task):
    """(ablation.json, ablation.parquet) of `lab ablate <task>`, or None."""
    folder = paths.RUNS / task
    if not (folder / "ablation.json").exists():
        return None
    return json.loads((folder / "ablation.json").read_text(encoding="utf-8")), pl.read_parquet(folder / "ablation.parquet")


def load_policies():
    """The timelines of `lab viz policy`, the policy of the story first."""
    folder = paths.RUNS / "policies"
    found = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(folder.glob("*.json"))] if folder.exists() else []
    story = paths.RUNS / "story.json"
    featured = json.loads(story.read_text(encoding="utf-8"))["policy"]["id"] if story.exists() else None
    return sorted(found, key=lambda d: (d["policy"] != featured, d["first_divergence"] is None, d["policy"]))


def short(task):
    return task.split("_")[0]


def title(task):
    return task.split("_", 1)[1].replace("_", " ")


# ---------------------------------------------------------------- index

def signed_log(x):
    """Position of a difference on a symmetric log axis in cents: 0.01 -> 1, 1.00 -> 2.0, -100.00 -> -4.0."""
    return math.copysign(math.log10(1 + abs(x) * 100), x)


def difference_strip(tasks):
    """Every wrong value of every task as one dot: where it sits says what kind of mistake it is.

    One cent is a rounding, a whole number of francs is a typed correction, a large amount a missing rule.
    """
    rows, labels = [], []
    for task in tasks:
        diffs = load_diffs(task)
        if diffs is None:
            continue
        keys = [c for c in diffs.columns if ":" not in c]
        for value in value_columns(diffs):
            wrong = diffs.filter(pl.col(f"diff:{value}").fill_null(1) != 0)
            label = f"{short(task)} · {value}"
            labels.append(label)
            for r in wrong.iter_rows(named=True):
                d = r[f"diff:{value}"]
                rows.append(dict(label=label, x=signed_log(d) if d is not None else None,
                                 key=" ".join(str(r[k]) for k in keys), target=r[f"target:{value}"],
                                 computed=r[f"computed:{value}"], diff=d))
    rows = [r for r in rows if r["x"] is not None]
    ticks = [-1000, -10, -1, -0.01, 0, 0.01, 1, 10, 1000]
    trace = dict(type="scatter", mode="markers", x=[r["x"] for r in rows], y=[r["label"] for r in rows],
                 marker=dict(size=9, color="@series-1", opacity=0.8, line=dict(width=2, color="@surface")),
                 customdata=[[r["key"], r["target"], r["computed"], f"{r['diff']:+,.2f}"] for r in rows],
                 hovertemplate="<b>%{customdata[0]}</b><br>target %{customdata[1]}<br>computed %{customdata[2]}"
                               "<br>difference %{customdata[3]}<extra></extra>")
    return dict(data=[trace], layout=layout(
        height=60 + 34 * len(labels),
        xaxis=dict(tickvals=[signed_log(t) for t in ticks], ticktext=[f"{t:+,g}" if t else "0" for t in ticks],
                   tickangle=0,
                   title=dict(text="target − computed (currency units or days, log scale)", font=dict(color="@muted")),
                   zeroline=True),
        yaxis=dict(categoryorder="array", categoryarray=labels[::-1], type="category")))


def tile(label, value, note=""):
    return (f'<div class="tile"><div class="tile-label">{label}</div><div class="tile-value">{value}</div>'
            f'<div class="tile-note">{note}</div></div>')


def tiles(tasks):
    """One tile per scored task: exact rows of the last scoring."""
    out = []
    for task in tasks:
        diffs = load_diffs(task)
        if diffs is None:
            out.append(tile(esc(task), "–", f"not scored yet: lab score {esc(task)}"))
            continue
        ok, total = exact_rows(diffs), diffs.height
        shown = math.floor(10000 * ok / total) / 100  # rounded down: 100.00% only when every row is exact
        out.append(tile(esc(task), f"{shown:.2f}%", f"{ok:,} of {total:,} rows exact"))
    return '<div class="tiles">' + "".join(out) + "</div>"


def rule_index(ablations):
    """Every rule card of every task, with the rows it makes right and a link to its card."""
    rows = "".join(
        f'<tr><td>{esc(short(data["task"]))}</td><td><a href="#rules/{esc(data["task"])}/card-{esc(short(data["task"]))}-'
        f'{esc(card["id"])}">{esc(card["rule"])}</a></td><td class="num">{card["broken"]:,}</td>'
        f'<td class="num">{share(card["broken"], data["rows"])}</td></tr>'
        for data, _ in ablations for card in data["cards"])
    return ('<div class="scroll"><table class="index"><thead><tr><th>task</th><th>rule</th><th class="num">rows it makes '
            f'right</th><th class="num">share of the task</th></tr></thead><tbody>{rows}</tbody></table></div>')


def policy_index(policies):
    rows = "".join(
        f'<tr><td><a href="#policy/{esc(d["policy"])}">{esc(d["policy"])}</a></td><td>{esc(d["begin"])}</td>'
        f'<td>{esc(d["first_divergence"]["date"] + ", " + d["first_divergence"]["source"]) if d["first_divergence"] else "none"}'
        "</td></tr>" for d in policies)
    return ('<div class="scroll"><table class="index"><thead><tr><th>policy</th><th>begin</th><th>first divergence</th>'
            f"</tr></thead><tbody>{rows}</tbody></table></div>")


def index_view(tasks, ablations, policies, story):
    rules = sum(len(data["cards"]) for data, _ in ablations)
    views = [("rules", "Before / after", f"{rules} rules switched off one at a time: how many rows each one makes "
              "right, and where they are."),
             ("policy", "Policy timeline", f"{len(policies)} policies month by month against the diagnostic files, "
              "with a marker on the first value that differs."),
             ("story", "The journey of 100 francs", "What Neuron does with the money of a customer, for a reader who "
              "knows nothing about computers or insurance. English and Italian.")]
    cards = "".join(f'<a class="view-card" href="#{v}"><span class="view-card-title">{t}</span>'
                    f'<span class="view-card-text">{esc(x)}</span></a>' for v, t, x in views if v != "story" or story)
    return (section("Three views", "Every view reads only the artifacts of the lab pipeline, so it works for a new "
                    "target too.", f'<div class="view-cards">{cards}</div>')
            + section("Exact rows", "The share of target rows that the rules reproduce to the cent and to the day, "
                      "from the last <code>lab score</code> of each task.", tiles(tasks))
            + section("What kind of mistakes are left",
                      "Every value that differs from the target is one dot. One cent is a rounding, a whole number of "
                      "francs is a value typed by hand (task t5), a large amount is a rule that is still missing.",
                      chart(difference_strip(tasks), "differences"))
            + (section("Every rule", "Each rule card of <code>lab/rules</code>, switched off on its own: the rows that "
                       "go wrong without it and are right with it.", rule_index(ablations)) if ablations else "")
            + (section("Every policy traced", "The policies of <code>lab viz policy</code> and of the story.",
                       policy_index(policies)) if policies else ""))


# ---------------------------------------------------------------- rules (before / after)

def binned(df, column):
    """The rows with a `bin` column for the where axis: months or years of a date, values or ranges of a number,
    the most frequent categories of anything else; and the kind of axis."""
    values = df[column].drop_nulls()
    if df[column].dtype == pl.Date:
        span = (values.max() - values.min()).days if values.len() else 0
        return df.with_columns(pl.col(column).dt.truncate("1mo" if span <= 3 * 366 else "1y").alias("bin")), "date"
    if df[column].dtype.is_numeric():
        number = pl.col(column).cast(pl.Float64)
        if df[column].dtype.is_integer() and values.n_unique() <= 60:
            return df.with_columns(number.alias("bin")), "number"
        low, high = float(values.cast(pl.Float64).min()), float(values.cast(pl.Float64).max())
        width = (high - low) / BINS or 1
        return df.with_columns(((number - low) / width).floor().clip(0, BINS - 1).mul(width).add(low + width / 2)
                               .alias("bin")), "number"
    top = df[column].cast(pl.String).value_counts(sort=True).head(TOP_CATEGORIES)[column].to_list()
    text = pl.col(column).cast(pl.String)
    return df.with_columns(pl.when(text.is_in(top)).then(text).otherwise(pl.lit("other")).alias("bin")), "category"


def bar_gap(slots, width=1000, widest=24):
    """The gap that keeps bars at most `widest` px thick on a plot about `width` px wide (wider bars read as blocks)."""
    return max(0.15, 1 - widest * slots / width)


def where_figure(card, table):
    """Two panels on the card's where axis: every row of the task, and the rows that go wrong without the rule."""
    column = f"where:{card['id']}"
    work = table.select(column, (pl.col("on") & ~pl.col(f"off:{card['id']}")).alias("broken")).filter(
        pl.col(column).is_not_null())
    work, kind = binned(work, column)
    counts = work.group_by("bin").agg(pl.len().alias("rows"), pl.col("broken").sum().alias("broken")).sort("bin")
    x = [str(v) for v in counts["bin"]] if kind != "number" else counts["bin"].to_list()
    hover = "%{x}<br>%{y:,} rows<extra></extra>"
    bars = dict(type="bar", x=x, marker=dict(cornerradius=4), hovertemplate=hover)
    fig = dict(data=[dict(bars, y=counts["rows"].to_list(), yaxis="y2", marker=dict(color="@neutral", cornerradius=4)),
                     dict(bars, y=counts["broken"].to_list(), yaxis="y", marker=dict(color="@series-2", cornerradius=4))],
               layout=layout(height=330, bargap=bar_gap(len(x)), margin=dict(l=8, r=16, t=28, b=8),
                             xaxis=dict(type="category" if kind == "category" else ("date" if kind == "date" else "linear"),
                                        title=dict(text=esc(card["where_label"]), font=dict(color="@muted"))),
                             yaxis=axis(domain=[0, 0.42], rangemode="tozero"),
                             yaxis2=axis(domain=[0.58, 1], rangemode="tozero"),
                             annotations=[panel_title("every row of the task", 1.0),
                                          panel_title("rows that are wrong without the rule", 0.42)]))
    rows = "".join(f"<tr><td>{esc(b)}</td><td>{r:,}</td><td>{n:,}</td></tr>"
                   for b, r, n in zip(x, counts["rows"], counts["broken"]))
    data = (f'<details class="data"><summary>Table of the chart</summary><table><thead><tr><th>{esc(card["where_label"])}'
            f'</th><th>rows</th><th>wrong without the rule</th></tr></thead><tbody>{rows}</tbody></table></details>')
    return fig, data


def examples_table(card, keys, values):
    """The rows a card breaks, with the target and the value without the rule."""
    head = "".join(f"<th>{esc(k)}</th>" for k in keys) + "<th>value</th><th>target</th><th>without the rule</th>"
    body = "".join("<tr>" + "".join(f"<td>{esc(e[k])}</td>" for k in keys)
                   + "".join(f"<td>{esc(v)}</td><td>{esc(e[v]['target'])}</td><td>{esc(e[v]['off'])}</td>"
                             for v in values if v in e)
                   + "</tr>" for e in card["examples"])
    return f'<div class="scroll"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def share(part, whole):
    """A percentage that never shows a small non-zero part as 0.00%."""
    value = 100 * part / whole if whole else 0
    return "<0.01%" if 0 < value < 0.01 else f"{value:.2f}%"


def card_html(task, card, data, table):
    """One rule card: the rule, how it was switched off, before / after, where, what the trees say, the change."""
    name = f"{short(task)}-{card['id']}"
    rows = data["rows"]
    if card["broken"] == 0:
        body = '<p class="empty">Switching this rule off changes no row of this task.</p>'
    elif card["broken"] <= SMALL or not card.get("where"):
        body = examples_table(card, data["keys"], data["values"])
    else:
        fig, table_view = where_figure(card, table)
        body = chart(fig, name) + table_view
        if card["broken"] > len(card["examples"]):
            body += (f'<details class="data"><summary>The first {len(card["examples"])} of the {card["broken"]:,} rows'
                     f'</summary>{examples_table(card, data["keys"], data["values"])}</details>')
    fixed = (f"; {card['fixed']:,} rows are right only without it" if card["fixed"] else
             "; no row is right only without it")
    by_value = ", ".join(f"{v} {n:,}" for v, n in card["broken_by_value"].items() if n) if len(data["values"]) > 1 else ""
    trees = "\n".join(line for lines in card["trees"].values() for line in lines)
    edits = "\n\n".join(f"{e['file']}\n- {e['old']}\n+ {e['new']}" for e in card["edits"])
    return (
        f'<article class="card" id="card-{esc(name)}"><h3>{esc(card["rule"])}</h3>'
        f'<p class="lead">Switched off: {esc(card["off"])}.</p>'
        '<div class="tiles">'
        + tile("Wrong rows without the rule", f"{card['wrong_off']:,}", f"of {rows:,}")
        + tile("Wrong rows with the rule", f"{card['wrong_on']:,}", "the values no rule reproduces")
        + tile("Rows the rule makes right", f"{card['broken']:,}", f"{share(card['broken'], rows)} of the rows{fixed}")
        + "</div>"
        + (f'<p class="note">Values that go wrong: {esc(by_value)}.</p>' if by_value else "")
        + body
        + (f'<details class="data"><summary>What the optimal trees of lab score say about the wrong rows</summary>'
           f"<pre>{esc(trees)}</pre></details>" if trees else "")
        + f'<details class="data"><summary>The change in a scratch copy of the submission</summary><pre>{esc(edits)}'
          "</pre></details></article>")


def contribution_figure(task, data):
    """Leave one out: the rows each rule makes right, on a log axis, largest first."""
    found = sorted((c for c in data["cards"] if c["broken"]), key=lambda c: c["broken"])
    labels = [c["id"].replace("-", " ") for c in found]
    trace = dict(type="scatter", mode="markers+text", x=[c["broken"] for c in found], y=labels,
                 text=[f"{c['broken']:,}" for c in found], textposition="middle right", textfont=dict(color="@ink2"),
                 marker=dict(size=12, color="@series-1", line=dict(width=2, color="@surface")),
                 customdata=[c["rule"] for c in found], cliponaxis=False,
                 hovertemplate="<b>%{customdata}</b><br>%{x:,} rows<extra></extra>")
    top = max([c["broken"] for c in found] or [1])
    return dict(data=[trace], layout=layout(
        height=70 + 40 * len(found), margin=dict(l=8, r=48, t=8, b=8),
        xaxis=dict(type="log", range=[-0.2, math.log10(top) + 0.6],
                   title=dict(text="rows that go wrong when only this rule is switched off (log scale)",
                              font=dict(color="@muted"))),
        yaxis=dict(type="category", categoryorder="array", categoryarray=labels)))


def rules_panel(task, data, table):
    cards = "".join(card_html(task, c, data, table) for c in data["cards"])
    none = [c["id"].replace("-", " ") for c in data["cards"] if not c["broken"]]
    exact = data["rows"] - data["wrong"]
    head = (f'<h2>{esc(task)}</h2><p class="lead">With every rule on, {exact:,} of {data["rows"]:,} rows are exact. Each '
            "card below switches one rule off in a scratch copy of the submission and scores it again with "
            "<code>lab score --submission</code>; the submission itself never changes.</p>")
    contribution = chart(contribution_figure(task, data), f"{short(task)}-contribution")
    note = f'<p class="note">No row of this task depends on: {esc(", ".join(none))}.</p>' if none else ""
    return (f'<div class="panel" data-panel="{esc(task)}">{head}<h3 class="sub">Contribution of each rule</h3>'
            f"{contribution}{note}{cards}</div>")


def rules_view(tasks):
    loaded = [(task, found) for task in tasks if (found := load_ablation(task))]
    if not loaded:
        return section("Before / after", "No rule cards scored yet: <code>lab ablate &lt;task&gt;</code>.", "")
    tabs = "".join(f'<a class="tab" href="#rules/{esc(t)}" data-tab="{esc(t)}">{esc(short(t))} {esc(title(t))}</a>'
                   for t, _ in loaded)
    panels = "".join(rules_panel(task, data, table) for task, (data, table) in loaded)
    return (f'<h2 class="view-title">Before / after</h2><p class="lead">A rule found in the data is convincing when '
            "switching it off breaks exactly the rows it explains, and nothing else. Every card of "
            "<code>lab/rules/&lt;task&gt;.json</code> is one rule.</p>"
            f'<nav class="tabs" aria-label="Tasks">{tabs}</nav>{panels}')


# ---------------------------------------------------------------- policy timeline

def money(value, currency=""):
    return f"{value:,.2f} {currency}".strip()


def timeline_figure(d):
    """Three panels on one time axis: value, money in and out per month, values that differ from the files."""
    x, cur = d["months"], d["currency"]
    files_x = [v["date"] for v in d["valuations"]] + [p["date"] for p in d["projection"] if p["target"] is not None]
    files_y = [v["policy_value"] for v in d["valuations"]] + [p["target"] for p in d["projection"]
                                                               if p["target"] is not None]
    files_name = ["policy value in t3_surrender_value"] * len(d["valuations"]) + [
        f"projected value of policy year {p['year']} in t2_projection_year" for p in d["projection"]
        if p["target"] is not None]
    line = dict(type="scatter", mode="lines", yaxis="y3")
    traces = [
        dict(line, x=x, y=d["computed"]["value"], name="value of the units (rules)",
             line=dict(color="@series-1", width=2), hovertemplate=f"%{{y:,.2f}} {cur}<extra>value</extra>"),
        dict(line, x=[p["date"] for p in d["projection"]], y=[p["computed"] for p in d["projection"]],
             name="projection of the offer (rules)", line=dict(color="@series-3", width=2),
             hovertemplate=f"%{{y:,.2f}} {cur}<extra>projection</extra>"),
        dict(type="scatter", mode="markers", x=files_x, y=files_y, yaxis="y3", name="value in the files",
             marker=dict(size=8, color="@ink", line=dict(width=2, color="@surface")), customdata=files_name,
             hovertemplate=f"%{{customdata}}: %{{y:,.2f}} {cur}<extra></extra>"),
        dict(type="bar", x=x, y=d["computed"]["premiums"], yaxis="y2", name="premiums invested",
             marker=dict(color="@series-4"), hovertemplate=f"%{{y:,.2f}} {cur}<extra>premiums</extra>"),
        dict(type="bar", x=x, y=d["computed"]["charges"], yaxis="y2", name="charges",
             marker=dict(color="@series-2"), hovertemplate=f"%{{y:,.2f}} {cur}<extra>charges</extra>"),
        dict(type="bar", x=x, y=d["differing_per_month"], yaxis="y", name="values that differ",
             marker=dict(color="@critical"), hovertemplate="%{y} values<extra>differ</extra>"),
    ]
    annotations = [panel_title(f"Value ({cur})", 1.0), panel_title(f"Money in and out per month ({cur})", 0.62),
                   panel_title("Values that differ from the files, per month", 0.24)]
    shapes = []
    first = d["first_divergence"]
    if first:
        shapes.append(dict(type="line", xref="x", yref="paper", x0=first["date"], x1=first["date"], y0=0, y1=1,
                           line=dict(color="@critical", width=1)))
        annotations.append(dict(text=f"first divergence {first['date']}: {esc(first['source'])}", x=first["date"],
                                xref="x", y=0.2, yref="paper", xanchor="right", yanchor="top", showarrow=False,
                                font=dict(color="@ink", size=12), bgcolor="@surface"))
    else:
        annotations.append(dict(text="every booking and every value matches the files", x=0.5, xref="paper",
                                y=0.1, yref="paper", showarrow=False, font=dict(color="@muted", size=12)))
    return dict(data=traces, layout=layout(
        height=620, showlegend=True, hovermode="x unified", barmode="relative", bargap=0.1,
        legend=dict(orientation="h", y=-0.08, x=0, font=dict(color="@ink2")), margin=dict(l=8, r=16, t=24, b=8),
        xaxis=dict(type="date", showspikes=True, spikemode="across", spikethickness=1, spikecolor="@axis",
                   spikedash="solid"),
        yaxis=axis(domain=[0, 0.2], rangemode="tozero"), yaxis2=axis(domain=[0.3, 0.6]),
        yaxis3=axis(domain=[0.68, 1], rangemode="tozero"), annotations=annotations, shapes=shapes))


def differences_table(d):
    if not d["differences"]:
        return ""
    rows = "".join(f"<tr><td>{esc(x['date'])}</td><td>{esc(x['source'])}</td><td>{esc(x['what'])}</td>"
                   f"<td>{esc(x['target'])}</td><td>{esc(x['computed'])}</td></tr>" for x in d["differences"])
    more = (f'<p class="note">The first {len(d["differences"])} of {d["differences_total"]:,} differences.</p>'
            if d["differences_total"] > len(d["differences"]) else "")
    return (f'<h3 class="sub">What differs</h3><div class="scroll"><table><thead><tr><th>date</th><th>file</th>'
            f"<th>value</th><th>in the file</th><th>computed</th></tr></thead><tbody>{rows}</tbody></table></div>{more}")


def policy_panel(d):
    first = d["first_divergence"]
    bookings = d["bookings"] or {}
    same, total = bookings.get("same", 0), sum(bookings.values())
    facts = (f"{d['currency']}, begin {d['begin']}, end {d['end']}, premium frequency {d['frequency']}, payment "
             f"{d['payment']}, product {d['product']}, funds {', '.join(d['funds'])}")
    tiles_html = ('<div class="tiles">'
                  + tile("Bookings as in NRBOOK", f"{same:,}" if total else "–",
                         f"of {total:,}" if total else "no diagnostic bookings for this policy")
                  + tile("Values as in the files", f"{d['checks']['ok']:,}", f"of {d['checks']['total']:,} in "
                         + esc(", ".join(d["checks"]["sources"])))
                  + tile("First divergence", esc(first["date"]) if first else "none",
                         esc(f"{first['source']}: {first['what']}") if first else "the rules reproduce the policy")
                  + "</div>")
    return (f'<div class="panel" data-panel="{esc(d["policy"])}"><h2>{esc(d["policy"])}</h2><p class="lead">{esc(facts)}'
            f"</p>{tiles_html}{chart(timeline_figure(d), 'timeline-' + d['policy'])}{differences_table(d)}</div>")


def policy_view(policies):
    if not policies:
        return section("Policy timeline", "No policy traced yet: <code>lab viz policy &lt;id&gt;</code>.", "")
    tabs = "".join(f'<a class="tab" href="#policy/{esc(d["policy"])}" data-tab="{esc(d["policy"])}">{esc(d["policy"])}'
                   f'<span class="tab-note">{"exact" if not d["first_divergence"] else "differs " + d["first_divergence"]["date"][:7]}'
                   "</span></a>" for d in policies)
    return ('<h2 class="view-title">Policy timeline</h2><p class="lead">One policy month by month, replayed by the '
            "code of the submission through a subclass of its <code>FundAccounting</code> that writes down every "
            "booking. The bookings are compared with NRBOOK and t3_booking, the values with t3_holding, "
            "t3_surrender_value, t2_projection_year and the rows of every task. The red line marks the first value "
            "that differs.</p>"
            f'<nav class="tabs" aria-label="Policies">{tabs}</nav>' + "".join(policy_panel(d) for d in policies))


# ---------------------------------------------------------------- page

def section(heading, lead, body):
    return f'<section class="block"><h2>{esc(heading)}</h2><p class="lead">{lead}</p>{body}</section>'


def chart(fig, name):
    """A chart placeholder; the page script renders it with the current theme when it becomes visible."""
    spec = json.dumps(fig, default=str).replace("</", "<\\/")  # no "</script>" inside the script element
    return (f'<div class="chart" id="chart-{esc(name)}"></div><script type="application/json" '
            f'data-chart="chart-{esc(name)}">{spec}</script>')


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Neuron Rule Atlas</title>
<style>
:root { color-scheme: light; %(light)s }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { color-scheme: dark; %(dark)s } }
:root[data-theme="dark"] { color-scheme: dark; %(dark)s }
* { box-sizing: border-box; }
body { margin: 0; background: var(--page); color: var(--ink); font-family: %(font)s; line-height: 1.5; }
a { color: var(--series-1); }
code { font-size: 0.92em; }
.bar { position: sticky; top: 0; z-index: 5; background: var(--page); border-bottom: 1px solid var(--border); }
.bar-inner { max-width: 1080px; margin: 0 auto; padding: 10px 16px; display: flex; gap: 12px 20px; align-items: center;
             flex-wrap: wrap; }
.brand { font-weight: 650; color: var(--ink); text-decoration: none; margin-right: auto; }
.bar nav { display: flex; gap: 4px; flex-wrap: wrap; }
.bar nav a { color: var(--ink2); text-decoration: none; padding: 4px 10px; border-radius: 6px; }
.bar nav a[aria-current="page"] { color: var(--ink); background: var(--wash); }
main { max-width: 1080px; margin: 0 auto; padding: 8px 16px 64px; }
h1, h2, h3 { line-height: 1.25; } h2 { font-size: 20px; margin: 32px 0 4px; } h3 { font-size: 16px; margin: 0 0 4px; }
.view-title { font-size: 26px; margin-top: 24px; }
h3.sub { margin: 24px 0 8px; }
.lead { color: var(--ink2); margin: 0 0 16px; max-width: 76ch; }
.note, .empty { color: var(--muted); font-size: 14px; margin: 8px 0; }
.chart { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 8px; margin: 8px 0; }
.tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin: 8px 0; }
.tile { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 12px 16px; }
.tile-label { color: var(--ink2); font-size: 13px; } .tile-value { font-size: 26px; font-weight: 600; }
.tile-note { color: var(--muted); font-size: 13px; }
.card { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 16px; margin: 16px 0; }
.card .tile { background: var(--page); }
.view-cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 12px; }
.view-card { display: flex; flex-direction: column; gap: 6px; background: var(--surface); border: 1px solid var(--border);
             border-radius: 10px; padding: 16px; text-decoration: none; color: var(--ink); }
.view-card:hover, .view-card:focus-visible { border-color: var(--series-1); }
.view-card-title { font-weight: 650; } .view-card-text { color: var(--ink2); font-size: 14px; }
.tabs { display: flex; gap: 6px; flex-wrap: wrap; margin: 8px 0 4px; }
.tab { border: 1px solid var(--border); border-radius: 6px; padding: 4px 10px; color: var(--ink2); text-decoration: none;
       background: var(--surface); font-size: 14px; }
.tab[aria-current="true"] { color: var(--ink); border-color: var(--series-1); background: var(--wash); }
.tab-note { color: var(--muted); font-size: 12px; margin-left: 6px; }
.scroll { overflow-x: auto; }
table { border-collapse: collapse; font-size: 13px; margin: 8px 0; font-variant-numeric: tabular-nums; }
th, td { text-align: left; padding: 4px 10px 4px 0; border-bottom: 1px solid var(--border); white-space: nowrap; }
th { color: var(--ink2); font-weight: 600; }
th.num, td.num { text-align: right; padding-left: 16px; }
table.index td { white-space: normal; } table.index { width: 100%%; }
details.data { margin: 8px 0; } details.data summary { cursor: pointer; color: var(--ink2); font-size: 14px; }
pre { white-space: pre-wrap; word-break: break-word; font-size: 12px; color: var(--ink2); background: var(--page);
      border-radius: 6px; padding: 8px; }
button { font: inherit; background: var(--surface); color: var(--ink); border: 1px solid var(--border);
         border-radius: 6px; padding: 4px 12px; cursor: pointer; }
[hidden] { display: none !important; }
%(story_css)s
</style></head><body>
<header class="bar"><div class="bar-inner"><a class="brand" href="#index">Neuron Rule Atlas</a>
<nav aria-label="Views"><a href="#index" data-nav="index">Index</a><a href="#rules" data-nav="rules">Before / after</a>
<a href="#policy" data-nav="policy">Policy timeline</a>%(story_nav)s</nav>
<button id="theme" type="button">Switch theme</button></div></header>
<main>
<div class="view" data-view="index"><h1 class="view-title">How the rules of Neuron were found, and how well they work</h1>
%(index)s</div>
<div class="view" data-view="rules" hidden>%(rules)s</div>
<div class="view" data-view="policy" hidden>%(policy)s</div>
<div class="view" data-view="story" hidden>%(story)s</div>
</main>
<script type="application/octet-stream" id="plotly-gzip">%(plotly)s</script>
<script>
const THEMES = %(themes)s;
async function loadPlotly() {  // plotly.js is embedded gzip-compressed (2.8 MB less); the browser unpacks it offline
  const packed = Uint8Array.from(atob(document.getElementById("plotly-gzip").textContent), c => c.charCodeAt(0));
  const code = await new Response(new Blob([packed]).stream().pipeThrough(new DecompressionStream("gzip"))).text();
  const script = document.createElement("script");
  script.textContent = code;
  document.head.appendChild(script);
}
function current() {
  const set = document.documentElement.dataset.theme;
  return set || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
}
function paint(value, tokens) {
  if (typeof value === "string" && value.startsWith("@")) return tokens[value.slice(1)] ?? value;
  if (Array.isArray(value)) return value.map(v => paint(v, tokens));
  if (value && typeof value === "object") return Object.fromEntries(Object.entries(value).map(([k, v]) => [k, paint(v, tokens)]));
  return value;
}
const painted = new Map();
function render(all) {
  if (!window.Plotly) return;
  const theme = current(), tokens = THEMES[theme];
  document.querySelectorAll("script[data-chart]").forEach(spec => {
    const target = document.getElementById(spec.dataset.chart);
    if (!target || target.offsetParent === null) return;
    if (!all && painted.get(target.id) === theme) { Plotly.Plots.resize(target); return; }
    const fig = paint(JSON.parse(spec.textContent), tokens);
    Plotly.react(target, fig.data, fig.layout, {displaylogo: false, responsive: true});
    painted.set(target.id, theme);
  });
}
function show() {
  const [view, sub] = (decodeURIComponent(location.hash.slice(1)) || "index").split("/");
  const known = document.querySelector(`[data-view="${view}"]`) ? view : "index";
  document.querySelectorAll("[data-view]").forEach(v => v.hidden = v.dataset.view !== known);
  document.querySelectorAll("[data-nav]").forEach(a => a.dataset.nav === known
    ? a.setAttribute("aria-current", "page") : a.removeAttribute("aria-current"));
  const box = document.querySelector(`[data-view="${known}"]`);
  const panels = box.querySelectorAll("[data-panel]");
  if (panels.length) {
    const chosen = [...panels].some(p => p.dataset.panel === sub) ? sub : panels[0].dataset.panel;
    panels.forEach(p => p.hidden = p.dataset.panel !== chosen);
    box.querySelectorAll("[data-tab]").forEach(t => t.setAttribute("aria-current", String(t.dataset.tab === chosen)));
  }
  render(false);
  const anchor = location.hash.split("/")[2];
  if (anchor && document.getElementById(anchor)) document.getElementById(anchor).scrollIntoView();
  else window.scrollTo(0, 0);
}
document.getElementById("theme").addEventListener("click", () => {
  document.documentElement.dataset.theme = current() === "dark" ? "light" : "dark";
  render(true);
});
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => render(true));
addEventListener("hashchange", show);
%(story_js)s
show();
loadPlotly().then(() => render(true));
</script></body></html>
"""


def packed_plotly():
    """plotly.js of the Plotly package, gzip-compressed and in base64, for the page to unpack."""
    from plotly.offline import get_plotlyjs
    return base64.b64encode(gzip.compress(get_plotlyjs().encode("utf-8"), 9, mtime=0)).decode("ascii")


def page(index, rules, policy, story):
    from . import story as stories

    def tokens(theme):
        return " ".join(f"--{k}: {v};" for k, v in THEMES[theme].items())
    return PAGE % dict(light=tokens("light"), dark=tokens("dark"), font=FONT, index=index, rules=rules, policy=policy,
                       story=story or "", story_nav='<a href="#story" data-nav="story">Story</a>' if story else "",
                       story_css=stories.CSS, story_js=stories.JS, plotly=packed_plotly(), themes=json.dumps(THEMES))


def atlas(tasks=None):
    """Write runs/atlas.html from the artifacts of every task; return its path."""
    from . import story
    tasks = tasks or list(scoring.TASKS)
    ablations = [found for task in tasks if (found := load_ablation(task))]
    policies = load_policies()
    story_html = story.view()
    out = paths.RUNS / "atlas.html"
    out.write_text(page(index_view(tasks, ablations, policies, story_html), rules_view(tasks), policy_view(policies),
                        story_html), encoding="utf-8")
    return out
