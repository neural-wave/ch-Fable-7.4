# 009 · t3_booking (ADM, AMC, RSK) · from the story to round 1

**Step:** story → first rule as a sketch with holes, and a way to check it one run at a time. **LLM:** Claude
Code.

## Input

The task text of t3 (see `007-t3-story.md`): on every monthly anniversary Neuron takes the admin fee, the
management charge (a different rate per pot) and the risk charge by cancelling units in all funds and pots; the
customer orders are complete; reversed events and technical corrections can be ignored. The glossary: the risk
charge is the monthly price for the death benefit, by the sum at risk and the death probability.

What t2 already found (`006-t2-findings.md`): the risk charge on the sum at risk of the tariff option (A 1 % of
the value, B sum insured less value, C sum insured), the death probability of the age convention of the system,
loading and smoker factor, one rounding at the end; the old system cuts off, Neuron NG rounds half up. What the
premium bookings found (`008-t3-premium-findings.md`): exact cross rates, the trade date tells the system. What
the customer orders found (`order_bookings/r1-search`): the bid price of the last price day on or before the
trade date redeems units.

Tables: NRCHRG (CG_ADMFEE, CG_AMCP1, CG_AMCP2 per tariff family and generation, with validity), NRAGRE (fee type
AMC), NREVNT (event 300, the charge runs), NRBOOK (the ADM, AMC and RSK bookings, without amounts).

## Prompt 1: how to check a charge run on its own

A run charges a share of the value of every fund and pot, so it can only be checked on the units held before
it, and one wrong rule would spoil every later run. Make the holdings before every run known exactly, from what
Neuron booked: the units of t3_booking for the premium and charge bookings, the units of NRBOOK for the complete
customer orders, without reversed events and technical corrections (teacher forcing, §6).

## Output 1

`tools/detective/replay.py`: `known_units` and `holdings_before` (cumulative units per fund and pot, an asof join
on the position of the run); the order of bookings and runs is a hole (`ordering`: by event number, by day and
event, or by day with every run before the bookings of its day).

## Prompt 2: the charge run

Write the charge run the story describes, on the replayed holdings: one booking per charge, fund and pot. Every
open choice becomes a hole.

## Output 2

`charges.py`, round 1: the value of a fund and pot at the bid price of the run date in the policy currency; ADM
the fee of the tariff valid on the run date shared by value; AMC a twelfth of the yearly rate of the pot (or of an
individual AMC rate) on the value; RSK the t2 formula on the whole value of the run, shared by value; the units
cancelled at the bid price.

Holes:

- `rounding`: half up or cut off, or a pair by system
- `valued`: the value of a fund and pot in cents or in millionths of a cent
- `parameter_day`: the date whose tariff counts (the run date, the application date)

`reports/t3_booking_adm_amc/r1-search.md`: 3330756 of 3661465 admin fee and management charge bookings right, the
price always; **S1** the rounding by system, cents, the tariff of the run date: 2663960 / 2928356. The findings
that followed are in `010-t3-charges-findings.md`.
