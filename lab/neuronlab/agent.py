"""The agent of the lab: one headless session per task, one after the other (standard library only).

The sessions run one after the other because they all edit starter_kit/my_solution/submission.py. Each one follows
the skill rule-discovery (.claude/skills/rule-discovery/SKILL.md) until one of its stop conditions.

    lab agent [task ...]                       default: the tasks t1 to t4 (t0 is done)
    python lab/neuronlab/agent.py [task ...]   the same without installing the lab (scripts/claude-tasks.sh)

    AGENT_BACKEND=opencode  (default) OpenCode on the open-weights model of .env.llm, with scripts/opencode-open.jsonc;
                            `--auto` approves every action the configuration does not deny
    AGENT_BACKEND=claude    Claude Code in auto permission mode: actions its classifier finds risky are denied
    AGENT_MODEL=...         the model (OpenCode: an id the endpoint serves; Claude Code: e.g. opus)
    MAX_BUDGET_USD=20       Claude Code only: stops a session at that cost
    AGENT_IDLE_TIMEOUT=900  stops a session whose trace gets no new event for that many seconds (0: never)
    AGENT_TIMEOUT=0         stops a session after that many seconds in all (0, the default: never)

The trace of each session is lab/runs/<task>/agent-<time>.jsonl, one JSON event per line as the backend writes it,
closed by a `result` line in the format of Claude Code (answer, turns, cost, duration, session id) so that the
summary and the runs page read both backends alike. A session stopped by a timeout ends with exit code 124 and a
`result` that says why; the next task starts.
"""
import ctypes
import datetime as dt
import json
import os
import pathlib
import shutil
import signal
import subprocess
import sys
import time

REPO = pathlib.Path(__file__).resolve().parents[2]  # the project skills are found from the root of the repository
DEFAULT_TASKS = ("t1_next_due_dates", "t2_projected_maturity_value", "t3_surrender_value", "t4_annual_statement")
BACKENDS = ("opencode", "claude")
OPENCODE_CONFIG = REPO / "scripts" / "opencode-open.jsonc"
PROMPT = """Use the skill rule-discovery on the task {task}. Read lab/runs/{task}/notes.md first if it exists. Follow the
loop of the skill until one of its stop conditions, then verify (step 5), let t5 see the task if it scores well
(step 6) and write the notes (step 7). Change only the function of {task} (in starter_kit/my_solution/submission.py or its module of tasks/)
and the rule modules it uses, so that the other tasks keep their score. End with the score of {task} (total and holdout)."""
SKILL = "The skill is the file .claude/skills/rule-discovery/SKILL.md: read it first and follow it. "
IDLE_TIMEOUT = 900  # seconds without a new event in the trace: a remote model that stopped answering
TIMED_OUT = 124  # the exit code of `timeout`


def backend():
    name = (os.environ.get("AGENT_BACKEND") or "opencode").strip().lower()
    if name not in BACKENDS:
        raise RuntimeError(f"AGENT_BACKEND is {name!r}: use one of {', '.join(BACKENDS)}")
    return name


def prompt(task, which=None):
    text = PROMPT.format(task=task)
    if (which or backend()) == "opencode":  # one line: a Windows .cmd shim cuts an argument at a newline
        return SKILL + " ".join(text.split())
    return text


def read_env_file(path=REPO / ".env.llm"):
    """KEY=VALUE lines of .env.llm, as `source` reads them; '#' starts a comment after a blank."""
    found = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.split(" #", 1)[0].strip()
            if "=" in line and not line.startswith("#"):
                key, value = (part.strip() for part in line.split("=", 1))
                found[key] = value.strip("'\"")
    return found


def opencode_env():
    """The environment of OpenCode: the endpoint of .env.llm (the file wins, as with scripts/opencode-open.sh),
    the model of AGENT_MODEL when set, and the configuration with the provider "open" and no other."""
    env = dict(os.environ, **read_env_file())
    if os.environ.get("AGENT_MODEL"):
        env["OPEN_MODEL"] = os.environ["AGENT_MODEL"]
    missing = [k for k in ("OPEN_BASE_URL", "OPEN_API_KEY", "OPEN_MODEL", "OPEN_CONTEXT")
               if not env.get(k) or "REPLACE_ME" in env[k]]
    if missing:
        raise RuntimeError(f"fill in {', '.join(missing)} in .env.llm (see .env.llm.example)")
    env["OPEN_PROTOCOL"] = env.get("OPEN_PROTOCOL") or "openai"
    env["OPEN_BASE_URL"] = env["OPEN_BASE_URL"].rstrip("/")
    env["OPEN_MAX_OUTPUT"] = env.get("OPEN_MAX_OUTPUT") or "8192"  # the 32000 default eats a small window
    env["OPENCODE_CONFIG"] = str(OPENCODE_CONFIG)
    return env


