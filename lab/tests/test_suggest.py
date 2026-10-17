"""Step 5 (`lab suggest`): the harness side with a scripted model, and the real model when one is configured.

The scripted tests check that a valid proposal reaches the exact score and that a bad one is rejected; the last
test asks the configured open-weights model (skipped when .env.llm has no endpoint).
"""
import json
import os

import pytest

from neuronlab import llm, paths, suggest

TASK, ABLATE = "t0_commission", "*@*"


@pytest.fixture(autouse=True, scope="module")
def pipeline():
    if not (paths.run_dir(TASK) / "pool.json").exists():
        from neuronlab import cli
        cli.run(TASK)


def scripted(answer):
    return lambda prompt, system="", max_tokens=2048: answer


def test_right_feature_recovers_the_score(monkeypatch):
    answer = json.dumps([{"name": "tier_at_receipt", "expr": "at(BR_TIER, PR_RCVDT)", "why": "rate follows the tier"}])
    monkeypatch.setattr(llm, "complete", scripted(answer))
    monkeypatch.setattr(llm, "settings", lambda: ("scripted", "", "", "scripted-model"))
    text = suggest.suggest(TASK, ablate=ABLATE)
    assert "best before: C2.1 224418" in text
    assert text.rstrip().endswith("225848 rows exact")


def test_invalid_proposals_are_rejected(monkeypatch):
    answer = '[{"name": "x", "expr": "__import__(\'os\').system(\'ls\')"}, {"name": "y", "expr": "at(BR_TIER, NOPE)"}]'
    monkeypatch.setattr(llm, "complete", scripted(answer))
    monkeypatch.setattr(llm, "settings", lambda: ("scripted", "", "", "scripted-model"))
    text = suggest.suggest(TASK, ablate=ABLATE)
    assert "0 valid proposals" in text and "224418 rows exact; after: C2.1 224418" in text


def configured():
    """True when .env.llm (or the environment) names an endpoint, a key and a model without placeholders."""
    paths.load_env()
    try:
        llm.settings()
    except RuntimeError:
        return False
    return True


@pytest.mark.skipif(not (os.environ.get("NEURON_LLM") and configured()),
                    reason="calls the open-weights model: set NEURON_LLM=1 and fill in .env.llm")
def test_open_weights_model_finds_the_missing_feature():
    text = suggest.suggest(TASK, ablate=ABLATE)
    print(text)
    assert text.rstrip().endswith("225848 rows exact")
