"""Where the lab finds the challenge data and keeps its caches and run artifacts."""
import os
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[2]
LEGACY = pathlib.Path(os.environ.get("NEURON_LEGACY", REPO / "legacy"))
TARGETS = pathlib.Path(os.environ.get("NEURON_TARGETS", REPO / "targets"))
STARTER_KIT = REPO / "starter_kit"
SUBMISSION = STARTER_KIT / "my_solution"
CACHE = REPO / "lab" / ".cache"
DERIVED = CACHE / "derived"  # pseudo-targets built from legacy tables (derived.py)
RUNS = REPO / "lab" / "runs"


def run_dir(task):
    """Artifact folder of one task, created on first use."""
    folder = RUNS / task
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def load_env(path=REPO / ".env.llm"):
    """KEY=VALUE lines of .env.llm into os.environ, without overriding variables that are already set."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split(" #", 1)[0].strip()  # inline comments need a blank before '#', tokens may contain '#'
        if "=" in line and not line.startswith("#"):
            key, value = (part.strip() for part in line.split("=", 1))
            os.environ.setdefault(key, value.strip("'\""))
