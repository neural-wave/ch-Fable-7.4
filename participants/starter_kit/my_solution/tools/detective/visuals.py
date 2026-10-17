"""Visualizations (t6): pictures of the rules, of the places where a rule changes and of one policy's accounting.

    uv run python -m detective.visuals          # writes tools/visuals/*.png and index.html

- `conversion_chart`: the share of wrong projected values (t2) by application month, with the rounding of Neuron
  NG for all policies; the step at the system conversion is the finding t2_projection_year/r2-search-old
- `birthday_chart`: the same share by the days from the start date to the insured's next birthday, with the age
  in completed years; the step half a year before the birthday is the age convention (nearest birthday)
- `cents_chart`: the differences of the first rule of every target, in cents: rounding shows as ±1
- `calendar_chart`: the due dates and the collection dates of the next year (t1) as calendar heat maps
- `waterfall_chart`: an annual statement (t4) from the premiums to what was invested after all charges
- `timeline_chart`: one policy's life: its value at every run, the premiums and the charges of every month
"""
import datetime as dt
import json
import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import polars as pl  # noqa: E402

from accounting import accounting, holdings  # noqa: E402
from detective.load import LEGACY, load  # noqa: E402
from detective.report import REPORTS  # noqa: E402
from detective.targets import target  # noqa: E402
from eras import conversion_day  # noqa: E402
from projection import projected_years  # noqa: E402
from schedule import next_due_dates  # noqa: E402
from statement import statements  # noqa: E402
from surrender import valued  # noqa: E402

VISUALS = pathlib.Path(__file__).resolve().parents[1] / "visuals"
SURFACE, INK, SECONDARY, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]  # the first categorical slots of the dataviz reference palette
SEQUENTIAL = ["#fcfcfb", "#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
EXAMPLE = ("BL10000013", 2021)  # the example of the task text
EXTRACT = dt.date(2026, 6, 30)


def styled(axes) -> None:
    """Recessive chrome: no top and right frame, a hairline grid behind the marks, muted ticks."""
    axes.set_facecolor(SURFACE)
    for side in ("top", "right"):
        axes.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        axes.spines[side].set_color(AXIS)
    axes.grid(axis="y", color=GRID, linewidth=0.6)
    axes.set_axisbelow(True)
    axes.tick_params(colors=MUTED, labelcolor=SECONDARY, labelsize=9)


def figure(title: str, subtitle: str, rows: int = 1, cols: int = 1, size=(10, 4.5), **options):
    """A figure on the chart surface with a title and a subtitle in the text inks."""
    fig, axes = plt.subplots(rows, cols, figsize=size, facecolor=SURFACE, **options)
    fig.suptitle(title, x=0.01, ha="left", fontsize=13, color=INK, fontweight="bold")
    fig.text(0.01, 0.905, subtitle, ha="left", fontsize=9.5, color=SECONDARY)
    for single in np.atleast_1d(axes).ravel():
        styled(single)
    return fig, axes


def saved(fig, name: str, laid_out: bool = False) -> pathlib.Path:
    """Write `fig` as tools/visuals/<name>.png (fitted to the page unless it is `laid_out` already)."""
    VISUALS.mkdir(parents=True, exist_ok=True)
    path = VISUALS / f"{name}.png"
    if not laid_out:
        fig.tight_layout(rect=(0, 0, 1, 0.88))
    fig.savefig(path, dpi=150, facecolor=SURFACE)
    plt.close(fig)
    return path


def wrong_projections(legacy: pathlib.Path, **conventions) -> pl.DataFrame:
    """policy_id and WRONG (the share of the policy's projected years the rule misses), with `conventions`."""
    made = projected_years(legacy, **conventions).rename({"value": "RULE"})
    years = target("t2_projection_year").join(made, on=["policy_id", "policy_year"], how="left")
    return years.group_by("policy_id").agg(WRONG=pl.col("value").ne_missing(pl.col("RULE")).mean())


def conversion_chart(legacy: pathlib.Path = LEGACY) -> pathlib.Path:
    """The share of wrong projections by application month, all policies rounded half up."""
    policies = load("NRPOLH").group_by(policy_id="PH_POLNR").agg(pl.col("PH_APPDT").first())
    wrong = wrong_projections(legacy, rounding="half_up").join(policies, on="policy_id")
    monthly = wrong.group_by(MONTH=pl.col("PH_APPDT").dt.truncate("1mo")).agg(pl.col("WRONG").mean()).sort("MONTH")
    fig, axes = figure("Projected values wrong with Neuron NG's rounding, by application month",
                       "t2: share of policy years off when every offer rounds half up; the old system cut cents off")
    axes.plot(monthly["MONTH"], monthly["WRONG"], color=SERIES[0], linewidth=2)
    switch = conversion_day(legacy)
    axes.axvline(switch, color=MUTED, linewidth=1, linestyle="--")
    axes.annotate(f"system conversion {switch}", (switch, 0.9), xytext=(8, 0), textcoords="offset points",
                  color=SECONDARY, fontsize=9)
    axes.set_ylim(0, 1)
    axes.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1))
    return saved(fig, "conversion")


