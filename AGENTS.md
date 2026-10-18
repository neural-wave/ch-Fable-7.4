# Neuron challenge

Any work on a challenge task (t0_commission to t5_outlier_detection) follows the skill `rule-discovery`
(`.claude/skills/rule-discovery/SKILL.md`): load it first. The first command on a task is
`uv run lab run <task>` in `lab/`, before reading data or writing code: clustering, optimal trees and the exact
score find the rules, the model only steers them. To run several tasks unattended: `scripts/opencode-tasks.sh`.

t7 (the tax audit of `such.pdf`, code in the package `starter_kit/my_solution/taxes/`) has no target values. Its first
command is `uv run lab run t7_payout_taxes` in `lab/`: the pseudo-target of the tax types NRTAXB books on each payout.
Score every change of the t7 code with `uv run lab t7check` (consistency with NRTAXB); the two examples of such.pdf
are a sanity check only, never a rule to fit.
