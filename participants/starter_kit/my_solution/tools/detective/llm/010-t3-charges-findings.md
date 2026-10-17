# 010 · t3_booking (ADM, AMC, RSK) · from the findings of round r1 to the rule

**Step:** findings → holes → search → code. **LLM:** Claude Code. Every hole was proposed after a finding and
decided by `formulas.fill_holes` on 80 % of the policies, checked on the other 20 %, on the holdings replayed
before every run (`replay.holdings_before`).

## The management charge of the old system

`reports/t3_booking_amc/r1.md` (145463 wrong): **r1/C1** a change point at the conversion: 65.1 % wrong before,
1.3 % after. Before it, the target over a twelfth of the yearly charge is 1.033 after a month of 31 days, 1.000
after 30, 0.967 after 29 and 0.933 after 28 (median per month length): days over 360.

- `r1-search-accrual`: **S1** days over 360 in the old system, a twelfth in Neuron NG: 1441857 / 1467108
- `r2-search-accrual` (after r2/T1, anniversaries on the 30th or 31st): **S1** the days since the previous run:
  1446747 / 1467108
- `r5-search-accrual` (after r5/T1: the first run of old policies starting on the 31st, 30 days from 2002-10-31
  to 2002-11-30): **S1** the days since the previous monthly anniversary of the start date: 1467108 / 1467108

## The admin fee shares

`reports/t3_booking_adm/r2-search-remainder.md`: Neuron's admin fee bookings of a run add up to the tariff fee
(all but 5 of 397842 runs), round 2's do not in 149132 runs. **S1** the missing cents to the fund and pot with the
largest value, the shares rounded by system: 1427910 / 1461248.

## Units and value from the exact cross rate

`t3_booking_adm_amc/r2-search-units` (8885 management charges with the right amount and units off by one
millionth): **S1** units from the exact cross rate: 2882990 / 2928356. `r2-search-value`: **S1** the value from
the exact cross rate too, kept in cents: 2883152.

## What a run sees

`t3_booking_adm/r3.md`, `t3_booking_amc/r3.md`: the wrong charges are of runs on the 30th or 31st and of monthly
bank transfers, a premium received shortly before the run and bought after it.
`t3_booking_adm_amc/r3-search-order`: **S1** a run sees the bookings traded before its day: 2906371 / 2928356.

`t3_booking_adm/r4.md`, `t3_booking_amc/r4.md`: BL10001304 had a switch-in of a technical correction (event 990)
in its holdings; the task says to ignore them. Without them (`r5.md`): ADM 1827502 / 1827505, AMC 1833882 /
1833960 (the 78 left are fixed by r5-search-accrual above).

## The risk charge

- `t3_booking_rsk/r1-search`: **S1** a twelfth of the year, the age convention of t2 by system, the age at the
  start plus the completed policy years: 714346 / 764890
- `r1-search-value` (after r1/T1: large sums insured, too low by 1–5 cents, a larger sum at risk comes from a
  smaller value): **S1** the sum at risk on the value after the admin fee and the management charge of the run:
  760776 / 764890
- `r2-search-age` (after r2/T1: insured born on day 1 to 12, old policies running after the conversion): **S1**
  the age convention of the system that made the offer (PH_APPDT, as in t2): 764888 / 764890, held out 190855 /
  190856

## When the value runs out

`t3_booking_charges/r1.md`: 4617205 of 4617211 charge bookings right. The 6 wrong are two runs of paid-up
policies: in BL10001005 (2021-10-01) the admin fee took exactly the value of every fund (754 of 850) while a
management charge of 1 cent was still booked; in BL10004387 (2020-12-01) the risk charge took exactly what the
admin fee and the management charge left (199 of 635).

`r1-search-limit`: **S1** the admin fee no more than the value, the risk charge no more than what is left:
3693246 / 3693246, held out 923965 / 923965 (also limiting the management charge: one less; no limit: three less).

## Which charges are booked

The amount target leaves out a booking Neuron did not make. `bookings.presence` makes every run, fund and pot
held and charge type a candidate, booked when NRBOOK has it (`reports/charge_bookings`). Two RSK amounts of −1 cent
(the remainder correction of shares rounded up to 1 cent each) have no booking.

`charge_bookings/r1-search-booked`: **S1** only positive amounts are booked: 4470186 / 4470186, held out 1034553 /
1034553 (every amount but 0: two extra). `charge_bookings/r2`: 5504739 / 5504739 candidates right.
