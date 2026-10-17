"""Automated discovery for t7: the patterns in the tax tables that point at the rules of Neuron's tax module.

Every section is a general analysis: it looks at all tax types, countries, jobs and years alike, prints its evidence
as counts, dates and rates (never a calculated tax amount) and ends with FINDING lines for what stands out.

 1. codes      every tax type of NRCODE against its rates (NRTAXR) and bookings (NRTAXB): a type without rates
               takes its amount from other bookings, a type without bookings changes the base of another
 2. rates      the timeline of NRTAXR per country, type and region: the first day of a tax, gaps, rate changes,
               versions entered after the day they apply from, restatements of a period
 3. bookings   per type the first and last year, the years without bookings, the bookings without a valid rate
               and those whose rate differs between "as known at processing" and "as known today"
 4. jobs       per job user TB_USRID the days it ran, its era (COBOL or Neuron NG, `conventions.CONVERSION`), its
               usual delay from the effective date and time of day: the batch schedules
 5. eras       the taxed payouts on which "rounding by country" and "rounding by system era" disagree
 6. remittance the remittance days (`conventions.REMITTANCE`) on a weekend or public holiday, and the payouts
               processed in a later month than they are effective: where a shift would change the date
 7. fx         payouts and premiums dated before the first exchange rate of their currency
 8. separation the base definitions of `base_split` that separate the taxed payouts best, per event type
 9. trees      per tax type a shallow decision tree that predicts which payouts got a booking from the residence,
               the event, dates, ages and earlier bookings: its splits are candidate conditions, its errors the
               exceptions to look at by hand
10. changes    the years in which the share of residents' payouts with a tax type jumps

    NEURON_DATA=<participants> PYTHONPATH="$PWD:$PWD/tools:$PWD/.." python -B -m t7lab.t7_discover [--section trees ...]
"""
import argparse

import holidays
import polars as pl
from sklearn.tree import DecisionTreeClassifier, export_text

from bookings import received_premiums
from conventions import CONVERSION, REMITTANCE, TAX_CURRENCY, TAXES, TRUNCATED, WITHHELD
from dates import completed_years
from legacy import as_date, as_lenient_date, table, valid_on
from market import exchange_rates
from t7lab.base_split import separations
from neuron.load import LEGACY
from t7lab.tax_join import joined
from payouts import EVENT, payouts

RATE_KEY = ["TX_CNTRY", "TX_TAXTP", "TX_REGIO"]  # one rate series of NRTAXR
CATEGORIES = ["AD_CNTRY", "AD_REGIO", "AD_TAXST", "AD_CHURCH", "EVENT_TYPE", "PH_CCY"]  # tree features, one-hot
NUMBERS = ["PAYOUT_YEAR", "START_YEAR", "YEARS_HELD", "AGE", "NEURON_NG", "FULL", "BASE_POSITIVE"]  # tree features
DOMINANT = 0.9  # a delay or time of day shared by this many of a job's bookings is its schedule
JUMP = 0.5  # a change of the yearly share of payouts with a tax type at least this large is a change point
MIN_PAYOUTS = 5  # ... between two years with at least this many payouts each; fewer are noise
EXAMPLES = 8  # exceptions of a tree listed by policy and event


def finding(text: str):
    print(f"FINDING  {text}")


def show(frame: pl.DataFrame):
    with pl.Config(tbl_rows=-1, tbl_cols=-1, tbl_width_chars=220, fmt_str_lengths=60,
                   tbl_formatting="ASCII_MARKDOWN", tbl_hide_dataframe_shape=True):  # ASCII: Windows consoles
        print(frame)


def timestamp(col: str) -> pl.Expr:
    """The legacy timestamp `YYYYMMDDHHMMSS` of column `col` as a datetime."""
    return pl.col(col).cast(pl.String).str.to_datetime("%Y%m%d%H%M%S", strict=False)


