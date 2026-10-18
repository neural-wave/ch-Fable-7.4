#!/usr/bin/env bash
# Claude Code as the agent of the lab: one headless session per task, one after the other because they all edit
# starter_kit/my_solution/submission.py. The sessions are run by lab/neuronlab/agent.py (standard library only, also
# `lab agent` and the button "Run every task unattended" of `lab serve`); this wrapper keeps the old command.
# Usage: scripts/claude-tasks.sh [task ...]    default: the tasks t1 to t4 (t0 is done)
#   AGENT_MODEL=opus        model of the sessions (default: the one of Claude Code)
#   MAX_BUDGET_USD=20       stops a session at that cost
#   PYTHON=python3          the Python that runs agent.py
# The trace of each session is lab/runs/<task>/agent-<time>.jsonl (follow it with tail -f); the summary and the
# session id are printed at the end, and `claude --resume <session id>` continues a session.
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
exec "${PYTHON:-python3}" "$root/lab/neuronlab/agent.py" "$@"
