"""t2: the projection of the offer, month by month from the start date to maturity.

From the story (tools/detective/llm/005-t2-story.md), every month:
1. the premium due in that month comes in, less the entry charge (NRENTC of the broker tier)
2. the admin fee CG_ADMFEE goes out
3. the management charge goes out: a twelfth of the yearly rate on the value
4. the risk charge goes out: sum at risk x death probability of the age / 12 x (1 + loading) x smoker factor
5. the value grows by a twelfth of the illustration rate NRILLU
with the parameters valid on the application date of the policy as offered (its first version).

Found in the data (tools/detective/llm/006-t2-findings.md):
- one pot: the management charge is CG_AMCP2 on the whole value (r2-search-regular/S1, after r1/T1: every
  regular premium was wrong with two pots)
- the system that made the offer decides the conventions: the old one before the system conversion (event 800),
  Neuron NG from that day on, judged on the application date (r3-search-era/S1, r6-search-boundary/S1, after
  r1/T3, T4: a split just after the conversion)
  - rounding: cut off by the old system, half up by Neuron NG (r2-search-old/S1, r1-search-single/S1)
  - entry age: days / 365 rounded half up by the old system, the nearest birthday by Neuron NG
    (r5-search-era-age/S1, after r4/T1)
- the growth in decimal arithmetic with 28 significant digits (r1-search-single/S1)
- option A: the sum at risk is 1 % of the value, kept exact; the risk charge is rounded once
  (r4-search-risk/S1, after r3/T1)
- an impossible birth date (31 April) is read as the last day of its month (r5-search-age/S1)

The choices stay parameters of `projection`, so the search can test them again on new data:
- `parameter_day`: the date whose parameters count (PH_APPDT application, PH_BEGDT start)
- `pots`: "one" (everything at CG_AMCP2) or "two" (the premiums of the first PD_INIMON months at CG_AMCP1)
- `age`: the age at the start date by a convention of `entry_age`, plus the completed policy years
- `rounding`: every amount rounded "half_up" to the cent or cut off ("down")
- `era_day`: the date column that tells which system made the offer, and `boundary` the system of the conversion
  day itself ("old" or "new"); `age` and `rounding` take one convention or a pair (old system, Neuron NG)
- `growth`: "fraction" (value x (12 + rate) / 12, rounded once) or "decimal<digits>" (the factor 1 + rate / 12
  and the product with that many significant digits)
- `at_risk` and `charge`: how 1 % of the value is kept and where the risk charge is rounded (`risk_charge`)
- `impossible`: how an impossible birth date is read (`legacy.lenient_date`)
"""
import decimal
import functools
import math

import polars as pl

from eras import by_era, half_up, new_system
from legacy import lenient_date, raw, table, version_on
from money import RATE_UNIT, rounded

PERCENT = 100
YEAR = 12  # months
MONTHLY = math.prod((YEAR, RATE_UNIT))  # a yearly rate in millionths, applied for one month
CUBED = pow(RATE_UNIT, 3)  # three rates multiplied
EVERY = {"J": 12, "H": 6, "Q": 3, "M": 1, "E": 0}  # FREQ: months between premiums, 0 for a single premium
SEXES = {"M": "1", "W": "2"}  # tariff key position 3 -> MO_SEX; U (unisex) takes the sex of the person
SMOKER = "J"  # PS_SMOKE: J (ja) or N
MODES = {True: decimal.ROUND_HALF_UP, False: decimal.ROUND_DOWN}


def people(legacy_dir, impossible: str = "clamp") -> pl.DataFrame:
    """The persons with BIRTH: the birth date with an impossible day read by `impossible`."""
    births = raw(legacy_dir, "NRPERS").select(pl.col("PS_PERNR"), BIRTH=lenient_date("PS_BIRTH", impossible))
    return table(legacy_dir, "NRPERS").join(births, on="PS_PERNR")