def command(task, exe=None, which=None):
    """The command of one session (`exe`: another executable, or a command prefix, for tests)."""
    which = which or backend()
    exe = exe or shutil.which("opencode" if which == "opencode" else "claude")
    if not exe:
        missing = {"opencode": "OpenCode is not on PATH: install it with `npm i -g @opencode/cli` (Node.js)",
                   "claude": "Claude Code is not on PATH: install it and log in with `claude`"}
        raise RuntimeError(missing[which])
    prefix = list(exe) if isinstance(exe, (list, tuple)) else [exe]
    if which == "opencode":
        # --standalone: a private server started here reads OPENCODE_CONFIG, the shared background service does not
        return [*prefix, "run", "--standalone", "--auto", "--format", "json", "--title", f"rule-discovery {task}",
                prompt(task, which)]
    options = ["--permission-mode", "auto", "--output-format", "stream-json", "--verbose"]
    if os.environ.get("AGENT_MODEL"):
        options += ["--model", os.environ["AGENT_MODEL"]]
    if os.environ.get("MAX_BUDGET_USD"):
        options += ["--max-budget-usd", os.environ["MAX_BUDGET_USD"]]
    return [*prefix, "-p", *options, prompt(task, which)]


def events(trace):
    found = []
    with open(trace, encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith("{"):
                try:
                    found.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return found


def opencode_result(trace, code, seconds):
    """A `result` event in the format of Claude Code from an OpenCode trace: the last text is the answer."""
    found = events(trace)
    texts = [e["part"].get("text", "") for e in found if e.get("type") == "text" and isinstance(e.get("part"), dict)]
    cost = sum(float((e.get("part") or {}).get("cost") or 0) for e in found if e.get("type") == "step_finish")
    return {"type": "result", "subtype": "success" if code == 0 else "error", "is_error": code != 0,
            "result": texts[-1] if texts else "", "num_turns": sum(e.get("type") == "step_start" for e in found),
            "total_cost_usd": cost, "duration_ms": round(seconds * 1000),
            "session_id": next((e.get("sessionID") for e in found if e.get("sessionID")), None), "backend": "opencode"}


def summary(trace):
    """The answer of the session, then turns, cost and session id, from the final `result` event of the trace."""
    end = next((e for e in reversed(events(trace)) if e.get("type") == "result"), {})
    return (f"{end.get('result') or '(no result: see the trace)'}\n"
            f"   {end.get('num_turns', '?')} turns, {end.get('total_cost_usd') or 0:.2f} USD, "
            f"session {end.get('session_id', '?')}")


def limits():
    """(idle seconds, total seconds) of AGENT_IDLE_TIMEOUT and AGENT_TIMEOUT, None for a limit turned off with 0."""
    idle = float(os.environ.get("AGENT_IDLE_TIMEOUT") or IDLE_TIMEOUT)
    total = float(os.environ.get("AGENT_TIMEOUT") or 0)
    return idle or None, total or None


def spawn_options():
    """Popen options that let `stop` end the session and every process it started.

    Windows: a process without a console (lab serve runs the jobs so) cannot give one to a console program, so the
    session gets none either; POSIX: a session of its own, killed as a group.
    """
    if os.name == "nt":
        return {"creationflags": subprocess.CREATE_NO_WINDOW} if not ctypes.windll.kernel32.GetConsoleWindow() else {}
    return {"start_new_session": True}


def stop(process):
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True)
    else:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    try:
        process.wait(timeout=30)
    except subprocess.TimeoutExpired:
        process.kill()


def watch(process, trace, idle, total, poll=1.0):
    """Wait for a session; stop it when its trace stays silent `idle` seconds or it runs `total` seconds.

    Returns (exit code, why it was stopped or None).
    """
    started = last = time.time()
    size = 0
    while process.poll() is None:
        time.sleep(poll)
        now = time.time()
        current = trace.stat().st_size if trace.exists() else 0
        if current != size:
            size, last = current, now
        if idle and now - last > idle:
            stop(process)
            return TIMED_OUT, f"no new event in the trace for {idle:.0f} s (AGENT_IDLE_TIMEOUT)"
        if total and now - started > total:
            stop(process)
            return TIMED_OUT, f"the session ran longer than {total:.0f} s (AGENT_TIMEOUT)"
    return process.returncode, None


