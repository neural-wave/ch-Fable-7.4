"""Claude Code as the agent of the lab: one headless session per task, one after the other (standard library only).

The sessions run one after the other because they all edit starter_kit/my_solution/submission.py. Each one follows
the skill rule-discovery (.claude/skills/) until one of its stop conditions, in auto permission mode: actions the
classifier finds risky are denied, never asked.

    lab agent [task ...]                       default: the tasks t1 to t4 (t0 is done)
    python lab/neuronlab/agent.py [task ...]   the same without installing the lab (scripts/claude-tasks.sh)

    AGENT_MODEL=opus        model of the sessions (default: the one of Claude Code)
    MAX_BUDGET_USD=20       stops a session at that cost

The trace of each session is lab/runs/<task>/agent-<time>.jsonl (stream-json, one event per line); the summary and
the session id are printed at the end, and `claude --resume <session id>` continues a session.
"""
import datetime as dt
import json
import os
import pathlib
import shutil
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]  # the project skills are found from the root of the repository
DEFAULT_TASKS = ("t1_next_due_dates", "t2_projected_maturity_value", "t3_surrender_value", "t4_annual_statement")
PROMPT = """Use the skill rule-discovery on the task {task}. Read lab/runs/{task}/notes.md first if it exists. Follow the
loop of the skill until one of its stop conditions, then verify (step 5), let t5 see the task if it scores well
(step 6) and write the notes (step 7). Change only the function of {task} (in starter_kit/my_solution/submission.py or its module of tasks/)
and the rule modules it uses, so that the other tasks keep their score. End with the score of {task} (total and holdout)."""


def command(task, claude=None):
    """The `claude -p` command of one session (`claude`: another executable, or a command prefix, for tests)."""
    claude = claude or shutil.which("claude")
    if not claude:
        raise RuntimeError("Claude Code is not on PATH: install it and log in with `claude`")
    options = ["--permission-mode", "auto", "--output-format", "stream-json", "--verbose"]
    if os.environ.get("AGENT_MODEL"):
        options += ["--model", os.environ["AGENT_MODEL"]]
    if os.environ.get("MAX_BUDGET_USD"):
        options += ["--max-budget-usd", os.environ["MAX_BUDGET_USD"]]
    prefix = list(claude) if isinstance(claude, (list, tuple)) else [claude]
    return [*prefix, "-p", *options, PROMPT.format(task=task)]


def summary(trace):
    """The answer of the session, then turns, cost and session id, from the final `result` event of the trace."""
    end = {}
    with open(trace, encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith("{"):
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if event.get("type") == "result":
                    end = event
    return (f"{end.get('result') or '(no result: see the trace)'}\n"
            f"   {end.get('num_turns', '?')} turns, {end.get('total_cost_usd') or 0:.2f} USD, "
            f"session {end.get('session_id', '?')}")


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


def session(task, runs=None, claude=None):
    """Run one session of a task, its stream-json trace into the run folder; returns the exit code."""
    folder = (runs or REPO / "lab" / "runs") / task
    folder.mkdir(parents=True, exist_ok=True)
    trace = folder / f"agent-{dt.datetime.now():%Y%m%dT%H%M%S}.jsonl"
    print(f"== {task}  (trace: {trace.relative_to(REPO) if trace.is_relative_to(REPO) else trace})", flush=True)
    with open(trace, "w", encoding="utf-8") as out:
        code = subprocess.run(command(task, claude), stdin=subprocess.DEVNULL, stdout=out, cwd=REPO).returncode
    if code:
        print("   the session ended with an error, see the trace", flush=True)
    print(summary(trace), flush=True)
    return code


def main(argv=None):
    tasks = list(argv if argv is not None else sys.argv[1:]) or list(DEFAULT_TASKS)
    codes = [session(task) for task in tasks]
    return 1 if any(codes) else 0


if __name__ == "__main__":
    sys.exit(main())