def birthday_chart(legacy: pathlib.Path = LEGACY) -> pathlib.Path:
    """The share of wrong projections by days from the start date to the next birthday, ages in completed years."""
    people = load("NRRISK").join(load("NRPERS"), left_on="RK_PERNR", right_on="PS_PERNR").select(
        policy_id="RK_POLNR", BIRTH="PS_BIRTH")
    starts = load("NRPOLH").group_by(policy_id="PH_POLNR").agg(pl.col("PH_BEGDT").first())
    birthday = pl.col("BIRTH").dt.offset_by(pl.format("{}y", pl.col("PH_BEGDT").dt.year().sub(pl.col("BIRTH").dt.year())))
    next_birthday = pl.when(birthday.lt(pl.col("PH_BEGDT"))).then(birthday.dt.offset_by("1y")).otherwise(birthday)
    wrong = wrong_projections(legacy, age="completed").join(people, on="policy_id").join(starts, on="policy_id")
    days = wrong.with_columns(DAYS=next_birthday.sub(pl.col("PH_BEGDT")).dt.total_days().floordiv(7).mul(7)).drop_nulls("DAYS")
    weekly = days.group_by("DAYS").agg(pl.col("WRONG").mean()).sort("DAYS")
    fig, axes = figure("Projected values wrong with the age in completed years, by days to the next birthday",
                       "t2: the rule misses the insured persons less than half a year before their birthday: "
                       "Neuron counts the nearest birthday")
    axes.bar(weekly["DAYS"], weekly["WRONG"], width=6, color=SERIES[0])
    axes.axvline(182.5, color=MUTED, linewidth=1, linestyle="--")
    axes.annotate("half a year", (182.5, 0.95), xytext=(8, 0), textcoords="offset points", color=SECONDARY,
                  fontsize=9)
    axes.set_xlabel("days from the start date to the next birthday", color=SECONDARY, fontsize=9)
    axes.set_ylim(0, 1)
    axes.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1))
    return saved(fig, "birthday")


FIRST_ROUNDS = {"t0_commission": "r1", "t2_projection_year": "r3", "t3_booking_prm": "r3",
                "t3_booking_adm": "r3", "t3_booking_amc": "r3", "t3_booking_rsk": "r2"}


def cents_chart() -> pathlib.Path:
    """The most common differences (rule minus target, in cents) of an early round of every target."""
    fig, axes = figure("Most common differences of an early rule, in cents",
                       "rule minus target of the wrong rows; ±1 cent is rounding, larger steps are a convention",
                       2, 3, size=(11, 6), sharey=False)
    for single, (name, round_name) in zip(axes.ravel(), FIRST_ROUNDS.items()):
        found = json.loads((REPORTS / name / f"{round_name}.json").read_text())["differences"]
        value = "amount_pc" if "amount_pc" in found else next(iter(found))
        rows = sorted((row for row in found[value] if row["DIFF"] is not None), key=lambda row: row["DIFF"])
        single.bar([str(row["DIFF"]) for row in rows], [row["ROWS"] for row in rows], color=SERIES[0])
        single.set_title(f"{name} {round_name}", fontsize=9.5, color=INK, loc="left")
        single.tick_params(axis="x", labelrotation=45)
    return saved(fig, "cents")