def connection(lines):
    """The model of a stream-json trace and whether it answered: the `init` event names the model Claude Code is
    connected to, the `result` event says if the request went through (its text is the error when it did not)."""
    found = {"model": None, "source": None, "version": None, "ok": False, "error": "no init event in the trace"}
    for line in lines:
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "system" and event.get("subtype") == "init":
            found.update(model=event.get("model"), source=event.get("apiKeySource"),
                         version=event.get("claude_code_version"), error="no result event in the trace")
        elif event.get("type") == "result":
            failed = event.get("is_error") or event.get("subtype") != "success"
            found.update(ok=not failed, error=(str(event.get("result") or event.get("subtype")) if failed else None))
    return found


def probe(model="", claude=None):
    """connection() of a one-word request: which model Claude Code answers with right now (about 0.01 USD on Claude).

    A custom model works the same: Claude Code reads ANTHROPIC_BASE_URL, ANTHROPIC_AUTH_TOKEN and ANTHROPIC_MODEL
    from the environment (.env.llm) and the `init` event names the model it asked the endpoint for."""
    claude = claude or shutil.which("claude")
    if not claude:
        return dict(connection([]), error="Claude Code is not on PATH: install it and log in with `claude`")
    prefix = list(claude) if isinstance(claude, (list, tuple)) else [claude]
    command = [*prefix, "-p", "--output-format", "stream-json", "--verbose", "--tools", "", "--disable-slash-commands",
               "--strict-mcp-config", "--no-session-persistence", "--system-prompt", "Answer with one word."]
    if model:
        command += ["--model", model]
    try:
        done = subprocess.run([*command, "ok"], stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=180,
                              cwd=REPO)
    except subprocess.TimeoutExpired:
        return dict(connection([]), error="Claude Code did not answer in 180 s")
    except OSError as e:
        return dict(connection([]), error=f"Claude Code could not start: {e}")
    found = connection(done.stdout.splitlines())
    if not found["ok"] and found["model"] is None and done.stderr.strip():
        found["error"] = done.stderr.strip().splitlines()[-1]
    return found


def session(task, runs=None, exe=None, which=None):
    """Run one session of a task, its trace into the run folder; returns the exit code (124: stopped by a timeout)."""
    which = which or backend()
    folder = (runs or REPO / "lab" / "runs") / task
    folder.mkdir(parents=True, exist_ok=True)
    trace = folder / f"agent-{dt.datetime.now():%Y%m%dT%H%M%S}.jsonl"
    shown = trace.relative_to(REPO) if trace.is_relative_to(REPO) else trace
    print(f"== {task}  ({which}, trace: {shown})", flush=True)
    env = opencode_env() if which == "opencode" else None
    started = time.time()
    with open(trace, "w", encoding="utf-8") as out:
        process = subprocess.Popen(command(task, exe, which), stdin=subprocess.DEVNULL, stdout=out, cwd=REPO,
                                   env=env, **spawn_options())
        code, why = watch(process, trace, *limits())
    end = None
    if which == "opencode":
        end = opencode_result(trace, code, time.time() - started)
    elif why:
        end = {"type": "result", "subtype": "error", "is_error": True, "result": "", "num_turns": None,
               "total_cost_usd": None, "duration_ms": round((time.time() - started) * 1000), "backend": "claude"}
    if end is not None:
        if why:
            last = f". Last answer: {end['result']}" if end["result"] else ""
            end.update(subtype="error_timeout", is_error=True, stopped=why, result=f"stopped by lab agent: {why}{last}")
        with open(trace, "a", encoding="utf-8") as out:
            out.write(json.dumps(end) + "\n")
    if code:
        print(f"   the session {'was stopped: ' + why if why else 'ended with an error'}, see the trace", flush=True)
    print(summary(trace), flush=True)
    return code


def main(argv=None):
    tasks = list(argv if argv is not None else sys.argv[1:]) or list(DEFAULT_TASKS)
    codes = [session(task) for task in tasks]
    return 1 if any(codes) else 0


if __name__ == "__main__":
    sys.exit(main())
