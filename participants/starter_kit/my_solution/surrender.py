"""t3: the surrender value of a policy on a valuation date (tools/detective/llm/011-t3-runs-story.md).

From the task text: the units (`accounting.holdings`) are valued at the redemption price, the last price on or
before the valuation date, in the policy currency; that is the policy value. The surrender value is the policy
value less the surrender penalty: the rate of the product's scale (PD_SRPSCL) for the completed policy years
(NRSURR), none in a waiver period (NRWAIV). Surrendered policies and policies of insured persons who died are
worth 0.

The choices stay parameters of `surrender_values`:
- `rounding`: the cents of the value and of the penalty, "half_up" or "down", or a pair (old system, Neuron NG)
  by the valuation date (`eras`)
- `summed`: the value of each fund and pot rounded to the cent and then added ("each"), or added in millionths
  of a cent and rounded once ("once")
- `valuation`: the exchange rate rounded to millionths ("rate") or exact (`charges.value_of`)
- `penalty`: the cents of the penalty: rounded like the value ("value"), "half_up", "down" or "up", or the rest
  of the value at (1 - penalty rate) rounded like the value ("net"); or a pair (old system, Neuron NG)
- `floor`: a surrender value below 0 (of a value that the charges used up) paid as 0 ("zero") or kept ("none")
- `ended`: a policy is worth 0 from the day of its surrender or death claim ("on") or from the day after it
  ("after"), or only by its units ("units", the bookings of the claim sell them)
"""
import polars as pl

from charges import SCALES, value_of
from eras import by_era, half_up, new_system
from legacy import table, version_on
from market import price_on, rate_on
from money import RATE_UNIT, rounded
from projection import completed_years
from runs import ends

ENDED = {"on": "le", "after": "lt"}
FLOORS = {"zero": lambda value: value.clip(0), "none": lambda value: value}


def valued(legacy_dir, held: pl.DataFrame, rounding, summed: str, valuation: str) -> pl.DataFrame:
    """BK_POLNR, VALUATION and POLICY_VALUE in cents of the units BOOKED per fund and pot in `held`."""
    policies = version_on(held, table(legacy_dir, "NRPOLH"), {"BK_POLNR": "PH_POLNR"}, None, "PH_VRSNR")
    funds = policies.join(table(legacy_dir, "NRFUND").select("FD_FNDID", "FD_CCY"), left_on="BK_FNDID",
                          right_on="FD_FNDID")
    bid = price_on(legacy_dir, funds, "BK_FNDID", "VALUATION").rename({"FP_BIDPR": "BK_PRICE"})
    exchanged = rate_on(legacy_dir, rate_on(legacy_dir, bid, "PH_CCY", "VALUATION", "POLICY_FX"), "FD_CCY",
                        "VALUATION", "FUND_FX")
    systems = exchanged.with_columns(NEW_SYSTEM=new_system(legacy_dir, "VALUATION")).with_columns(
        HALF_UP=by_era(rounding, half_up), UNITS=pl.col("BOOKED"),
        BK_FXRAT=rounded(pl.col("POLICY_FX").mul(RATE_UNIT), pl.col("FUND_FX"), True))
    scales = {"each": "cents", "once": "micro"}
    parts = systems.with_columns(VALUE=value_of(scales[summed], valuation))
    summed_up = parts.group_by("BK_POLNR", "VALUATION").agg(pl.col("VALUE").sum(), pl.col("HALF_UP", "NEW_SYSTEM").first())
    whole = rounded(pl.col("VALUE"), SCALES[scales[summed]], pl.col("HALF_UP"))
    return summed_up.select("BK_POLNR", "VALUATION", "HALF_UP", "NEW_SYSTEM", POLICY_VALUE=whole)


def penalty_rates(legacy_dir, values: pl.DataFrame) -> pl.DataFrame:
    """`values` with SR_RATE: the surrender penalty rate of the completed policy years on the valuation date, 0
    beyond the scale and in a waiver period."""
    policies = version_on(values, table(legacy_dir, "NRPOLH"), {"BK_POLNR": "PH_POLNR"}, None, "PH_VRSNR")
    products = policies.join(table(legacy_dir, "NRPROD"), left_on="PH_PRDCD", right_on="PD_PRDCD")
    years = products.with_columns(SR_SCALE=pl.col("PD_SRPSCL"),
                                  SR_YEAR=completed_years(pl.col("PH_BEGDT"), pl.col("VALUATION")))
    rated = years.join(table(legacy_dir, "NRSURR"), on=["SR_SCALE", "SR_YEAR"], how="left")
    periods = table(legacy_dir, "NRWAIV").select("WV_VLDFR", "WV_VLDTO").iter_rows()
    waived = pl.any_horizontal([pl.col("VALUATION").is_between(start, end) for start, end in periods])
    return rated.with_columns(SR_RATE=pl.when(waived).then(0).otherwise(pl.col("SR_RATE").fill_null(0)))

def penalty_of(penalty) -> pl.Expr:
    """The surrender penalty in cents: POLICY_VALUE at SR_RATE, rounded by `penalty` (see the module docstring)."""
    exact = pl.col("POLICY_VALUE").mul(pl.col("SR_RATE"))
    modes = {"value": rounded(exact, RATE_UNIT, pl.col("HALF_UP")), "half_up": rounded(exact, RATE_UNIT, True),
             "down": rounded(exact, RATE_UNIT, False), "up": exact.neg().floordiv(RATE_UNIT).neg(),
             "net": pl.col("POLICY_VALUE").sub(rounded(pl.col("POLICY_VALUE").mul(pl.lit(RATE_UNIT).sub(pl.col("SR_RATE"))),
                                                       RATE_UNIT, pl.col("HALF_UP")))}
    return by_era(penalty, modes.get)


def surrender_values(legacy_dir, held: pl.DataFrame, rounding=("down", "half_up"), summed: str = "each",
                     valuation: str = "exact", penalty="net", ended: str = "on",
                     floor: str = "zero") -> pl.DataFrame:
    """BK_POLNR, VALUATION, SURRENDER_VALUE and POLICY_VALUE (cents) of every policy on every valuation date of
    `held` (`accounting.holdings`); 0 without units."""
    values = penalty_rates(legacy_dir, valued(legacy_dir, held, rounding, summed, valuation))
    gone = values.join(ends(legacy_dir), left_on="BK_POLNR", right_on="PH_POLNR", how="left")
    closing = {name: getattr(pl.col("ENDED"), comparison)(pl.col("VALUATION")).fill_null(False)
               for name, comparison in ENDED.items()}
    worth = pl.when(closing.get(ended, pl.lit(False))).then(0)
    priced = gone.select("BK_POLNR", "VALUATION",
                         SURRENDER_VALUE=worth.otherwise(FLOORS[floor](pl.col("POLICY_VALUE").sub(penalty_of(penalty)))),
                         POLICY_VALUE=worth.otherwise(pl.col("POLICY_VALUE")))
    everyone = table(legacy_dir, "NRPOLH").select(BK_POLNR="PH_POLNR").unique().join(
        held.select("VALUATION").unique(), how="cross")
    return everyone.join(priced, on=["BK_POLNR", "VALUATION"], how="left").fill_null(0)