def calendar_grid(days: pl.Series, start: dt.date) -> tuple[np.ndarray, dict[int, str]]:
    """(a 7 x 53 grid of the counts per day of the year from `start`, rows Monday to Sunday, empty where none;
    {week: month name} of the weeks where a month begins)."""
    grid = np.full((7, 53), np.nan)
    counts = dict(days.value_counts().iter_rows())
    first_monday = start - dt.timedelta(days=start.weekday())
    months = {}
    for offset in range(365):
        day = start + dt.timedelta(days=offset)
        week = (day - first_monday).days // 7
        grid[day.weekday(), week] = counts.get(day, np.nan)
        if day.day == 1:
            months[week] = day.strftime("%b")
    return grid, months


def calendar_chart(legacy: pathlib.Path = LEGACY) -> pathlib.Path:
    """The due dates and collection dates of the year after the extract date as calendar heat maps."""
    dues = next_due_dates(legacy, EXTRACT)
    start = EXTRACT + dt.timedelta(days=1)
    fig, axes = figure("Due dates and collection dates of the next year (t1)",
                       "premiums per day from July 2026; direct debits move to the next Ticino business day: "
                       "weekends and holidays thin out, Mondays fill up",
                       2, 1, size=(11, 4.8))
    fig.subplots_adjust(left=0.06, right=0.9, top=0.8, bottom=0.07, hspace=0.45)
    colours = matplotlib.colors.LinearSegmentedColormap.from_list("blues", SEQUENTIAL[1:])
    colours.set_bad(SURFACE)
    scale = matplotlib.colors.LogNorm(vmin=1, vmax=dues["due_date"].value_counts()["count"].max())
    for single, column, title in zip(axes, ["due_date", "collection_date"], ["due dates", "collection dates"]):
        grid, months = calendar_grid(dues[column], start)
        shown = single.imshow(grid, cmap=colours, norm=scale, aspect="auto")
        single.set_title(title, fontsize=9.5, color=INK, loc="left")
        single.set_yticks(range(7), ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])
        single.set_xticks(list(months), list(months.values()))
        single.grid(False)
    bar = fig.colorbar(shown, cax=fig.add_axes((0.92, 0.12, 0.012, 0.62)))
    bar.set_label("premiums per day (log scale)", color=SECONDARY, fontsize=9)
    bar.ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda count, _: f"{count:g}"))
    bar.ax.tick_params(colors=MUTED, labelcolor=SECONDARY, labelsize=8)
    bar.outline.set_visible(False)
    return saved(fig, "calendar", laid_out=True)


def waterfall_chart(bookings: pl.DataFrame, legacy: pathlib.Path = LEGACY) -> pathlib.Path:
    """The annual statement of the task's example (BL10000013, 2021) as a waterfall: the premiums, every charge
    taken off, what is left."""
    policy, year = EXAMPLE
    row = statements(legacy, bookings).filter(pl.col("BK_POLNR").eq(policy), pl.col("YEAR").eq(year)).row(0, named=True)
    steps = [("premiums", row["PREMIUMS"]), ("entry", -row["ENTRY"]), ("admin", -row["ADMIN"]),
             ("management", -row["MANAGEMENT"]), ("risk", -row["RISK"])]
    fig, axes = figure(f"Annual statement {year} of {policy} (t4)",
                       "from the premiums received to what is left after the entry, admin, management and risk "
                       "charges; francs", size=(9, 4.5))
    level = 0
    for position, (name, cents) in enumerate(steps):
        bottom = level if cents >= 0 else level + cents
        axes.bar(position, abs(cents) / 100, bottom=bottom / 100, color=SERIES[0] if cents >= 0 else SERIES[1], width=0.6)
        axes.annotate(f"{cents / 100:+,.2f}", (position, (level + max(cents, 0)) / 100), xytext=(0, 4),
                      textcoords="offset points", ha="center", color=SECONDARY, fontsize=9)
        level += cents
    axes.bar(len(steps), level / 100, color=SERIES[2], width=0.6)
    axes.annotate(f"{level / 100:,.2f}", (len(steps), level / 100), xytext=(0, 4), textcoords="offset points",
                  ha="center", color=SECONDARY, fontsize=9)
    axes.set_xticks(range(len(steps) + 1), [name for name, _ in steps] + ["net"])
    return saved(fig, "waterfall")


