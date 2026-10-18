#!/usr/bin/env bash
# The lab pipeline, then OpenCode as its agent: one task after the other, because they all edit
# starter_kit/my_solution/submission.py. For each task the script itself runs, before any model sees the task:
#   lab run      steps 1-4, 6, 7: profiling, clustering, optimal trees, pool, exact score, residuals
#   lab suggest  step 5, only when the report shows a missing feature (conflicting vectors, "Fit another cluster")
#   lab score    the exact score of the function now in submission.py, and where it is wrong
# Their output goes to lab/runs/<task>/pipeline.md. Then an OpenCode session on the open-weights model of .env.llm
# continues the loop of the skill rule-discovery from step 2, and the script scores the task again.
# t7 has no target values: the pipeline runs on the pseudo-target t7_payout_taxes (the tax types NRTAXB books on
# each payout) and `lab t7check` takes the place of `lab score`.
# Usage: scripts/opencode-tasks.sh [task ...]    default: the tasks t1 to t4 (t0 is done); t7 for the tax audit
# The trace of each session is lab/runs/<task>/agent-<time>.jsonl.
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
tasks=("$@")
if [[ ${#tasks[@]} -eq 0 ]]; then
  tasks=(t1_next_due_dates t2_projected_maturity_value t3_surrender_value t4_annual_statement)
fi

lab() { (cd "$root/lab" && uv run lab "$@"); }

for task in "${tasks[@]}"; do
  if [[ "$task" == t7* ]]; then
    task=t7_payout_taxes
    check=(t7check) score_line="taxed or not as NRTAXB|same tax types as NRTAXB|the function fails"
    goal="The task is t7 of such.pdf: the functions t7_tax_payout and t7_tax_annual (in
the package starter_kit/my_solution/taxes/). It has no target values: the pipeline ran on the pseudo-target t7_payout_taxes,
one yes/no value per tax type that NRTAXB books on each payout, so its trees say when Neuron withheld which tax. Use
them for the conditions of the code; the amounts come from the rates of NRTAXR. Score every change with
uv run lab t7check (consistency with NRTAXB on every payout and year; the two examples of such.pdf are a sanity
check only, do not fit the code to them). lab t7check takes about two minutes: give its shell command a timeout of
600000 ms. Keep a change only if lab t7check does not get worse; run it after your last edit too. Change only
the package taxes/, so that the other tasks keep their score."
  else
    check=(score "$task") score_line="Exact rows"
    goal="Change only the function of $task (in starter_kit/my_solution/submission.py) and
the rule modules it uses, so that the other tasks keep their score. End with the score of $task (total and holdout)."
  fi
  runs="$root/lab/runs/$task"
  mkdir -p "$runs"
  pipeline="$runs/pipeline.md"
  echo "== $task"

  echo "   steps 1-4, 6, 7: lab run"
  { echo "# lab run $task"; echo; lab run "$task" 2>&1; } >"$pipeline"
  if grep -q "conflicting vector (" "$runs/report.md" ||
     grep "Fit another cluster" "$runs/report.md" | grep -qv "missing): none\."; then
    echo "   step 5: lab suggest"
    { echo; echo "# lab suggest $task"; echo; lab suggest "$task" 2>&1 || echo "step 5 failed: see the error above"; } >>"$pipeline"
  fi
  echo "   the code now: lab ${check[*]}"
  { echo; echo "# lab ${check[*]}"; echo; lab "${check[@]}" 2>&1 || echo "lab ${check[*]} failed: see the error above"; } >>"$pipeline"
  grep -E "$score_line" "$pipeline" | sed 's/^ */   before: /' || true
  backup="$runs/before-agent-$(date +%Y%m%dT%H%M%S)"  # the code as the agent found it, to restore by hand if needed
  mkdir -p "$backup" && cp "$root"/starter_kit/my_solution/*.py "$backup"/

  trace="$runs/agent-$(date +%Y%m%dT%H%M%S).jsonl"
  echo "   agent (trace: $trace)"
  prompt="Use the skill rule-discovery on the task $task. The pipeline already ran: lab/runs/$task/pipeline.md has
the output of lab run (steps 1-4, 6, 7), of lab suggest (step 5, when the report showed a missing feature) and of
lab ${check[*]} (the code now in submission.py). Read it first, and lab/runs/$task/notes.md if it exists. Then
follow the loop of the skill from step 2 (Decide) until one of its stop conditions: every change is a feature
(lab feature), a freeze (lab freeze) or a change of the code scored with lab ${check[*]}. Verify (step 5), let t5 see
the task if it scores well (step 6) and write the notes (step 7). $goal"
  (cd "$root" && "$root/scripts/opencode-open.sh" run --auto --format json --title "$task" "$prompt" </dev/null >"$trace") ||
    echo "   the session ended with an error, see the trace"

  echo "   after the agent: lab ${check[*]} (the code before the agent: $backup)"
  after="$(lab "${check[@]}" 2>&1 || true)"
  grep -E "$score_line" <<<"$after" | sed 's/^ */   after: /' || { echo "   lab ${check[*]} failed:"; tail -5 <<<"$after"; }
done