def offered_policies(legacy_dir, impossible: str = "clamp") -> pl.DataFrame:
    """The first version of every policy (the one offered), with its risk, person (`people`), product and
    broker."""
    first = table(legacy_dir, "NRPOLH").sort("PH_VRSNR").unique("PH_POLNR", keep="first")
    risks = first.join(table(legacy_dir, "NRRISK"), left_on="PH_POLNR", right_on="RK_POLNR")
    insured = risks.join(people(legacy_dir, impossible), left_on="RK_PERNR", right_on="PS_PERNR")
    products = insured.join(table(legacy_dir, "NRPROD"), left_on="PH_PRDCD", right_on="PD_PRDCD")
    return products.join(table(legacy_dir, "NRBROK"), left_on="PH_BRKNR", right_on="BR_BRKNR", how="left")


def with_parameters(legacy_dir, policies: pl.DataFrame, day: str) -> pl.DataFrame:
    """`policies` with the charges, entry charge and illustration rate valid on the date column `day`."""
    tariff = policies.with_columns(TARGEN=pl.col("RK_TARKEY").str.slice(3, 2), TARFAM=pl.col("PD_TARFAM"))
    charged = version_on(tariff, table(legacy_dir, "NRCHRG"), {"TARFAM": "CG_TARFAM", "TARGEN": "CG_TARGEN"}, day,
                         "CG_VLDFR")
    entry = version_on(charged, table(legacy_dir, "NRENTC"), {"BR_TIER": "EC_TIER"}, day, "EC_VLDFR")
    rates = table(legacy_dir, "NRILLU").with_columns(ALL=pl.lit(1))
    return version_on(entry.with_columns(ALL=pl.lit(1)), rates, {"ALL": "ALL"}, day, "IL_VLDFR")


def completed_years(start: pl.Expr, end: pl.Expr) -> pl.Expr:
    """Whole years from `start` to `end`: the birthday in the year of `end` counts once it is reached."""
    anniversary = start.dt.offset_by(pl.format("{}y", end.dt.year().sub(start.dt.year())))
    return end.dt.year().sub(start.dt.year()).sub(anniversary.gt(end).cast(pl.Int64))


def entry_age(age: str, day: str = "PH_BEGDT") -> pl.Expr:
    """The age on the date column `day` (the start date) by one of the usual conventions:

    completed years; the nearest birthday (completed years half a year later); the difference of the calendar
    years; days / 365 or days / 365.25 cut off ("days365", "days365.25") or rounded half up ("nearest_days365",
    "nearest_days365.25"); months / 12 rounded half up.
    """
    birth, begin = pl.col("BIRTH"), pl.col(day)
    days = begin.sub(birth).dt.total_days()
    months = begin.dt.year().sub(birth.dt.year()).mul(YEAR).add(begin.dt.month().sub(birth.dt.month())).sub(
        begin.dt.day().lt(birth.dt.day()).cast(pl.Int64))
    conventions = {"completed": completed_years(birth, begin),
                   "nearest": completed_years(birth, begin.dt.offset_by("6mo")),
                   "calendar": begin.dt.year().sub(birth.dt.year()),
                   "days365": days.floordiv(365), "days365.25": days.mul(4).floordiv(1461),
                   "nearest_days365": rounded(days, 365, True), "nearest_days365.25": rounded(days.mul(4), 1461, True),
                   "months": rounded(months, YEAR, True)}
    return conventions[age]


def mortality_sex() -> pl.Expr:
    """MO_SEX of the tariff: M -> 1, W -> 2, U -> the sex of the person."""
    basis = pl.col("RK_TARKEY").str.slice(2, 1)
    return basis.replace_strict(SEXES, default=None).fill_null(pl.col("PS_SEX"))


@functools.cache
def factor(rate: int, digits: int) -> decimal.Decimal:
    """1 + rate / 12 (rate in millionths) with `digits` significant digits."""
    context = decimal.Context(prec=digits)
    return context.add(1, context.divide(rate, MONTHLY))


def decimal_growth(rows: pl.Series, digits: int) -> pl.Series:
    """The VALUE (cents) of `rows` grown by a month at IL_RATE in decimal arithmetic with `digits` significant
    digits, rounded half up or cut off by HALF_UP."""
    context = decimal.Context(prec=digits)
    columns = (rows.struct.field(name).to_list() for name in ("VALUE", "IL_RATE", "HALF_UP"))
    grown = [int(context.multiply(value, factor(rate, digits)).quantize(1, rounding=MODES[up]))
             for value, rate, up in zip(*columns, strict=True)]
    return pl.Series(grown, dtype=pl.Int64)


