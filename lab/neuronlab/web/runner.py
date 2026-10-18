"""Jobs of `lab serve`: lab commands and Claude Code sessions, one at a time, with progress events and cancel.

Every job is a list of commands run in order in a subprocess (`python -m neuronlab.cli ...`, the Claude Code
sessions too: `lab agent <task>`). Jobs run one after the other: they write into the same run folders and the agent
edits submission.py. The child gets NEURON_EVENTS, the file where `events.py` appends the step events; its output
goes to a log file. Both files are under `lab/runs/_jobs/`, and the state of each job goes to the history.
"""
import collections
import datetime as dt
import itertools
import json
import os
import pathlib
import signal
import subprocess
import sys
import threading

from .. import paths
from . import history

JOBS_NAME = "_jobs"


def jobs_dir():
    folder = paths.RUNS / JOBS_NAME
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def lab(*args):
    return [sys.executable, "-m", "neuronlab.cli", *map(str, args)]


PIPELINE = ("profile", "frame", "cluster", "tree", "pool", "iterate", "report")


def plan(action, task, options=None):
    """(kind, run folder, commands, environment) of an action of the page."""
    options = options or {}
    env = {"LLM_MODEL": options["model"]} if options.get("model") else {}
    if action == "run":
        steps = [s for s in options.get("steps") or PIPELINE if s in PIPELINE]
        commands = [lab("run", task)] if list(steps) == list(PIPELINE) else [lab(s, task) for s in steps]
        commands += [lab("feature", task, f["name"], f["expr"]) for f in options.get("features", [])]
        if options.get("suggest"):
            commands.append(lab("suggest", task, *max_features(options)))
        return "Pipeline", task, commands, env
    if action == "suggest":
        ablate = ["--ablate", options["ablate"]] if options.get("ablate") else []
        return "Step 5", f"{task}~{'ablate' if ablate else 'llm'}", [lab("suggest", task, *ablate,
                                                                         *max_features(options))], env
    if action == "feature":
        return "Step 5", f"{task}~llm", [lab("feature", task, options["name"], options["expr"])], env
    if action == "score":
        reason = score_refusal(task)
        if reason:
            raise ValueError(reason)
        return "Score", task, [lab("score", task)], env
    if action == "ablate":
        reason = ablate_refusal(task)
        if reason:
            raise ValueError(reason)
        return "Ablation", task, [lab("ablate", task, *options.get("cards", []))], env
    if action == "freeze":
        run = options.get("run") or task
        reason = freeze_refusal(run, options.get("candidate"))
        if reason:
            raise ValueError(reason)
        return "Freeze", run, [lab("freeze", run, *([options["candidate"]] if options.get("candidate") else []))], env
    if action == "policy":
        return "Viz", task, [lab("viz", "policy", *options["policies"])], env
    if action == "agent":
        env = {"AGENT_MODEL": options["model"]} if options.get("model") else {}
        return "Agent", task, [lab("agent", task)], env
    raise ValueError(f"unknown action {action}")


def score_refusal(task):
    from ..score import refusal
    return refusal(task)


def ablate_refusal(task):
    """Why `lab ablate` has nothing to do for a task, or None: it switches off the rule cards of rules/<task>.json."""
    reason = score_refusal(task)  # the cards change submission.py and score it again
    if reason:
        return reason
    if not (paths.RULES / f"{task}.json").exists():
        return f"no rule cards for {task}: lab ablate switches off the cards of lab/rules/{task}.json"
    return None


def freeze_refusal(run, candidate=None):
    from .. import freeze
    try:
        return freeze.refusal(run, candidate)
    except (OSError, StopIteration, KeyError) as e:
        return f"cannot freeze {run}: {e}"


def max_features(options):
    n = options.get("max_features")
    return ["--max-features", str(int(n))] if n else []


def read_events(path):
    if not path.exists():
        return []
    events = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("{"):
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                pass  # a line being written
    return events


def planned(kind, commands):
    """Indexes of the seven steps a job goes through: from its commands, else from its kind."""
    if not commands:
        return {i for i, c in enumerate(history.SHAPES.get(kind, "sssssss")) if c == "d"}
    found = set()
    for command in commands:
        words = command.split()
        if words[:1] != ["lab"] or len(words) < 2:
            continue
        if words[1] == "run":
            found |= {0, 1, 2, 3, 5, 6}
        elif words[1] in history.STEP_OF:
            found |= {history.STEP_OF[words[1]]} | ({5} if words[1] == "pool" else set())
        elif words[1] in ("suggest", "feature"):
            found |= {2, 3, 4, 5, 6}
        elif words[1] in ("score", "ablate"):
            found.add(5)
    return found


