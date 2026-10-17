# 003 · t1_next_due_dates · from the story to round 1

**Step:** story → first rule. **LLM:** Claude Code.

## Input

The task text of t1:

> For every regular-premium policy in state 10 on the extract date 2026-06-30, calculate all premium due dates
> of the following year (after 2026-06-30, up to and including 2027-06-30), each with its collection date.
> - The due dates follow the premium frequency from the start date. There is no due date on or after the
>   maturity date.
> - Neuron maintains the schedule itself. The past due dates in NRPREM.PR_DUEDT show how it behaves.
> - Assume that nothing changes on the policy after the extract date.

Key terms: the collection date is the day the money is taken from the customer's account; a business day is a
working day in the local calendar. Code lists: FREQ J yearly, H half-yearly, Q quarterly, M monthly, E single;
PAYMT LS direct debit, UB bank transfer; STATE 10 in force, premium paying.

## Prompt

Write the simplest rule that the story describes. Where it leaves a choice open, take the plainest reading.

## Output

`schedule.py`, round 1: the policy version valid on the extract date, state 10, frequency not E; due dates =
start date + k periods (calendar months, a day 31 clamped to the end of a shorter month), before maturity;
collection date = due date. The story says the past due dates "show how it behaves" but not how: that is left
to the discovery loop.
