"""t3: the monthly charge run, which takes the admin fee, the management charge and the risk charge by cancelling
units in every fund and pot (the task text, tools/detective/llm/009-t3-charges-story.md).

A run gets the units held before it (UNITS per fund and pot of a policy, on the run date RUN) and gives one
booking per charge, fund and pot:
- the value of a fund and pot: its units at the redemption price (the last price on or before the run date), in
  the policy currency at the exchange rate of the run date
- ADM: the admin fee CG_ADMFEE, shared between the funds and pots by value
- AMC: a twelfth of the yearly management charge of the pot (CG_AMCP1, CG_AMCP2, or an individual AMC rate while
  it is valid) on the value
- RSK: the risk charge of the month on the sum at risk of the whole value (`projection.sum_at_risk`), with the
  death probability of the age, the loading and the smoker factor, shared by value
The units cancelled are the amount at the redemption price.

The choices stay parameters of `charge_run`:
- `parameter_day`: the date column whose tariff counts
- `rounding`: "half_up" or "down", or a pair (old system, Neuron NG) by the run date (`eras`)
- `remainder`: where the cents go that the rounded shares of the admin fee miss: nowhere ("none"), to the fund
  and pot with the largest value ("largest"), the first or the last in the order of fund and pot ("first",
  "last"), or one cent each to the largest remainders of shares cut off ("hamilton")
- `accrual`: the part of the yearly management charge for a run: a twelfth ("month"), or the days since the
  same day a month earlier ("days360", "days365") or since the previous monthly anniversary of the start date
  ("anniversary360", "anniversary365") over 360 or 365; or a pair (old system, Neuron NG)
- `conversion`: how an amount becomes units (`premiums.units_of`)
- `risk_age`: the age convention of `projection.entry_age`, or a pair (old system, Neuron NG), and `age_basis`
  the age it is taken at: on the run date ("attained") or at the start plus the completed policy years ("policy");
  `age_era_day` is the date that tells which system's age convention counts
- `risk_accrual`: the part of the yearly risk charge for a run, like `accrual`
- `risk_value`: the value the risk charge is reckoned and shared on: before the run ("before") or after its
  admin fee and management charge ("after")
- `valuation`: the value in the policy currency with the exchange rate rounded to millionths ("rate") or exact
- `valued`: the value of a fund and pot kept in cents ("cents") or in millionths of a cent ("micro")
- `limit`: what a run takes when the value runs out: every charge in full ("none"); the admin fee no more
  than the value and the risk charge no more than what the admin fee and the management charge left ("value");
  or also the management charge no more than what the admin fee left ("all")
- `booked`: the charges that become bookings: every amount but 0 ("nonzero"), or only the positive ones
  ("positive", a share that the rounding of the others pushed below 0 is not taken back)
"""
import polars as pl

from eras import by_era, half_up, new_system
from legacy import table, version_on
from market import price_on, rate_on
from money import RATE_UNIT, rounded
from premiums import units_of
from projection import CUBED, PERCENT, completed_years, entry_age, mortality_sex, people, sum_at_risk

UNIT_CENTS = 10_000  # millionths of a unit per cent
SCALES = {"cents": 1, "micro": RATE_UNIT}  # the parts of a cent that a value keeps
MANAGEMENT = "AMC"  # FEETP of a management charge agreement
POT_RATES = {"1": "CG_AMCP1", "2": "CG_AMCP2"}
NEEDED = ["NEW_SYSTEM", "HALF_UP", "PH_BEGDT", "CG_ADMFEE", "CG_AMCP1", "CG_AMCP2", "AG_RATE", "BK_PRICE", "BK_PRCDT",
          "POLICY_FX", "FUND_FX", "BK_FXRAT", "RK_TARKEY", "RK_SUMIN", "RK_LOAD", "PS_SMOKE", "CG_SMKFAC", "MO_QX"]


