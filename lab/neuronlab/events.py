"""Progress events of a run, for `lab serve`: JSON lines appended to the file named by NEURON_EVENTS.

Without the variable every call is a no-op, so the pipeline behaves as before on the command line. Each event is
one line `{"t": seconds since the epoch, "event": ..., ...}`; the server tails the file and streams it to the page.
"""
import contextlib
import json
import os
import time

from . import paths

ARTIFACTS = {
    "profile": ("profile.json",), "frame": ("frame.json", "frame.parquet"),
    "cluster": ("clusters.json", "labels.parquet", "histograms.json"), "tree": ("trees.json",),
    "pool": ("pool.json", "ledger.jsonl"), "iterate": ("residuals.json", "outliers.json"), "report": ("report.md",), "score": ("score.md", "diffs.parquet"),
    "llm": ("llm",), "ablate": ("ablation.json", "ablation.parquet"),
}


def emit(event, **fields):
    """Append one event to NEURON_EVENTS, if set."""
    target = os.environ.get("NEURON_EVENTS")
    if not target:
        return
    with open(target, "a", encoding="utf-8") as f:
        f.write(json.dumps({"t": round(time.time(), 3), "event": event, **fields}, default=str) + "\n")


@contextlib.contextmanager
def step(name, run):
    """Events `running`, then `done` (with seconds and the artifacts written) or `failed` around one step."""
    started = time.time()
    emit("step", step=name, run=run, state="running")
    try:
        yield
    except BaseException as e:
        emit("step", step=name, run=run, state="failed", secs=round(time.time() - started, 2), error=str(e)[:500])
        raise
    folder = paths.RUNS / run
    files = [f for f in ARTIFACTS.get(name, ()) if (folder / f).exists()]
    emit("step", step=name, run=run, state="done", secs=round(time.time() - started, 2), files=files)
