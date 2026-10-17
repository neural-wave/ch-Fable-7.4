"""Exact arithmetic of the lab and the date helper of the submission, against independent implementations."""
import datetime as dt
import decimal
import random
import sys
from decimal import Decimal

import polars as pl
import pytest

from neuronlab import exact, paths

sys.path.insert(0, str(paths.SUBMISSION))
import neuron  # noqa: E402

VALUES = [random.Random(0).randint(-10 ** 9, 10 ** 9) for _ in range(5000)] + [5, -5, 15, -15, 25, -25, 0, 1, -1]


@pytest.mark.parametrize("mode", exact.MODES)
def test_round_to_matches_decimal(mode):
    """Integers in units of 0.001 rounded to units of 0.1, in every mode, exactly as Decimal.quantize."""
    got = pl.DataFrame({"n": VALUES}, schema={"n": pl.Int128}).select(exact.round_to(pl.col("n"), 3, 1, mode))
    want = [int(Decimal(v).scaleb(-3).quantize(Decimal("0.1"), rounding=getattr(decimal, mode)).scaleb(1))
            for v in VALUES]
    assert got.to_series().to_list() == want


@pytest.mark.parametrize("day", [dt.date(2024, 1, 31), dt.date(2023, 1, 31), dt.date(2024, 8, 31),
                                 dt.date(2006, 3, 31), dt.date(2023, 12, 15), dt.date(2024, 2, 29)])
@pytest.mark.parametrize("months", [-13, -1, 1, 2, 11, 12, 25])
def test_add_months_matches_polars(day, months):
    """neuron.add_months (submission) and Polars offset_by (lab) clip a missing day to the end of the month alike."""
    assert neuron.add_months(day, months) == pl.select(pl.lit(day).dt.offset_by(f"{months}mo")).item()