def mode_share(col: pl.Expr) -> tuple[pl.Expr, pl.Expr]:
    """The most frequent value of `col` in a group and the share of the group that has it."""
    return col.drop_nulls().mode().sort().first(), col.eq(col.drop_nulls().mode().sort().first()).mean()


# 1. codes ------------------------------------------------------------------------------------------------------------

def codes(legacy_dir):
    names = table(legacy_dir, "NRCODE").filter(pl.col("CD_DOMAIN").eq("TAXTP")).select(TAXTP="CD_CODE", TEXT="CD_TXTDE")
    rates = table(legacy_dir, "NRTAXR").group_by(TAXTP="TX_TAXTP").agg(RATES=pl.len())
    booked = table(legacy_dir, "NRTAXB").group_by(TAXTP="TB_TAXTP").agg(BOOKINGS=pl.len())
    frame = names.join(rates, on="TAXTP", how="full", coalesce=True).join(booked, on="TAXTP", how="full",
                                                                         coalesce=True)
    frame = frame.with_columns(pl.col("RATES", "BOOKINGS").fill_null(0)).sort("TAXTP")
    show(frame)
    for tax, text, rates_n, bookings_n in frame.iter_rows():
        if text is None:
            finding(f"{tax} is booked or rated but not in NRCODE: a typo or an undocumented type")
        elif bookings_n and not rates_n:
            finding(f"{tax} ({text}) is booked {bookings_n}x without any rate: its amount comes from other bookings")
        elif rates_n and not bookings_n:
            finding(f"{tax} ({text}) has rates but no bookings: it changes the base or rate of another type")


# 2. rates ------------------------------------------------------------------------------------------------------------

def rate_rows(legacy_dir) -> pl.DataFrame:
    rates = table(legacy_dir, "NRTAXR").with_columns(pl.col("TX_REGIO").fill_null(""))
    return rates.with_columns(FROM=as_date("TX_VLDFR"), TO=as_date("TX_VLDTO"), ENTERED=timestamp("TX_CHGTS").dt.date(),
                              PERCENT=pl.col("TX_RATE").truediv(10_000)).sort(*RATE_KEY, "TX_VLDFR", "TX_VRSNR")


def restatements(rates: pl.DataFrame) -> pl.DataFrame:
    """Pairs of versions of one series whose periods overlap: the later version restates the earlier one."""
    pairs = rates.join(rates, on=RATE_KEY, suffix="_NEW").filter(
        pl.col("TX_VRSNR_NEW").gt(pl.col("TX_VRSNR")), pl.col("TX_VLDFR_NEW").le(pl.col("TX_VLDTO")),
        pl.col("TX_VLDTO_NEW").ge(pl.col("TX_VLDFR")))
    return pairs.select(*RATE_KEY, "FROM", "TO", OLD="PERCENT", NEW="PERCENT_NEW", ENTERED="ENTERED_NEW",
                        DAYS_LATE=pl.col("ENTERED_NEW").sub(pl.col("FROM_NEW")).dt.total_days())


def periods(rates: pl.DataFrame, keep: str) -> pl.DataFrame:
    """One version of every period of a series, the first entered or the `keep` "last" (today's view), with the
    end of the period before (PREV_TO) and its rate (PREV)."""
    chosen = rates.sort("TX_VRSNR").unique([*RATE_KEY, "TX_VLDFR"], keep=keep).sort(*RATE_KEY, "TX_VLDFR")
    return chosen.with_columns(PREV_TO=pl.col("TO").shift().over(RATE_KEY),
                               PREV=pl.col("PERCENT").shift().over(RATE_KEY))


def rate_changes(rates: pl.DataFrame) -> pl.DataFrame:
    """The rate changes between consecutive periods, as known today and as first entered (VIEW)."""
    views = [periods(rates, keep).with_columns(VIEW=pl.lit(view)) for keep, view in [("last", "today"),
                                                                                      ("first", "as first entered")]]
    changes = pl.concat(views).filter(pl.col("PREV").is_not_null(), pl.col("PERCENT").ne(pl.col("PREV")))
    return changes.group_by(*RATE_KEY, "FROM", "PREV", "PERCENT").agg(pl.col("VIEW").sort().str.join(" and ")).sort(
        *RATE_KEY, "FROM")