def with_policy(legacy_dir, held: pl.DataFrame, parameter_day: str) -> pl.DataFrame:
    """`held` with the policy version, risk, person, product and tariff valid on the run date, and the individual
    management charge rate AG_RATE where one is valid."""
    policies = version_on(held, table(legacy_dir, "NRPOLH"), {"BK_POLNR": "PH_POLNR"}, "RUN", "PH_VRSNR")
    risks = policies.join(table(legacy_dir, "NRRISK"), left_on="BK_POLNR", right_on="RK_POLNR")
    insured = risks.join(people(legacy_dir), left_on="RK_PERNR", right_on="PS_PERNR")
    products = insured.join(table(legacy_dir, "NRPROD"), left_on="PH_PRDCD", right_on="PD_PRDCD")
    tariff = products.with_columns(TARGEN=pl.col("RK_TARKEY").str.slice(3, 2), TARFAM=pl.col("PD_TARFAM"))
    charged = version_on(tariff, table(legacy_dir, "NRCHRG"), {"TARFAM": "CG_TARFAM", "TARGEN": "CG_TARGEN"},
                         parameter_day, "CG_VLDFR")
    agreements = table(legacy_dir, "NRAGRE").filter(pl.col("AG_FEETP").eq(MANAGEMENT))
    return version_on(charged, agreements, {"BK_POLNR": "AG_POLNR"}, "RUN", "AG_VLDFR")


def priced(legacy_dir, rows: pl.DataFrame) -> pl.DataFrame:
    """`rows` with BK_PRICE and BK_PRCDT, the redemption price of the run date, and POLICY_FX, FUND_FX and
    BK_FXRAT, the exchange rates of the run date."""
    funds = rows.join(table(legacy_dir, "NRFUND").select("FD_FNDID", "FD_CCY"), left_on="BK_FNDID",
                      right_on="FD_FNDID")
    bid = price_on(legacy_dir, funds, "BK_FNDID", "RUN").rename({"FP_BIDPR": "BK_PRICE", "FP_PRCDT": "BK_PRCDT"})
    exchanged = rate_on(legacy_dir, rate_on(legacy_dir, bid, "PH_CCY", "RUN", "POLICY_FX"), "FD_CCY", "RUN",
                        "FUND_FX")
    return exchanged.with_columns(BK_FXRAT=rounded(pl.col("POLICY_FX").mul(RATE_UNIT), pl.col("FUND_FX"), True))


def value_of(valued: str, valuation: str) -> pl.Expr:
    """The value of UNITS of a fund and pot in policy cents, kept in parts of a cent by `valued`."""
    worth = pl.col("UNITS").cast(pl.Int128).mul(pl.col("BK_PRICE")).mul(SCALES[valued])
    rates = {"rate": (worth, pl.col("BK_FXRAT").cast(pl.Int128).mul(UNIT_CENTS)),
             "exact": (worth.mul(pl.col("FUND_FX")), pl.col("POLICY_FX").cast(pl.Int128).mul(UNIT_CENTS).mul(RATE_UNIT))}
    return rounded(*rates[valuation], pl.col("HALF_UP")).cast(pl.Int64)


def management_rate() -> pl.Expr:
    """The yearly management charge of the pot BK_POTCD: an individual rate, else the tariff's."""
    tariff = pl.col("BK_POTCD").replace_strict(POT_RATES, return_dtype=pl.String)
    return pl.coalesce("AG_RATE", pl.when(tariff.eq("CG_AMCP1")).then(pl.col("CG_AMCP1")).otherwise(pl.col("CG_AMCP2")))


def shared(total: pl.Expr, remainder: str, by: str = "VALUE") -> pl.Expr:
    """`total` (cents, the same in every row of a run) shared between the rows of a run by the column `by` (see
    `remainder`)."""
    run = ["BK_POLNR", "RUN"]
    exact = total.cast(pl.Int128).mul(pl.col(by))
    whole = pl.col(by).sum().over(run).cast(pl.Int128)
    shares = rounded(exact, whole, pl.col("HALF_UP"))
    missing = total.sub(shares.sum().over(run))
    order = pl.struct("BK_FNDID", "BK_POTCD").rank("ordinal").over(run)
    chosen = {"largest": pl.struct(pl.col(by).neg(), "BK_FNDID", "BK_POTCD").rank("ordinal").over(run).eq(1),
              "first": order.eq(1), "last": order.eq(pl.len().over(run)), "none": pl.lit(False)}
    match remainder:
        case "hamilton":
            cut = exact.floordiv(whole)
            behind = total.sub(cut.sum().over(run))
            rank = pl.struct(exact.mod(whole).cast(pl.Int64).neg(), "BK_FNDID", "BK_POTCD").rank("ordinal").over(run)
            return cut.add(rank.le(behind).cast(pl.Int128)).cast(pl.Int64)
    return shares.add(pl.when(chosen[remainder]).then(missing).otherwise(0)).cast(pl.Int64)


