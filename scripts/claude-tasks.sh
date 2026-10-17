#!/usr/bin/env bash
# Claude Code as the agent of the lab: one headless session per task, one after the other because they all edit
# starter_kit/my_solution/submission.py. Each session follows the skill rule-discovery (.claude/skills/) until one of
# its stop conditions, in auto permission mode: actions the classifier finds risky are denied, never asked.
# Usage: scripts/claude-tasks.sh [task ...]    default: the tasks t1 to t4 (t0 is done)
#   AGENT_MODEL=opus        model of the sessions (default: the one of Claude Code)
#   MAX_BUDGET_USD=20       stops a session at that cost
# The trace of each session is lab/runs/<task>/agent-<time>.jsonl (follow it with tail -f); the summary and the
# session id are printed at the end, and `claude --resume <session id>` continues a session.
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root"  # the project skills are found from the root of the repository
tasks=("$@")
if [[ ${#tasks[@]} -eq 0 ]]; then
  tasks=(t1_next_due_dates t2_projected_maturity_value t3_surrender_value t4_annual_statement)
fi
options=(--permission-mode auto --output-format stream-json --verbose)
if [[ -n "${AGENT_MODEL:-}" ]]; then options+=(--model "$AGENT_MODEL"); fi
if [[ -n "${MAX_BUDGET_USD:-}" ]]; then options+=(--max-budget-usd "$MAX_BUDGET_USD"); fi

for task in "${tasks[@]}"; do
  mkdir -p "lab/runs/$task"
  trace="lab/runs/$task/agent-$(date +%Y%m%dT%H%M%S).jsonl"
  echo "== $task  (trace: $trace)"
  prompt="Use the skill rule-discovery on the task $task. Read lab/runs/$task/notes.md first if it exists. Follow the
loop of the skill until one of its stop conditions, then verify (step 5), let t5 see the task if it scores well
(step 6) and write the notes (step 7). Change only the function of $task (in starter_kit/my_solution/submission.py or its module of tasks/)
and the rule modules it uses, so that the other tasks keep their score. End with the score of $task (total and holdout)."
  claude -p "${options[@]}" "$prompt" </dev/null >"$trace" || echo "   the session ended with an error, see the trace"
  python3 - "$trace" <<'EOF'
import json, sys
events = [json.loads(line) for line in open(sys.argv[1], encoding="utf-8") if line.startswith("{")]
end = next((e for e in reversed(events) if e.get("type") == "result"), {})
print(end.get("result") or "(no result: see the trace)")
print(f"   {end.get('num_turns', '?')} turns, {end.get('total_cost_usd') or 0:.2f} USD, session {end.get('session_id', '?')}")
EOF
done