def rate_timeline(legacy_dir):
    rates = rate_rows(legacy_dir)
    show(rates.select(*RATE_KEY, "FROM", "TO", "TX_VRSNR", "PERCENT", "TX_THRSH", "ENTERED",
                      DAYS_LATE=pl.col("ENTERED").sub(pl.col("FROM")).dt.total_days()))
    latest, loaded = periods(rates, "last"), rates["FROM"].min()  # the earliest day: the initial load, no news
    starts = latest.group_by(RATE_KEY).agg(pl.col("FROM").min()).filter(pl.col("FROM").gt(loaded)).sort(RATE_KEY)
    for *key, first in starts.iter_rows():
        finding(f"{'/'.join(filter(None, key))} exists from {first}: a booking before it has no rate")
    gaps = latest.filter(pl.col("FROM").gt(pl.col("PREV_TO").dt.offset_by("1d")))
    for row in gaps.iter_rows(named=True):
        finding(f"{row['TX_CNTRY']}/{row['TX_TAXTP']} has no rate from {row['PREV_TO']} to {row['FROM']}")
    for row in rate_changes(rates).iter_rows(named=True):
        finding(f"{row['TX_CNTRY']}/{row['TX_TAXTP']}{'/' + row['TX_REGIO'] if row['TX_REGIO'] else ''} changes "
                f"from {row['PREV']}% to {row['PERCENT']}% on {row['FROM']} ({row['VIEW']})")
    late = rates.filter(pl.col("ENTERED").gt(pl.col("FROM")))
    for row in late.iter_rows(named=True):
        finding(f"{row['TX_CNTRY']}/{row['TX_TAXTP']} version {row['TX_VRSNR']} from {row['FROM']} was entered "
                f"{(row['ENTERED'] - row['FROM']).days} days late, on {row['ENTERED']}: bookings processed before "
                "then did not know it")
    for row in restatements(rates).iter_rows(named=True):
        finding(f"{row['TX_CNTRY']}/{row['TX_TAXTP']} {row['FROM']} - {row['TO']} restated from {row['OLD']}% to "
                f"{row['NEW']}% on {row['ENTERED']}: look for a correction job after that day")


# 3. bookings ---------------------------------------------------------------------------------------------------------

def booking_timeline(legacy_dir):
    known = joined(legacy_dir, "TB_CHGTS").with_columns(YEAR=as_date("TB_EFFDT").dt.year())
    today = joined(legacy_dir).select("TB_BOOKID", RATE_TODAY="TX_RATE")
    rated = set(table(legacy_dir, "NRTAXR")["TX_TAXTP"])
    both = known.join(today, on="TB_BOOKID", how="left")
    summary = both.group_by("TB_TAXTP").agg(
        BOOKINGS=pl.len(), FIRST=pl.col("YEAR").min(), LAST=pl.col("YEAR").max(),
        YEARS=pl.col("YEAR").n_unique(), NO_RATE=pl.col("TX_RATE").is_null().sum(),
        RATE_CHANGED_SINCE=pl.col("TX_RATE").ne_missing(pl.col("RATE_TODAY")).sum()).sort("TB_TAXTP")
    show(summary)
    for row in summary.iter_rows(named=True):
        tax, span = row["TB_TAXTP"], row["LAST"] - row["FIRST"] + 1
        finding(f"{tax} is booked from {row['FIRST']} to {row['LAST']}" +
                (f", but in {row['YEARS']} of those {span} years only" if row["YEARS"] < span else ""))
        if row["NO_RATE"] and tax in rated:
            years = sorted(set(both.filter(pl.col("TB_TAXTP").eq(tax), pl.col("TX_RATE").is_null())["YEAR"]))
            finding(f"{row['NO_RATE']} {tax} bookings have no rate known at processing (years {years})")
        if row["RATE_CHANGED_SINCE"]:
            finding(f"{row['RATE_CHANGED_SINCE']} {tax} bookings had another rate at processing than today: "
                    "Neuron used the rate it knew then")