def growth_of(growth: str) -> pl.Expr:
    """VALUE after a month of growth at IL_RATE."""
    match growth:
        case "fraction":
            return rounded(pl.col("VALUE").mul(pl.col("IL_RATE").add(MONTHLY)), MONTHLY, pl.col("HALF_UP"))
    digits = int(growth.removeprefix("decimal"))
    return pl.struct("VALUE", "IL_RATE", "HALF_UP").map_batches(lambda rows: decimal_growth(rows, digits),
                                                                return_dtype=pl.Int64)


def sum_at_risk(at_risk: str) -> pl.Expr:
    """The part of the death benefit above the value in hundredths of a cent: A 1 % of the value, B the sum insured
    less the value, C the sum insured. `at_risk` is how 1 % of the value is kept: "exact", or rounded to the cent
    by the policy's rounding ("cent") or half up ("cent_half_up")."""
    option = pl.col("RK_TARKEY").str.slice(6, 1)
    percent = {"exact": pl.col("VALUE"),
               "cent": rounded(pl.col("VALUE"), PERCENT, pl.col("HALF_UP")).mul(PERCENT),
               "cent_half_up": rounded(pl.col("VALUE"), PERCENT, True).mul(PERCENT)}[at_risk]
    return (pl.when(option.eq("A")).then(percent)
            .when(option.eq("B")).then(pl.col("RK_SUMIN").sub(pl.col("VALUE")).clip(0).mul(PERCENT))
            .otherwise(pl.col("RK_SUMIN").mul(PERCENT))).cast(pl.Int128)


def step(numerator: pl.Expr, *factors: int) -> pl.Expr:
    """One rounding of the risk charge: `numerator` / the product of `factors`, by the policy's rounding."""
    return rounded(numerator, pl.lit(math.prod(factors), pl.Int128), pl.col("HALF_UP"))


def risk_charge(at_risk: str, charge: str) -> pl.Expr:
    """Sum at risk x death probability / 12 x (1 + loading) x smoker factor, in cents. `charge` is where it is
    rounded: "once" at the end; "yearly" the charge of a year, then its twelfth; "steps" after every factor; or
    "rate<digits>" the monthly rate (probability, loading and smoker factor) to that many decimals, then the
    charge."""
    smoker = pl.when(pl.col("PS_SMOKE").eq(SMOKER)).then(pl.col("CG_SMKFAC")).otherwise(RATE_UNIT)
    loading = pl.col("RK_LOAD").add(RATE_UNIT)
    units, rate = sum_at_risk(at_risk), pl.col("MO_QX").cast(pl.Int128).mul(loading).mul(smoker)
    match charge:
        case "once":
            return step(units.mul(rate), YEAR, PERCENT, CUBED).cast(pl.Int64)
        case "yearly":
            return step(step(units.mul(rate), PERCENT, CUBED), YEAR).cast(pl.Int64)
        case "steps":
            probable = step(units.mul(pl.col("MO_QX")), PERCENT, RATE_UNIT)
            return step(step(step(probable.mul(loading), RATE_UNIT).mul(smoker), RATE_UNIT), YEAR).cast(pl.Int64)
    decimals = pow(10, int(charge.removeprefix("rate")))
    monthly = step(rate.mul(decimals), YEAR, CUBED)
    return step(units.mul(monthly), PERCENT, decimals).cast(pl.Int64)


def start(legacy_dir, parameter_day: str, age, rounding, era_day: str, boundary: str,
          impossible: str) -> pl.DataFrame:
    """One row per policy with everything the projection needs and VALUE = 0."""
    offered = offered_policies(legacy_dir, impossible).with_columns(NEW_SYSTEM=new_system(legacy_dir, era_day, boundary))
    policies = with_parameters(legacy_dir, offered, parameter_day)
    months = pl.col("PH_ENDDT").dt.year().sub(pl.col("PH_BEGDT").dt.year()).mul(YEAR).add(
        pl.col("PH_ENDDT").dt.month().sub(pl.col("PH_BEGDT").dt.month()))
    return policies.with_columns(MONTHS=months, EVERY=pl.col("PH_FREQ").replace_strict(EVERY, return_dtype=pl.Int64),
                                 ENTRY_AGE=by_era(age, entry_age), MO_TABID=pl.col("CG_MORTTB"),
                                 MO_SEX=mortality_sex(), HALF_UP=by_era(rounding, half_up),
                                 VALUE=pl.lit(0, pl.Int64), POT1=pl.lit(0, pl.Int64))


