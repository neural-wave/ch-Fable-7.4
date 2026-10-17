# 008 · t3_booking (PRM) · from the findings of round r2 to the rule

**Step:** findings → holes → search → code, seven times. **LLM:** Claude Code. Every hole was proposed after a
finding and decided by `formulas.fill_holes` on 80 % of the policies, checked on the other 20 %. The target is the
premium part of the diagnostic t3_booking (`diagnostics.part`).

## r2 → the exchange rate

`reports/t3_booking_prm/r2.md` (322803 right, 82666 wrong, 2167 missing): **r2/T1** fund currency not CHF, policy
currency CHF: 47739 of 47759 wrong; **r2/T2** the other way round: 17138 of 17140 wrong. Every wrong row under
T1–T4 has a fund currency other than the policy currency.

`r2-search-fx`: **S1** the rate of the money date, the cross rate kept exact: 323577 / 326017 (rounded to
millionths first: 306147).

## r3 → the trade date

`r3.md` (404597 right, 872 wrong, 2167 missing): **r3/T1, T2** the trade date more than one day after the money
date. 2655 NRBOOK trade dates are one business day later than the calendar says, on no holiday: the fund had no
price on that day.

`r3-search-trade`: **S1** the first day after the money date with a price of the fund: 324867 / 326017; the
Ticino calendar: 323577.

## r4 → the entry charge of individual agreements

`r4.md` (406199 right, 1233 wrong): 827 of the 861 premiums with a wrong split invest one cent less than Neuron;
all have an individual entry rate (NRAGRE ENT, 0.5 % or 1.5 %) whose charge is an exact half cent.

`r4-search-entry`: **S1** the entry charge cut off to the cent: 325425 / 326017 (half down ties; cut off is the
simpler rule).

## r5 → the exchange rate of the eve of the trade date

`r5.md` (406907 right, 525 wrong): 363 bookings with the right amount and other units, mostly where the trade
date is more than one day after the money date. The rate of the money date and the last rate before the trade
date differ only there.

`r5-search-fx`: **S1** the rate of the day before the trade date: 325706 / 326017.

## r6 → the pot

The 204 missing bookings are booked by NRBOOK in the other pot: 145 premiums at the end of the initial period,
due before it and received after it, or the other way round.

`r6-search-pot`: **S1** the money date decides the pot: 325878 / 326017. `r6.md`: 407469 right, 167 wrong.

## r7 → one rounding of the fund amount

160 bookings one cent too high, 152 of them in 4 policies. BL10000260 (2005, old system): 0.5 % of 775.00 is
3.875, Neuron invested 771.12. Neuron NG cut such charges off (581 premiums), the old system rounded them up (24),
so no rounding of the charge alone fits both (`r7-search-entry`, `r7-search-entry-era`: no gain).

`r7-search-split`: **S1** the amount of a fund as one rounding of premium × (1 − entry rate) × share: 326011 /
326017, held out 81618 / 81619.

## r8 → the system of a booking

7 bookings left, all received on 2007-08-10 and traded on 2007-08-13, across the conversion of 2007-08-11:
Neuron NG rounded them.

`r8-search-era`: **S1** the trade date tells the system: 326017 / 326017, held out 81619 / 81619. The premium
bookings are right: 407636 / 407636.
