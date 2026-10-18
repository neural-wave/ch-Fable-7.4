"""History of the runs: the jobs started by `lab serve`, plus the runs before it, rebuilt from their artifacts.

A job is recorded in `lab/runs/_history.jsonl`, one JSON object per state change; the last line of an id wins.
Runs made on the command line or before `lab serve` existed have no record. They are rebuilt from what they left:
- the ledger of a run folder: a burst of pool evaluations is a pipeline run (or a step-5 run in `<task>~llm`), a
  `code:` entry is a `lab score` of the submission;
- `agent-<time>.jsonl`: one unattended Claude Code session of `lab agent`, with its duration and cost.
Rebuilt runs have no step durations; their score is the best ledger entry of the burst, like the job records.
"""
import datetime as dt
import functools
import json
import os

from .. import paths

HISTORY_NAME = "_history.jsonl"
GAP = 120  # seconds of silence in a ledger that separate two runs
STEPS = ("Profile keys and joins", "Cluster relations", "Optimal decision trees", "Candidate pool",
         "Language model", "Exact scoring", "Pass on residuals")
STEP_OF = {"profile": 0, "frame": 0, "cluster": 1, "tree": 2, "pool": 3, "llm": 4, "score": 5, "iterate": 6,
           "report": 6}
SHAPES = {  # the steps each kind of run goes through, as the artifacts show them: done, skipped
    "Pipeline": "ddddsdd", "Step 5": "ssddddd", "Score": "sssssds", "Ablation": "sssssds", "Agent": "sssssss",
}


def history_file():
    return paths.RUNS / HISTORY_NAME


def kind_of(run):
    """Kind of a run from its folder name: `<task>`, `<task>~llm`, `<task>~score`, `<task>~off-<card>`..."""
    if "~" not in run:
        return "Pipeline"
    suffix = run.split("~", 1)[1]
    if suffix in ("llm", "ablate"):
        return "Step 5"
    if suffix == "score":
        return "Score"
    return "Ablation" if suffix == "on" or suffix.startswith("off-") else "Pipeline"


def parse_time(text):
    return dt.datetime.fromisoformat(text) if text else None


def now():
    return dt.datetime.now().isoformat(timespec="seconds")


def append(record):
    """Append one state of a job record."""
    with open(history_file(), "a", encoding="utf-8") as f:
        f.write(json.dumps(record, default=str) + "\n")


def recorded():
    """{id: last state} of the jobs of `lab serve`."""
    found = {}
    path = history_file()
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                record = json.loads(line)
                found[record["id"]] = record
    return found


def _mtime_key(path):
    return (str(path), path.stat().st_mtime_ns if path.exists() else 0)


@functools.lru_cache(maxsize=64)
def _ledger(key):
    path = key[0]
    if not os.path.exists(path):
        return ()
    entries = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.startswith("{"):
                entries.append(json.loads(line))
    return tuple(entries)


def ledger(run):
    """Every evaluation of a run folder, oldest first (cached until the file changes)."""
    return list(_ledger(_mtime_key(paths.RUNS / run / "ledger.jsonl")))


def best_entry(entries):
    """The entry with the most exact holdout rows, then discovery rows: the ranking of the pool."""
    if not entries:
        return None
    return max(entries, key=lambda e: (e["holdout"][0], e["discovery"][0], e["time"]))


def bursts(entries):
    """Ledger entries split into runs: a gap of GAP seconds, or a switch between pool and `code:` entries."""
    groups = []
    for e in entries:
        t, code = parse_time(e["time"]), e["candidate"].startswith("code:")
        last = groups[-1] if groups else None
        if last and code == last["code"] and (t - last["end"]).total_seconds() <= GAP and not code:
            last["entries"].append(e)
            last["end"] = t
        else:
            groups.append({"code": code, "start": t, "end": t, "entries": [e]})
    return groups


def run_folders():
    """Run folders of the lab: tasks and their variants, not the files of `lab viz`."""
    if not paths.RUNS.exists():
        return []
    return sorted(p.name for p in paths.RUNS.iterdir() if p.is_dir() and p.name.startswith("t"))


