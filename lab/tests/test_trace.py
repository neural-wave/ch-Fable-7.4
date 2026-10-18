"""The trace of a policy: the submission's own replay, written down and compared with the diagnostic files."""
import pytest

from neuronlab import paths, trace


@pytest.fixture(scope="module")
def accounting():
    return trace.tracer()(str(paths.LEGACY))


def test_an_exact_policy_has_no_divergence(accounting):
    """BL10000001: every booking as in NRBOOK and t3_booking, every value as in the files, so no marker."""
    found = trace.timeline("BL10000001", accounting)
    assert found["bookings"] == {"same": 4298}
    assert found["checks"]["ok"] == found["checks"]["total"] > 200
    assert found["first_divergence"] is None and found["differences_total"] == 0
    assert found["projection"][0] == {"year": 1, "date": "2008-03-26", "computed": 2117.45, "target": 2117.45}


def test_a_value_typed_by_hand_is_marked_in_its_month(accounting):
    """BL10000321: the bookings match, the surrender value of 2025-12-31 is 175 francs off: the marker is there."""
    found = trace.timeline("BL10000321", accounting)
    assert set(found["bookings"]) == {"same"}
    first = found["first_divergence"]
    assert (first["date"], first["source"]) == ("2025-12-31", "t3_surrender_value")
    assert float(first["target"]) - float(first["computed"]) == pytest.approx(175.00)
    marked = [m for m, n in zip(found["months"], found["differing_per_month"]) if n]
    assert marked == ["2025-12-31"]


def test_a_reversed_switch_is_not_a_difference():
    """NRBOOK keeps the bookings of the switch 245 that event 246 reversed; the submission rightly books nothing."""
    theirs = trace.diagnostic("BL10000321")
    assert 245 not in theirs["event"].to_list()
