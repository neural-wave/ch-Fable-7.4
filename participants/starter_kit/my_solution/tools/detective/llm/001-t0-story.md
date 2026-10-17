# 001 · t0_commission · from the story to round 1

**Step:** story → first rule (§9.2 "Start with the story").
**LLM:** Claude Code, in the session that rebuilt the solution on branch `point6`.

## Input

The task text of t0 in `Lifeware_Challenge.pdf`:

> Goal: calculate the commission for every premium item that was received and not reversed later.
> - The commission is a percentage of the received premium amount (PR_AMTRC).
> - The rate is in NRCOMR. It depends on the broker tier and on the type of premium: E for single-premium
>   policies, L for regular-premium policies.
> - A policy can change its broker over the years.

From the tools: `spec_for("t0_commission", ("amount",))` anchors the target at NRPREM (PR_POLNR, PR_DUENR);
the relation graph links NRPREM → NRPOLH (versioned) → NRBROK; the code list PRSTAT says O open, P paid,
R direct debit returned, W written off; FREQ E is single premium.

## Prompt

Write the simplest rule that the story describes, in polars, with exact integer arithmetic. Where the story
leaves a choice open, take the plainest reading and make it a parameter, so the search can test the other
readings instead of guessing.

## Output

`commission.py`, round 1:

- received and not reversed = PR_STATE P
- broker = the last version of the policy (`broker_day=None`): the story says the broker can change, but not
  which version counts
- rate = the NRCOMR row of the tier and premium type valid on the due date (`rate_day="PR_DUEDT"`)
- amount = PR_AMTRC × CR_RATE, rounded half up to the cent (`half_up=True`)

## Result

225858 target rows: 224418 right, 1440 wrong (99.36 %). Next: `discover` round r1.
