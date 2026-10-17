# 007 · t3_booking (PRM) · from the story to round 1

**Step:** story → first rule as a sketch with holes. **LLM:** Claude Code.

## Input

The task text of t3:

> - Charges cancel units: On every monthly anniversary, Neuron takes the admin fee, the management charge (with
>   a different rate per pot) and the risk charge by cancelling units in all funds and pots. These bookings exist
>   in NRBOOK, but their amounts and units are missing, so you have to calculate them.
> - Customer orders are complete: Fund switches, withdrawals and surrenders are orders of the customer, and their
>   bookings are complete in the export. Reversed events and technical corrections can be ignored.
> - Surrender value: Value the units at the redemption price (the last price on or before the valuation date) in
>   the policy currency.

From t4: "entry charges on the premiums invested in the year (trade date)". From the glossary: money date
(PR_RCVDT, BK_RCVDT), trade date (BK_TRDDT), business day "a working day in the local calendar", pot 1 the
initial units of the first PD_INIMON months. From the general text: NRBOOK is there to understand and debug the
accounting, not as a source for the formula.

The profile of NRBOOK (`profile.py`): the premium bookings (PRM) have BK_RCVDT, BK_TRDDT, BK_PRCDT, BK_FNDID and
BK_POTCD but no BK_AMTPC, BK_FXRAT, BK_PRICE or BK_UNITS; the customer orders (SWO, SWI, WDR, SUR, DTH) have all
of them. Tables linked to the premium items (`schema.relations`): NRPREM (due date, money date, amount received),
NRALLO (allocation sets with versions and validity), NRBROK (broker tier), NRENTC (entry rate per tier), NRAGRE
(individual agreements, fee type ENT), NRFPRC (bid and ask price per fund and day, with publication timestamps),
NRFXRT (exchange rates), NRFUND (fund currency).

## Prompt 1: the market conventions, from the bookings that are complete

The customer orders are complete in the export: let them say which price and which exchange rate Neuron uses,
before the premium bookings are written. Holes: the price column, the date of the exchange rate and its rounding.

`reports/order_bookings/r1-search.md`: **S1** the bid price of the last price day on or before the trade date
(latest publication), the exchange rate of the trade date rounded half up to millionths: 19964 / 19964, held out
4948 / 4948. This became `market.py` (`prices`, `price_on`, `rate_on`).

## Prompt 2: the premium bookings

Write the premium bookings the story describes, with every open choice as a hole: a premium received buys units
in the funds of the allocation valid on its date, after the entry charge of the broker tier or of an individual
agreement; units of the first PD_INIMON months go to pot 1.

## Output

`premiums.py`, round 1: the paid premium items of t0 (`commission.received_items`, PR_STATE paid), the entry
rate, the allocation with the highest version valid on the date, the amount of a fund as the invested part times
its share, the units at the ask price (the issue price) of the trade date, the trade date the first business day
after the money date.

Holes:

- `day`: the date whose broker, entry charge and allocation count (PR_RCVDT, PR_DUEDT)
- `rounding`: the cents and the millionths, half up or cut off, or a pair by system (as t2 found)
- `era_day`: the date that tells the system of a booking
- `price`: the price column that buys units (FP_ASKPR, FP_BIDPR, FP_MIDPR)

`reports/t3_booking/r1-search-premium.md`: round 1 has 297504 of 407636 premium bookings right, the price always;
**S1** the rounding by system on the money date: 258194 / 326017, held out 64609 / 81619. The findings that
followed are in `008-t3-premium-findings.md`.