def risk_age_of(age: str, age_basis: str) -> pl.Expr:
    """The age of the insured person for the risk charge of a run (see `risk_age` and `age_basis`)."""
    bases = {"attained": entry_age(age, "RUN"),
             "policy": entry_age(age).add(completed_years(pl.col("PH_BEGDT"), pl.col("RUN")))}
    return bases[age_basis]


def with_mortality(legacy_dir, rows: pl.DataFrame, risk_age, age_basis: str, age_era_day: str) -> pl.DataFrame:
    """`rows` with MO_QX, the death probability of the insured person's age for the run."""
    systems = rows.with_columns(AGE_SYSTEM=new_system(legacy_dir, age_era_day))
    aged = systems.with_columns(MO_TABID=pl.col("CG_MORTTB"), MO_SEX=mortality_sex(),
                                MO_AGE=by_era(risk_age, lambda age: risk_age_of(age, age_basis), "AGE_SYSTEM"))
    return aged.join(table(legacy_dir, "NRMORT"), on=["MO_TABID", "MO_SEX", "MO_AGE"], how="left")


def with_risk(values: pl.DataFrame, risk_accrual) -> pl.DataFrame:
    """`values` with RISK: the risk charge of the run in cents, on the sum at risk of the whole RISK_BASE."""
    run = ["BK_POLNR", "RUN"]
    whole = values.with_columns(OWN=pl.col("VALUE"), VALUE=pl.col("RISK_BASE").sum().over(run))
    smoker = pl.when(pl.col("PS_SMOKE").eq("J")).then(pl.col("CG_SMKFAC")).otherwise(RATE_UNIT)
    yearly = sum_at_risk("exact").mul(pl.col("MO_QX")).mul(pl.col("RK_LOAD").add(RATE_UNIT)).mul(smoker)
    part = by_era(risk_accrual, lambda name: accrued(name)[0]), by_era(risk_accrual, lambda name: accrued(name)[1])
    risk = rounded(yearly.mul(part[0]), part[1].cast(pl.Int128).mul(PERCENT).mul(CUBED), pl.col("HALF_UP"))
    return whole.with_columns(RISK=risk.fill_null(0).cast(pl.Int64), VALUE=pl.col("OWN")).drop("OWN")


def accrued(accrual: str) -> tuple[pl.Expr, pl.Expr]:
    """(numerator, denominator) of the part of a year that one run charges (see `accrual`)."""
    days = pl.col("RUN").sub(pl.col("RUN").dt.offset_by("-1mo")).dt.total_days()
    begin, run = pl.col("PH_BEGDT"), pl.col("RUN")
    months = run.dt.year().sub(begin.dt.year()).mul(12).add(run.dt.month().sub(begin.dt.month()))
    previous = begin.dt.offset_by(pl.format("{}mo", months.sub(1)))
    anniversary = run.sub(previous).dt.total_days()
    parts = {"month": (pl.lit(1), pl.lit(12)), "days360": (days, pl.lit(360)), "days365": (days, pl.lit(365)),
             "anniversary360": (anniversary, pl.lit(360)), "anniversary365": (anniversary, pl.lit(365))}
    return parts[accrual]


