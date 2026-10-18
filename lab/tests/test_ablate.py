"""`lab ablate`: rule cards switch one rule off in a scratch copy, never in the submission."""
import json

import pytest

from neuronlab import ablate, paths


def all_cards():
    for path in sorted(paths.RULES.glob("*.json")):
        task = json.loads(path.read_text(encoding="utf-8"))["task"]
        assert path.stem == task
        for card in ablate.cards(task):
            yield task, card


@pytest.mark.parametrize("task,card", list(all_cards()), ids=lambda x: x if isinstance(x, str) else x["id"])
def test_every_card_still_applies_to_the_submission(task, card):
    """Each text to replace is in the submission exactly once: a card that no longer applies fails here, not later."""
    assert card["rule"] and card["off"] and card["edits"]
    for edit in card["edits"]:
        source = (paths.SUBMISSION / edit["file"]).read_text(encoding="utf-8")
        assert source.count(edit["old"]) == 1, (card["id"], edit["file"], edit["old"])
        assert edit["new"] != edit["old"]


def test_the_scratch_copy_changes_and_the_submission_does_not():
    task, card = "t0_commission", next(c for c in ablate.cards("t0_commission") if c["id"] == "tier-on-money-date")
    before = (paths.SUBMISSION / "submission.py").read_text(encoding="utf-8")
    folder = ablate.scratch(task, card["id"], card["edits"])
    changed = (folder / "submission.py").read_text(encoding="utf-8")
    assert (paths.SUBMISSION / "submission.py").read_text(encoding="utf-8") == before
    assert "latest(policy_headers" in changed and "latest(policy_headers" not in before


def test_a_card_that_does_not_match_is_refused():
    with pytest.raises(ValueError, match="found 0 times"):
        ablate.scratch("t0_commission", "broken", [{"file": "submission.py", "old": "no such text", "new": "x"}])


def test_switching_off_half_up_breaks_one_commission():
    """README: half up beats half even on one row (BL10000869 #1, 399.205 -> 399.21); nothing else changes."""
    result = ablate.ablate("t0_commission", ["half-up"])
    card = next(c for c in result["cards"] if c["id"] == "half-up")
    assert (card["broken"], card["fixed"]) == (1, 0)
    assert card["examples"][0]["policy_id"] == "BL10000869" and card["examples"][0]["due_nr"] == "1"
    assert card["examples"][0]["amount"] == {"target": "399.21", "off": "399.20"}


def test_cards_without_their_columns_are_scored_again():
    """ablation.json is versioned and ablation.parquet is not: a card of the .json with no column is ablated again,
    so that `lab viz` finds the columns of every card."""
    import polars as pl
    table = paths.RUNS / "t0_commission" / "ablation.parquet"
    if table.exists():
        pl.read_parquet(table).select("policy_id", "due_nr", "on").write_parquet(table)
    result = ablate.ablate("t0_commission", ["half-up"])
    columns = pl.read_parquet(table).columns
    assert all(f"off:{c['id']}" in columns for c in result["cards"])