# 4. jobs -------------------------------------------------------------------------------------------------------------

def jobs(legacy_dir):
    person = pl.col("TB_USRID").str.contains(r"^U\d+$")
    done = timestamp("TB_CHGTS")
    bookings = table(legacy_dir, "NRTAXB").with_columns(
        JOB=pl.when(person).then(pl.lit("U* (person)")).otherwise("TB_USRID"), DONE=done,
        DELAY=done.dt.date().sub(as_date("TB_EFFDT")).dt.total_days(), TIME=done.dt.strftime("%H:%M"))
    delay, delay_share = mode_share(pl.col("DELAY"))
    time, time_share = mode_share(pl.col("TIME"))
    summary = bookings.group_by("JOB").agg(
        BOOKINGS=pl.len(), TYPES=pl.col("TB_TAXTP").unique().sort().str.join(","),
        FIRST=pl.col("DONE").min().dt.date(), LAST=pl.col("DONE").max().dt.date(),
        COBOL=pl.col("DONE").dt.date().lt(CONVERSION).sum(), DELAY=delay, DELAY_SHARE=delay_share.round(2),
        TIME=time, TIME_SHARE=time_share.round(2)).sort("FIRST")
    show(summary)
    for row in summary.iter_rows(named=True):
        era = ("only COBOL" if row["COBOL"] == row["BOOKINGS"] else "only Neuron NG" if not row["COBOL"]
               else f"both eras ({row['COBOL']} COBOL)")
        finding(f"{row['JOB']} books {row['TYPES']} from {row['FIRST']} to {row['LAST']}: {era}")
        if row["DELAY_SHARE"] >= DOMINANT:
            finding(f"{row['JOB']} processes {row['DELAY']} days after the effective date in "
                    f"{row['DELAY_SHARE']:.0%} of its bookings")
        if row["TIME_SHARE"] >= DOMINANT:
            finding(f"{row['JOB']} runs at {row['TIME']} ({row['TIME_SHARE']:.0%}): a batch")


# payout features, shared by sections 5 - 10 ---------------------------------------------------------------------------

def booked_types(legacy_dir, rows: pl.DataFrame) -> pl.DataFrame:
    """`rows` with HAS_<type> (the payout has a booking of the type) and BEFORE_<type> (an earlier booking of the
    policy, processed before the payout)."""
    bookings = table(legacy_dir, "NRTAXB").select("TB_POLNR", "TB_EVTNR", "TB_TAXTP", BOOKED_AT="TB_CHGTS")
    types = sorted(set(bookings["TB_TAXTP"]))
    own = rows.select(*EVENT).join(bookings, on=EVENT).group_by(EVENT).agg(pl.col("TB_TAXTP").unique())
    earlier = rows.select(*EVENT, "TB_CHGTS").join(bookings.drop("TB_EVTNR"), on="TB_POLNR").filter(
        pl.col("BOOKED_AT").lt(pl.col("TB_CHGTS"))).group_by(EVENT).agg(EARLIER=pl.col("TB_TAXTP").unique())
    flagged = rows.join(own, on=EVENT, how="left").join(earlier, on=EVENT, how="left")
    return flagged.with_columns(
        *[pl.col("TB_TAXTP").list.contains(tax).fill_null(False).alias(f"HAS_{tax}") for tax in types],
        *[pl.col("EARLIER").list.contains(tax).fill_null(False).alias(f"BEFORE_{tax}") for tax in types]).drop(
        "TB_TAXTP", "EARLIER")