def run_rows(legacy_dir, rows: pl.DataFrame, parameter_day: str = "RUN", rounding=("down", "half_up"),
             risk_age=("nearest_days365", "nearest"), age_basis: str = "policy",
             age_era_day: str = "PH_APPDT") -> pl.DataFrame:
    """`rows` (BK_POLNR, RUN, BK_FNDID, BK_POTCD) with all that a run needs and that does not depend on the units:
    the system and its rounding, the policy and its tariff, the price and the exchange rates, the death
    probability."""
    systems = rows.with_columns(NEW_SYSTEM=new_system(legacy_dir, "RUN")).with_columns(HALF_UP=by_era(rounding,
                                                                                                        half_up))
    with_prices = priced(legacy_dir, with_policy(legacy_dir, systems, parameter_day))
    return with_mortality(legacy_dir, with_prices, risk_age, age_basis, age_era_day).select(*rows.columns, *NEEDED)


def charges_of(rows: pl.DataFrame, valued: str = "cents", accrual=("anniversary360", "month"),
               remainder: str = "largest", conversion: str = "exact", valuation: str = "exact", risk_accrual="month",
               risk_value: str = "after", booked: str = "positive", limit: str = "value") -> pl.DataFrame:
    """BK_POLNR, BK_FNDID, BK_POTCD, BK_BKTYP, BK_TRDDT, BK_PRCDT, BK_AMTPC, BK_FXRAT, BK_PRICE and BK_UNITS of the
    ADM, AMC and RSK bookings of the runs of `rows` (`run_rows` with UNITS, the units held before the run)."""
    valued_rows = rows.with_columns(VALUE=value_of(valued, valuation))
    run = ["BK_POLNR", "RUN"]
    left = pl.col("VALUE").sum().over(run).floordiv(SCALES[valued])
    fees = {"none": pl.col("CG_ADMFEE"), "value": pl.min_horizontal("CG_ADMFEE", left)}
    fee = shared(fees.get(limit, fees["value"]), remainder)
    part = by_era(accrual, lambda name: accrued(name)[0]), by_era(accrual, lambda name: accrued(name)[1])
    management = rounded(pl.col("VALUE").cast(pl.Int128).mul(management_rate()).mul(part[0]),
                         part[1].cast(pl.Int128).mul(RATE_UNIT).mul(SCALES[valued]), pl.col("HALF_UP"))
    after_fee = pl.col("VALUE").floordiv(SCALES[valued]).sub(pl.col("ADM")).clip(0)
    managed = {"all": pl.min_horizontal("AMC", after_fee)}
    charged = valued_rows.with_columns(ADM=fee, AMC=management.cast(pl.Int64)).with_columns(
        AMC=managed.get(limit, pl.col("AMC")))
    bases = {"before": pl.col("VALUE"), "after": pl.col("VALUE").sub(pl.col("ADM")).sub(pl.col("AMC"))}
    values = with_risk(charged.with_columns(RISK_BASE=bases[risk_value]), risk_accrual)
    risks = {"none": pl.col("RISK"), "value": pl.min_horizontal("RISK", pl.col("RISK_BASE").sum().over(run).clip(0))}
    charges = values.with_columns(RSK=shared(risks.get(limit, risks["value"]), remainder, "RISK_BASE")).unpivot(
        ["ADM", "AMC", "RSK"], index=values.columns, variable_name="BK_BKTYP", value_name="BK_AMTPC")
    kept = {"nonzero": pl.col("BK_AMTPC").ne(0), "positive": pl.col("BK_AMTPC").gt(0)}
    return charges.filter(kept[booked]).select(
        "BK_POLNR", "BK_FNDID", "BK_POTCD", "BK_BKTYP", BK_TRDDT="RUN", BK_PRCDT="BK_PRCDT", BK_AMTPC="BK_AMTPC",
        BK_FXRAT="BK_FXRAT", BK_PRICE="BK_PRICE", BK_UNITS=units_of(conversion).neg())


def charge_run(legacy_dir, held: pl.DataFrame, parameter_day: str = "RUN", rounding=("down", "half_up"),
               risk_age=("nearest_days365", "nearest"), age_basis: str = "policy", age_era_day: str = "PH_APPDT",
               **conventions) -> pl.DataFrame:
    """The bookings of `charges_of` for the runs in `held` (BK_POLNR, RUN, BK_FNDID, BK_POTCD, UNITS), with the
    other `conventions` of `charges_of`."""
    rows = run_rows(legacy_dir, held, parameter_day, rounding, risk_age, age_basis, age_era_day)
    return charges_of(rows, **conventions)
