"""Bisection on step-by-step diagnostics: the first step at which a calculation leaves its target.

A diagnostic target has a value per key and step, e.g. t2_projection_year has the projected value of every
policy at the end of each policy year. A missing or wrong rule shows up first in the step where it acts for the
first time, and every later step inherits the difference: the first differing step points at the rule, and the
policies that share it point at its condition. That is how t2 was solved:

- every differing year one cent off at a tie: the growth needs the decimal arithmetic of Neuron (`money.grown`)
- the offers signed before the conversion off from the first year: COBOL truncates and counts ages in days
- birthdays about six months from the start date: the age is rounded, not the age last birthday

The opposite pattern is a manual correction (t5): every step right and only the final value wrong.
"""
import polars as pl

from money import francs
from neuron.load import LEGACY
from neuron.targets import target
from projection import projected_years
from submission import t2_projected_maturity_value


def first_divergence(predicted: pl.DataFrame, expected: pl.DataFrame, key: str, step: str) -> pl.DataFrame:
    """One row per `key` whose `value` differs in some `step`: the first such step, both values and the difference.

    Both frames have the columns `key`, `step` and `value`; a step missing from `predicted` counts as different.
    """
    both = expected.join(predicted, on=[key, step], how="left", suffix="_predicted")
    differing = both.filter(pl.col("value").ne(pl.col("value_predicted")).fill_null(True))
    first = differing.sort(step).group_by(key, maintain_order=True).first()
    return first.with_columns(difference=pl.col("value_predicted").sub(pl.col("value"))).sort(key)


def projection_years() -> pl.DataFrame:
    """The projected values of the submission in the format of t2_projection_year (exact decimals)."""
    return projected_years(LEGACY).select(policy_id="PH_POLNR", policy_year="YEAR", value=francs(pl.col("VALUE")))


def projection_divergence() -> pl.DataFrame:
    """`first_divergence` of the submission's projection against t2_projection_year."""
    return first_divergence(projection_years(), target("t2_projection_year", amounts=("value",)), "policy_id",
                            "policy_year")


def corrected_maturities() -> pl.DataFrame:
    """The policies whose projection is right in every year but whose maturity value is not: manual corrections.

    The difference shows how the value was changed, e.g. whole francs with the cents of the projection.
    """
    predicted = pl.DataFrame(list(t2_projected_maturity_value(LEGACY).items()), schema=["policy_id", "predicted"],
                             orient="row")
    expected = target("t2_projected_maturity_value", amounts=("maturity_value",))
    both = expected.join(predicted, on="policy_id").join(projection_divergence(), on="policy_id", how="anti")
    wrong = both.filter(pl.col("maturity_value").ne(pl.col("predicted")))
    return wrong.with_columns(difference=pl.col("maturity_value").sub(pl.col("predicted")))