def month(state: pl.DataFrame, number: int, mortality: pl.DataFrame, pots: str, growth: str, at_risk: str,
          charge: str) -> pl.DataFrame:
    """The state after projection month `number` (0 = the first month)."""
    single = pl.col("EVERY").eq(0)
    due = pl.when(single).then(pl.lit(number).eq(0)).otherwise(pl.lit(number).mod(pl.col("EVERY")).eq(0))
    premium = pl.when(due).then(pl.col("PH_PREMI")).otherwise(0)
    entry = rounded(premium.mul(pl.col("EC_RATE")), RATE_UNIT, pl.col("HALF_UP"))
    initial = pl.lit(pots).eq("two").and_(pl.lit(number).lt(pl.col("PD_INIMON")))
    paid = state.with_columns(VALUE=pl.col("VALUE").add(premium).sub(entry),
                              POT1=pl.col("POT1").add(pl.when(initial).then(premium.sub(entry)).otherwise(0)))
    fee = paid.with_columns(VALUE=pl.col("VALUE").sub(pl.col("CG_ADMFEE")))
    pot1 = pl.min_horizontal("POT1", "VALUE").clip(0)
    yearly = pot1.mul(pl.col("CG_AMCP1")).add(pl.col("VALUE").sub(pot1).clip(0).mul(pl.col("CG_AMCP2")))
    managed = fee.with_columns(VALUE=pl.col("VALUE").sub(rounded(yearly, MONTHLY, pl.col("HALF_UP"))), POT1=pot1)
    aged = managed.with_columns(MO_AGE=pl.col("ENTRY_AGE").add(pl.lit(number).floordiv(YEAR))).join(
        mortality, on=["MO_TABID", "MO_SEX", "MO_AGE"], how="left")
    risk = risk_charge(at_risk, charge).fill_null(0)
    return aged.with_columns(VALUE=pl.col("VALUE").sub(risk)).drop("MO_AGE", "MO_QX").with_columns(
        VALUE=growth_of(growth))


def projection(legacy_dir, parameter_day: str = "PH_APPDT", pots: str = "one", age=("nearest_days365", "nearest"),
               rounding=("down", "half_up"), era_day: str = "PH_APPDT", boundary: str = "new",
               growth: str = "decimal28", at_risk: str = "exact", charge: str = "once",
               impossible: str = "clamp") -> pl.DataFrame:
    """policy_id, month (1 = the first), value and MATURITY: the value at the end of every policy year and at
    maturity."""
    state = start(legacy_dir, parameter_day, age, rounding, era_day, boundary, impossible)
    mortality = table(legacy_dir, "NRMORT")
    rows = []
    for count, number in enumerate(range(state["MONTHS"].max()), 1):
        state = month(state.filter(pl.col("MONTHS").gt(number)), number, mortality, pots, growth, at_risk, charge)
        ends = state.with_columns(MATURITY=pl.col("MONTHS").eq(count)).filter(
            pl.lit(count).mod(YEAR).eq(0).or_(pl.col("MATURITY")))
        rows.append(ends.select(policy_id="PH_POLNR", month=pl.lit(count), value="VALUE", MATURITY="MATURITY"))
    return pl.concat(rows)


def projected_years(legacy_dir, **conventions) -> pl.DataFrame:
    """policy_id, policy_year and value: the projected value at the end of every policy year."""
    years = projection(legacy_dir, **conventions).filter(pl.col("month").mod(YEAR).eq(0))
    return years.select("policy_id", policy_year=pl.col("month").floordiv(YEAR), value="value")


def maturity_values(legacy_dir, **conventions) -> pl.DataFrame:
    """policy_id and maturity_value: the projected value at maturity."""
    return projection(legacy_dir, **conventions).filter("MATURITY").select("policy_id", maturity_value="value")