def timeline_chart(bookings: pl.DataFrame, legacy: pathlib.Path = LEGACY) -> pathlib.Path:
    """The life of the task's example policy (BL10000013): its value at every run, and its premiums and charges
    per month."""
    policy = EXAMPLE[0]
    own = bookings.filter(pl.col("BK_POLNR").eq(policy))
    runs = own.filter(pl.col("BK_BKTYP").eq("ADM"))["BK_TRDDT"].unique().sort().to_list()
    value = valued(legacy, holdings(own, runs), ("down", "half_up"), "each", "exact").sort("VALUATION")
    monthly = own.filter(pl.col("BK_BKTYP").is_in(["PRM", "ADM", "AMC", "RSK"]), pl.col("BK_TRDDT").le(runs[-1])).group_by(
        MONTH=pl.col("BK_TRDDT").dt.truncate("1mo"), KIND=pl.col("BK_BKTYP").eq("PRM")).agg(pl.col("BK_AMTPC").sum())
    fig, (top, bottom) = figure(f"The life of {policy}: value, premiums and charges",
                                "top: the policy value at every charge run (francs); bottom: premiums invested "
                                "and charges taken per month (francs)", 2, 1, size=(11, 6), sharex=True)
    top.plot(value["VALUATION"], value["POLICY_VALUE"] / 100, color=SERIES[0], linewidth=2)
    for kind, colour, sign, label in [(True, SERIES[0], 1, "premiums"), (False, SERIES[1], -1, "charges")]:
        part = monthly.filter(pl.col("KIND").eq(kind)).sort("MONTH")
        bottom.bar(part["MONTH"], sign * part["BK_AMTPC"] / 100, width=25, color=colour, label=label)
    bottom.axhline(0, color=AXIS, linewidth=0.8)
    bottom.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, frameon=False, fontsize=9, labelcolor=SECONDARY)
    return saved(fig, "timeline")


def index(paths: list[pathlib.Path]) -> pathlib.Path:
    """tools/visuals/index.html: every picture with the docstring of the function that drew it."""
    captions = {name.split("_")[0]: function.__doc__.split("\n")[0] for name, function in globals().items()
                if name.endswith("_chart")}
    items = "\n".join(f'<figure><img src="{path.name}" alt="{captions[path.stem]}"><figcaption>{captions[path.stem]}'
                      f"</figcaption></figure>" for path in paths)
    page = (f"<!doctype html><html lang=en><meta charset=utf-8><title>Neuron rules</title><style>"
            f"body{{background:{SURFACE};color:{INK};font-family:system-ui,sans-serif;max-width:1100px;margin:auto;"
            f"padding:16px}}img{{width:100%}}figcaption{{color:{SECONDARY};margin:4px 0 32px}}</style>"
            f"<h1>Neuron rules, pictured</h1>{items}</html>")
    path = VISUALS / "index.html"
    path.write_text(page)
    return path


def main() -> None:
    bookings = accounting(LEGACY, dt.date(2025, 12, 31))
    paths = [conversion_chart(), birthday_chart(), cents_chart(), calendar_chart(), waterfall_chart(bookings),
             timeline_chart(bookings)]
    print(index(paths))


if __name__ == "__main__":
    main()
