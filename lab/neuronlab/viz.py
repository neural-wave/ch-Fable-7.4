"""`lab viz`: the charts that show where a rule is right and where it is wrong, in one offline page.

The charts are read from the artifacts of the other steps only (`diffs.parquet` of `lab score`), so they work for
any target. Figures are plain Plotly JSON. Their colors are tokens such as `@series-1` or `@surface`, which the page
replaces with the values of the light or the dark theme, so that both themes are designed, not inverted.
"""
import html
import json
import math

import polars as pl

from . import paths
from .store import scoring

THEMES = {
    "light": {"surface": "#fcfcfb", "page": "#f9f9f7", "ink": "#0b0b0b", "ink2": "#52514e", "muted": "#898781",
              "grid": "#e1e0d9", "axis": "#c3c2b7", "border": "rgba(11,11,11,0.10)",
              "series-1": "#2a78d6", "series-2": "#eb6834", "series-3": "#1baf7a", "neutral": "#c3c2b7"},
    "dark": {"surface": "#1a1a19", "page": "#0d0d0d", "ink": "#f0efec", "ink2": "#c3c2b7", "muted": "#898781",
             "grid": "#2c2c2a", "axis": "#383835", "border": "rgba(255,255,255,0.10)",
             "series-1": "#3987e5", "series-2": "#d95926", "series-3": "#199e70", "neutral": "#52514e"},
}
FONT = 'system-ui, -apple-system, "Segoe UI", sans-serif'


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


def load_diffs(task):
    """diffs.parquet of the last `lab score <task>`, or None."""
    path = paths.run_dir(task) / "diffs.parquet"
    return pl.read_parquet(path) if path.exists() else None


def value_columns(diffs):
    return [c.split(":", 1)[1] for c in diffs.columns if c.startswith("diff:")]


def exact_rows(diffs):
    """Rows whose every value equals the target, as scoring.accuracy counts them."""
    same = pl.all_horizontal([pl.col(f"target:{v}") == pl.col(f"computed:{v}") for v in value_columns(diffs)])
    return int(diffs.select(same.fill_null(False).sum()).item())


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
            label = f"{task.split('_')[0]} · {value}"
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
    height = 60 + 34 * len(labels)
    fig = dict(data=[trace], layout=layout(
        height=height,
        xaxis=dict(tickvals=[signed_log(t) for t in ticks], ticktext=[f"{t:+g}" if t else "0" for t in ticks],
                   title=dict(text="target − computed (currency units, log scale)", font=dict(color="@muted")),
                   zeroline=True),
        yaxis=dict(categoryorder="array", categoryarray=labels[::-1], type="category")))
    return fig


def tiles(tasks):
    """One tile per scored task: exact rows of the last `lab score`."""
    out = []
    for task in tasks:
        diffs = load_diffs(task)
        if diffs is None:
            out.append(f'<div class="tile"><div class="tile-label">{task}</div><div class="tile-note">not scored '
                       f'yet: lab score {task}</div></div>')
            continue
        ok, total = exact_rows(diffs), diffs.height
        out.append(f'<div class="tile"><div class="tile-label">{task}</div><div class="tile-value">'
                   f'{100 * ok / total:.2f}%</div><div class="tile-note">{ok:,} of {total:,} rows exact</div></div>')
    return '<div class="tiles">' + "".join(out) + "</div>"


def section(title, lead, body):
    return f'<section><h2>{html.escape(title)}</h2><p class="lead">{lead}</p>{body}</section>'


def chart(fig, name):
    """A chart placeholder; the page script renders it with the current theme."""
    return f'<div class="chart" id="{name}"></div><script type="application/json" data-chart="{name}">' \
           f'{json.dumps(fig, default=str)}</script>'


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Neuron Rule Atlas</title>
<style>
:root { color-scheme: light; %(light)s }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { color-scheme: dark; %(dark)s } }
:root[data-theme="dark"] { color-scheme: dark; %(dark)s }
body { margin: 0; background: var(--page); color: var(--ink); font-family: %(font)s; line-height: 1.5; }
main { max-width: 1080px; margin: 0 auto; padding: 24px 16px 64px; }
header { display: flex; justify-content: space-between; align-items: baseline; gap: 16px; flex-wrap: wrap; }
h1 { font-size: 28px; margin: 0; } h2 { font-size: 20px; margin: 40px 0 4px; }
.lead { color: var(--ink2); margin: 0 0 16px; max-width: 72ch; }
.chart { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 8px; }
.tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; }
.tile { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 12px 16px; }
.tile-label { color: var(--ink2); font-size: 13px; } .tile-value { font-size: 28px; font-weight: 600; }
.tile-note { color: var(--muted); font-size: 13px; font-variant-numeric: tabular-nums; }
button { font: inherit; background: var(--surface); color: var(--ink); border: 1px solid var(--border);
         border-radius: 6px; padding: 4px 12px; cursor: pointer; }
</style></head><body><main>
<header><h1>Neuron Rule Atlas</h1><button id="theme" type="button">Switch theme</button></header>
<p class="lead">%(intro)s</p>
%(sections)s
</main>
<script>%(plotly)s</script>
<script>
const THEMES = %(themes)s;
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
function render() {
  const tokens = THEMES[current()];
  document.querySelectorAll("script[data-chart]").forEach(spec => {
    const fig = paint(JSON.parse(spec.textContent), tokens);
    Plotly.react(spec.dataset.chart, fig.data, fig.layout, {displaylogo: false, responsive: true});
  });
}
document.getElementById("theme").addEventListener("click", () => {
  document.documentElement.dataset.theme = current() === "dark" ? "light" : "dark";
  render();
});
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", render);
render();
</script></body></html>
"""


def page(intro, sections):
    from plotly.offline import get_plotlyjs
    def tokens(theme):
        return " ".join(f"--{k}: {v};" for k, v in THEMES[theme].items())
    return PAGE % dict(light=tokens("light"), dark=tokens("dark"), font=FONT, intro=intro,
                       sections="\n".join(sections), plotly=get_plotlyjs(), themes=json.dumps(THEMES))


def atlas(tasks=None):
    """Write runs/atlas.html from the artifacts of every scored task; return its path."""
    tasks = tasks or list(scoring.TASKS)
    sections = [
        section("Exact rows", "The share of target rows that the rules reproduce to the cent and to the day, from "
                "the last <code>lab score</code> of each task.", tiles(tasks)),
        section("What kind of mistakes are left",
                "Every value that differs from the target is one dot. One cent is a rounding, a whole number of "
                "francs is a value typed by hand (task t5), a large amount is a rule that is still missing.",
                chart(difference_strip(tasks), "differences")),
    ]
    out = paths.RUNS / "atlas.html"
    out.write_text(page("How the rules of Neuron were found and how well they reproduce its values.", sections),
                   encoding="utf-8")
    return out