def payout_features(legacy_dir) -> pl.DataFrame:
    """Every reported payout (`payouts`) with its event type, address flags, dates, ages and booked types."""
    rows = payouts(legacy_dir)
    keys = rows.select(*EVENT, "HD_PERNR", "TB_EFFDT", "TB_CHGTS")
    address = valid_on(keys, table(legacy_dir, "NRADDR"), {"HD_PERNR": "AD_PERNR"}, "TB_EFFDT", "AD",
                       known_at="TB_CHGTS").select(*EVENT, "AD_TAXST", "AD_CHURCH")
    events = table(legacy_dir, "NREVNT").select(TB_POLNR="EV_POLNR", TB_EVTNR="EV_EVTNR",
                                                EVENT_TYPE=pl.col("EV_EVTTP").cast(pl.String))
    day, start = as_date("TB_EFFDT"), as_date("PH_BEGDT")
    featured = rows.join(address, on=EVENT, how="left").join(events, on=EVENT, how="left").with_columns(
        PAYOUT_YEAR=day.dt.year(), START_YEAR=start.dt.year(), YEARS_HELD=completed_years(start, day),
        AGE=completed_years(as_lenient_date("PS_BIRTH"), day), NEURON_NG=timestamp("TB_CHGTS").dt.date().ge(CONVERSION),
        BASE_POSITIVE=pl.col("TAXABLE_BASE").gt(0), EFFECTIVE=day, PROCESSED=timestamp("TB_CHGTS").dt.date())
    return booked_types(legacy_dir, featured)


# 5. eras -------------------------------------------------------------------------------------------------------------

def eras(rows: pl.DataFrame):
    taxed = rows.filter(pl.any_horizontal(f"HAS_{tax}" for tax in WITHHELD))
    by_country = pl.col("COUNTRY").is_in(TRUNCATED)
    counts = taxed.group_by("COUNTRY", "NEURON_NG").agg(PAYOUTS=pl.len(), DISAGREE=by_country.eq(
        pl.col("NEURON_NG").not_()).not_().sum()).sort("COUNTRY", "NEURON_NG")
    show(counts)
    for country, ng, n, disagree in counts.iter_rows():
        if disagree:
            rule = "truncates" if country in TRUNCATED else "rounds half up"
            finding(f"{disagree} taxed {country} payouts processed {'by Neuron NG' if ng else 'by COBOL'}: the "
                    f"current rule {rule}, rounding by system era would not; one probe of them decides")


# 6. remittance -------------------------------------------------------------------------------------------------------

def public_holidays(countries: list[str], years: range) -> pl.DataFrame:
    days = [(country, day) for country in countries
            for day in holidays.country_holidays(country, years=years)]
    return pl.DataFrame(days, schema={"COUNTRY": pl.String, "DUE": pl.Date}, orient="row").with_columns(
        HOLIDAY=pl.lit(True))


def remittance(rows: pl.DataFrame):
    taxed = rows.filter(pl.any_horizontal(f"HAS_{tax}" for tax in WITHHELD), pl.col("COUNTRY").is_in(list(REMITTANCE)))
    days = pl.duration(days=pl.col("COUNTRY").replace_strict(REMITTANCE, return_dtype=pl.Int64))
    due = taxed.with_columns(DUE=pl.col("EFFECTIVE").dt.month_start().dt.offset_by("1mo").add(days),
                             LATER_MONTH=pl.col("PROCESSED").dt.month_start().gt(pl.col("EFFECTIVE").dt.month_start()))
    years = range(due["DUE"].dt.year().min(), due["DUE"].dt.year().max() + 1)
    flagged = due.join(public_holidays(list(REMITTANCE), years), on=["COUNTRY", "DUE"], how="left").with_columns(
        WEEKEND=pl.col("DUE").dt.weekday().ge(6), HOLIDAY=pl.col("HOLIDAY").fill_null(False))
    counts = flagged.group_by("COUNTRY").agg(
        PAYOUTS=pl.len(), WEEKEND=pl.col("WEEKEND").sum(), HOLIDAY=pl.col("HOLIDAY").sum(),
        SHIFTED=pl.col("WEEKEND").or_(pl.col("HOLIDAY")).sum(), LATER_MONTH=pl.col("LATER_MONTH").sum())
    show(counts.sort("COUNTRY"))
    for country, n, _, _, shifted, later in counts.sort("COUNTRY").iter_rows():
        if shifted:
            finding(f"{shifted} of {n} {country} remittance days fall on a weekend or holiday: a "
                    "business-day shift would change them")
        if later:
            finding(f"{later} of {n} {country} payouts were processed in a later month than effective: the month "
                    "of processing would change their remittance day")