def step_states(kind, events, status, commands=None):
    """The seven steps of the page with state (done, running, failed, skipped, waiting), seconds and files."""
    wanted = planned(kind, commands)
    finished = status in ("done", "failed", "cancelled", "interrupted")
    initial = "done" if finished and status == "done" else "waiting"
    steps = [{"n": i + 1, "name": name, "state": initial if i in wanted else "skipped", "secs": None, "files": []}
             for i, name in enumerate(history.STEPS)]
    seen = set()
    for e in events:
        if e.get("event") == "step" and e.get("step") in history.STEP_OF:
            s = steps[history.STEP_OF[e["step"]]]
            if s["n"] not in seen:  # profile and frame share step 1: the durations add up
                seen.add(s["n"])
                s.update(secs=0.0, files=[])
            s["state"] = {"running": "running", "done": "done", "failed": "failed"}[e["state"]]
            if e.get("secs") is not None:
                s["secs"] = round((s["secs"] or 0) + e["secs"], 2)
            s["files"] = sorted(set(s["files"]) | set(e.get("files", [])))
            if e["step"] == "pool" and e["state"] == "done":  # the pool scores every candidate exactly
                steps[5].update(state="done", files=["ledger.jsonl"])
        if e.get("event") == "progress":
            steps[history.STEP_OF.get(e.get("step"), 3)]["progress"] = {k: e.get(k) for k in ("done", "total", "best")}
    if status in ("failed", "cancelled", "interrupted"):
        for s in steps:
            if s["state"] == "running":
                s["state"] = "failed" if status == "failed" else "cancelled"
    return steps


class Runner:
    """The queue of jobs and the thread that runs them."""

    def __init__(self):
        self.lock = threading.Lock()
        self.wake = threading.Condition(self.lock)
        self.queue = collections.deque()
        self.current, self.process, self.cancelled = None, None, set()
        self.counter = itertools.count(1)
        self.recover()
        threading.Thread(target=self.loop, name="ergo-runner", daemon=True).start()

    def recover(self):
        """Jobs left running or queued by a server that stopped are interrupted: their process is gone."""
        for job in history.recorded().values():
            if job.get("status") in ("running", "queued"):
                history.append(dict(job, status="interrupted", ended=job.get("ended") or history.now()))

    def submit(self, action, task, options=None, origin="page"):
        kind, run, commands, env = plan(action, task, options)
        stamp = dt.datetime.now().strftime("%Y%m%dT%H%M%S")
        job_id = f"{stamp}-{next(self.counter)}"
        folder = jobs_dir()
        job = {"id": job_id, "run": run, "task": task, "kind": kind, "action": action, "options": options or {},
               "commands": [self.display(c) for c in commands], "status": "queued", "queued_at": history.now(),
               "started": None, "ended": None, "exit": None, "origin": origin,
               "events": str(folder / f"{job_id}.events.jsonl"), "log": str(folder / f"{job_id}.log")}
        with self.wake:
            self.queue.append((job, commands, env))
            history.append(job)
            self.wake.notify()
        return job

    @staticmethod
    def display(command):
        """A command as the person would type it: `lab run t0`, `lab agent t2`."""
        if command[:3] == [sys.executable, "-m", "neuronlab.cli"]:
            return " ".join(["lab", *command[3:]])
        return " ".join(c if " " not in c else f'"{c}"' for c in command[1:])

    def queued(self):
        with self.lock:
            return [job for job, _, _ in self.queue]

    def cancel(self, job_id):
        """Remove a queued job, or stop the running one with its child processes."""
        with self.lock:
            for item in list(self.queue):
                if item[0]["id"] == job_id:
                    self.queue.remove(item)
                    history.append(dict(item[0], status="cancelled", ended=history.now()))
                    return True
            if self.current and self.current["id"] == job_id and self.process:
                self.cancelled.add(job_id)
                kill_tree(self.process)
                return True
        return False

    def stop_queue(self):
        """Stop after the running job: every queued job is cancelled."""
        with self.lock:
            items, self.queue = list(self.queue), collections.deque()
        for job, _, _ in items:
            history.append(dict(job, status="cancelled", ended=history.now()))
        return len(items)

    def loop(self):
        while True:
            with self.wake:
                while not self.queue:
                    self.wake.wait()
                job, commands, env = self.queue.popleft()
                self.current = job
            try:
                self.execute(job, commands, env)
            finally:
                with self.lock:
                    self.current, self.process = None, None

    def execute(self, job, commands, env):
        job = dict(job, status="running", started=history.now())
        history.append(job)
        environment = dict(os.environ, NEURON_EVENTS=job["events"], PYTHONUNBUFFERED="1", PYTHONIOENCODING="utf-8",
                           **env)
        code = 0
        with open(job["log"], "a", encoding="utf-8", errors="replace") as log:
            for command in commands:
                log.write(f"$ {self.display(command)}\n")
                log.flush()
                try:
                    process = subprocess.Popen(command, cwd=paths.REPO if command[0] != sys.executable
                                               else paths.REPO / "lab", env=environment, stdout=log,
                                               stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                               **process_group())
                except OSError as e:
                    log.write(f"cannot start: {e}\n")
                    code = -1
                    break
                with self.lock:
                    self.process = process
                code = process.wait()
                if code or job["id"] in self.cancelled:
                    break
        status = "cancelled" if job["id"] in self.cancelled else ("done" if code == 0 else "failed")
        events = read_events(pathlib.Path(job["events"]))
        history.append(dict(job, status=status, ended=history.now(), exit=code,
                            steps=step_states(job["kind"], events, status, job["commands"])))


def process_group():
    """Popen options that let `kill_tree` stop the child and everything it started."""
    if os.name == "nt":  # no console window: a server started without a console cannot give its children one
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW}
    return {"start_new_session": True}


def kill_tree(process):
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True)
    else:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
