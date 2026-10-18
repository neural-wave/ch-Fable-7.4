"""The stdlib loader of the submission and the Polars store of the lab decode every table the same way."""
import os
import sys

import pytest

from neuronlab import paths, store

sys.path.insert(0, str(paths.SUBMISSION))
import neuron  # noqa: E402

BIG = {"NRBOOK"}  # 6.8 M rows: set NEURON_FULL=1 to include it


@pytest.mark.parametrize("name", store.tables())
def test_same_values(name):
    if name in BIG and not os.environ.get("NEURON_FULL"):
        pytest.skip("large table, set NEURON_FULL=1")
    lab = store.load(name)
    lab = lab.select(c for c in lab.columns if not c.endswith("_RAW"))
    stdlib = neuron.table(str(paths.LEGACY), name)
    assert lab.height == len(stdlib)
    for expected, actual in zip(lab.iter_rows(named=True), stdlib):
        assert {k: actual.get(k) for k in expected} == expected