# 7. fx ---------------------------------------------------------------------------------------------------------------

def fx_coverage(legacy_dir, rows: pl.DataFrame):
    firsts = exchange_rates(legacy_dir).group_by(CCY="FX_CCY").agg(FIRST_RATE=as_date("FX_RATDT").min())
    with_ccy = rows.with_columns(CCY=pl.col("COUNTRY").replace_strict(TAX_CURRENCY, default=None))
    payouts_before = with_ccy.join(firsts, on="CCY").filter(pl.col("EFFECTIVE").lt(pl.col("FIRST_RATE")))
    premiums = received_premiums(legacy_dir).select(TB_POLNR="PR_POLNR", RECEIVED=as_date("PR_RCVDT"))
    premiums_before = with_ccy.select("TB_POLNR", "COUNTRY", "CCY").unique().join(premiums, on="TB_POLNR").join(
        firsts, on="CCY").filter(pl.col("RECEIVED").lt(pl.col("FIRST_RATE")))
    counts = pl.concat([payouts_before.group_by("COUNTRY", "CCY").agg(PAYOUTS_BEFORE=pl.len()),
                        premiums_before.group_by("COUNTRY", "CCY").agg(PREMIUMS_BEFORE=pl.len())], how="diagonal")
    counts = counts.group_by("COUNTRY", "CCY").agg(pl.all().sum()).sort("COUNTRY")
    show(counts)
    for country, ccy, payouts_n, premiums_n in counts.iter_rows():
        finding(f"{country}: {payouts_n} payouts and {premiums_n} premiums are older than the first {ccy} rate: "
                "their conversion is an assumption")


# 8. separation -------------------------------------------------------------------------------------------------------

def separation(legacy_dir):
    counts = separations(legacy_dir, ["EVENT_TYPE"])
    show(counts)
    best = counts.sort("ERRORS").group_by("COUNTRY", "EVENT_TYPE", maintain_order=True).first()
    for row in best.sort("COUNTRY", "EVENT_TYPE").iter_rows(named=True):
        total = row["hit"] + row["missed"] + row["extra"] + row["rest"]
        verdict = "separates them exactly" if not row["ERRORS"] else f"still misplaces {row['ERRORS']}"
        finding(f"{row['COUNTRY']} event {row['EVENT_TYPE']} ({total} payouts): '{row['CANDIDATE']}' {verdict}")


# 9. trees ------------------------------------------------------------------------------------------------------------

def design(rows: pl.DataFrame) -> tuple[pl.DataFrame, list[str]]:
    """The features of every payout for predicting a booked type: the categories one-hot, the earlier bookings, numbers.

    The booked country (COUNTRY) and the bookings of the payout itself are left out: they are labels.
    """
    earlier = [col for col in rows.columns if col.startswith("BEFORE_")]
    frame = rows.select(*CATEGORIES, *NUMBERS, *earlier).with_columns(
        pl.col(*CATEGORIES).fill_null("?"), pl.col(*NUMBERS, *earlier).cast(pl.Int64).fill_null(-1))
    features = frame.to_dummies(CATEGORIES)
    return features, features.columns