def rebuilt():
    """Runs that left artifacts but no record: ledger bursts and Claude Code sessions."""
    found = []
    for run in run_folders():
        task = run.split("~")[0]
        for g in bursts(ledger(run)):
            kind = "Score" if g["code"] else kind_of(run)
            best = best_entry(g["entries"])
            found.append({"id": f"{run}@{g['start'].isoformat()}", "run": run, "task": task, "kind": kind,
                          "status": "done", "started": g["start"].isoformat(), "ended": g["end"].isoformat(),
                          "source": "ledger", "best": best, "evaluations": len(g["entries"])})
        for trace in sorted((paths.RUNS / run).glob("agent-*.jsonl")):
            found.append(agent_run(run, trace))
    return found


def agent_run(run, trace):
    """A Claude Code session of `lab agent` (or scripts/claude-tasks.sh) from its stream-json trace."""
    stamp = trace.stem.split("-", 1)[1]
    started = dt.datetime.strptime(stamp, "%Y%m%dT%H%M%S")
    end = result_event(trace)
    secs = (end or {}).get("duration_ms", 0) / 1000
    status = "running" if end is None else ("failed" if end.get("is_error") else "done")
    return {"id": f"{run}@agent-{stamp}", "run": run, "task": run.split("~")[0], "kind": "Agent",
            "status": status, "started": started.isoformat(), "source": "agent", "trace": trace.name,
            "ended": (started + dt.timedelta(seconds=secs)).isoformat() if end else None,
            "note": last_line((end or {}).get("result")),
            "cost": (end or {}).get("total_cost_usd"), "turns": (end or {}).get("num_turns")}


def last_line(text, width=160):
    lines = [s.strip() for s in (text or "").splitlines() if s.strip()]
    return lines[-1][:width] if lines else ""


def result_event(trace):
    """The final `result` event of a stream-json trace, None while the session runs."""
    with open(trace, "rb") as f:
        f.seek(0, os.SEEK_END)
        size = f.tell()
        f.seek(max(0, size - 200_000))
        tail = f.read().decode("utf-8", errors="replace")
    for line in reversed(tail.splitlines()):
        if '"type":"result"' in line.replace(" ", ""):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                return None
    return None


def overlaps(record, job):
    """A rebuilt run that lies inside the window of a job of the same folder is that job."""
    if record["run"] != job["run"] and not (record["kind"] == "Score" and job.get("kind") == "Score"
                                            and record["task"] == job["task"]):
        return False
    start, end = parse_time(job.get("started")), parse_time(job.get("ended")) or dt.datetime.now()
    t = parse_time(record["started"])
    return start is not None and start - dt.timedelta(seconds=5) <= t <= end + dt.timedelta(seconds=5)


def with_score(job):
    """A job record with the best ledger entry written while it ran (pool or score)."""
    if job.get("best") or job.get("status") == "queued" or not job.get("started"):
        return job
    start, end = parse_time(job["started"]), parse_time(job.get("ended")) or dt.datetime.now()
    folders = {job["run"], job["task"]} if job.get("kind") == "Score" else {job["run"]}
    entries = [e for f in folders for e in ledger(f)
               if start - dt.timedelta(seconds=2) <= parse_time(e["time"]) <= end + dt.timedelta(seconds=2)]
    if job.get("kind") == "Score":
        entries = [e for e in entries if e["candidate"].startswith("code:")]
    return dict(job, best=best_entry(entries))


def runs():
    """Every run, newest first: jobs of `lab serve` and rebuilt runs that no job covers."""
    jobs = [with_score(j) for j in recorded().values()]
    old = [r for r in rebuilt() if not any(overlaps(r, j) for j in jobs if j.get("kind") != "Agent")
           and not any(r["id"] == j.get("rebuilt_id") for j in jobs)]
    order = {"running": 0, "queued": 1}
    everything = sorted(jobs + old, key=lambda r: r.get("queued_at") or r.get("started") or "", reverse=True)
    return sorted(everything, key=lambda r: order.get(r.get("status"), 2))