def trees(rows: pl.DataFrame, depth: int):
    labels = [col for col in rows.columns if col.startswith("HAS_") and rows[col].any()]
    for label in labels:
        features, names = design(rows)
        target = rows[label].to_numpy()
        tree = DecisionTreeClassifier(max_depth=depth, min_samples_leaf=3, random_state=0)
        tree.fit(features.to_numpy(), target)
        wrong = rows.filter(pl.Series(tree.predict(features.to_numpy()) != target))
        print(f"\n-- {label.removeprefix('HAS_')}: {int(target.sum())} of {len(target)} payouts booked")
        print(export_text(tree, feature_names=names, show_weights=True))
        used = [names[i] for i in tree.tree_.feature if i >= 0]
        verdict = "explains every payout" if wrong.is_empty() else f"misses {wrong.height}"
        finding(f"{label.removeprefix('HAS_')}: a tree of depth {depth} on {', '.join(dict.fromkeys(used))} "
                f"{verdict}" + ("" if wrong.is_empty() else ", e.g. " + ", ".join(
                    f"{policy}#{event}" for policy, event in wrong.select(EVENT).head(EXAMPLES).iter_rows())))


# 10. changes ---------------------------------------------------------------------------------------------------------

def change_points(rows: pl.DataFrame):
    """The share of the payouts of residents of the tax's country that have the tax, per year, and its jumps."""
    labels = [col for col in rows.columns if col.startswith("HAS_") and rows[col].any()]
    shares = pl.concat([
        rows.filter(pl.col("AD_CNTRY").eq(TAXES.get(label.removeprefix("HAS_")))).group_by("PAYOUT_YEAR").agg(
            TAX=pl.lit(label.removeprefix("HAS_")), PAYOUTS=pl.len(), SHARE=pl.col(label).mean().round(2))
        for label in labels]).sort("TAX", "PAYOUT_YEAR")
    jumps = shares.with_columns(PREV=pl.col("SHARE").shift().over("TAX"),
                                PREV_YEAR=pl.col("PAYOUT_YEAR").shift().over("TAX"),
                                PREV_PAYOUTS=pl.col("PAYOUTS").shift().over("TAX")).filter(
        pl.col("SHARE").sub(pl.col("PREV")).abs().ge(JUMP),
        pl.min_horizontal("PAYOUTS", "PREV_PAYOUTS").ge(MIN_PAYOUTS))
    show(shares.pivot("TAX", index="PAYOUT_YEAR", values="SHARE").sort("PAYOUT_YEAR"))
    for row in jumps.iter_rows(named=True):
        finding(f"{row['TAX']}: the share of residents' payouts with it moves from {row['PREV']} in "
                f"{row['PREV_YEAR']} to {row['SHARE']} in {row['PAYOUT_YEAR']} ({row['PAYOUTS']} payouts)")


SECTIONS = ["codes", "rates", "bookings", "jobs", "eras", "remittance", "fx", "separation", "trees", "changes"]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--section", choices=SECTIONS, action="append", help="run only these sections")
    parser.add_argument("--depth", type=int, default=3, help="depth of the decision trees")
    args = parser.parse_args()
    legacy_dir, chosen = str(LEGACY), args.section or SECTIONS
    rows = payout_features(legacy_dir) if set(chosen) & {"eras", "remittance", "fx", "trees", "changes"} else None
    runs = {"codes": lambda: codes(legacy_dir), "rates": lambda: rate_timeline(legacy_dir),
            "bookings": lambda: booking_timeline(legacy_dir), "jobs": lambda: jobs(legacy_dir),
            "eras": lambda: eras(rows), "remittance": lambda: remittance(rows),
            "fx": lambda: fx_coverage(legacy_dir, rows), "separation": lambda: separation(legacy_dir),
            "trees": lambda: trees(rows, args.depth), "changes": lambda: change_points(rows)}
    for number, name in enumerate(SECTIONS, 1):
        if name in chosen:
            print(f"\n== {number}. {name} {'=' * 100}")
            runs[name]()


if __name__ == "__main__":
    main()
