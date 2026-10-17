# 006 · t2_projection_year · from the findings of round r1 to the rule

**Step:** findings → holes → search → code, six times. **LLM:** Claude Code. Every hole below was proposed
after a finding and decided by `formulas.fill_holes` on 80 % of the policies, checked on the other 20 %.

## r1 → the two kinds of policy

`reports/t2_projection_year/r1.md` (5058 right, 73982 wrong):

- **r1/T1** `PD_SRPSCL <= 2.5` (the regular-premium products FK, FX): 63741 of 63741 wrong
- **r1/T3, T4** single premium, first event (the start date) up to 2007-08-16: 4817 of 4835 wrong
- **r1/T2, T5** single premium after 2007-08-16: half right

Prompt: start where the rule is closest (the single premiums after the split date) and search the holes there.

`r1-search-single`: **S1** half up, decimal growth (28 and 16 digits tie), nearest age, parameters on PH_APPDT:
7890 / 8140, held out 2252 / 2324. `r2-search-age`: of the six age conventions, nearest and months tie.

## r2 → one pot, and the system conversion

- `r2-regular.md`: the regular premiums are all wrong with two pots. `r2-search-regular`: **S1** one pot (the
  management charge at CG_AMCP2 on the whole value): 35896 / 36376; two pots: 0. The single premium product has
  PD_INIMON = 0, so it never had a second pot to test.
- `r2-search-old`, the policies started up to 2007-08-16 (r1/T3, T4): **S1** cut off instead of half up:
  18751 / 19505; half up: 75. The split date of r1 lies just after the system conversion (event 800,
  2007-08-11): the old system cut amounts off, Neuron NG rounds half up, as the story warns.

Prompt: make the rounding a property of the system that made the offer.

`r3-search-era`: **S1** cut off when PH_APPDT is up to the conversion, half up after: 62657 / 64021, held out
14575 / 15019 (one convention for all: 43861).

## r3 → the sum at risk of option A

`r3.md` (1808 wrong, mostly ±1–3 cents): **r3/T1** old insured, small sum insured, late policy years: 889 of
6409 wrong. The breakdown of the wrong rows by the tariff key: 1493 of 1808 have option A (death benefit 101 %
of the value, so the sum at risk is 1 % of it). Holes: whether 1 % of the value is rounded to the cent and
where the risk charge is rounded (once, yearly, after every factor, a monthly rate to 6–10 decimals).

`r4-search-risk`: **S1** 1 % of the value kept exact, one rounding at the end: 63454 / 64021, held out
14788 / 15019. Every intermediate rounding is worse.

## r4 → impossible birth dates and the old age convention

`r4.md` (798 wrong, now in whole policies): **r4/T1** birth day of month <= 12, older insured. 29 policies:

- 8 have a birth date the decoder rejects (31 April, 30 February: the profile check `undecodable`), so no age.
  `r5-search-age`: clamped to the month end or rolled into the next month give the same ages: +150 rows.
- the other 21 were offered by the old system and are right with an entry age one higher (a diagnostic run with
  the age shifted by −1 and +1). Their start dates lie about half a year after a birthday: the old system rounds
  the age in days.

`r5-search-era-age`: the age convention as a pair (old system, Neuron NG): **S1** (days / 365 rounded half up,
nearest birthday), the system decided by PH_APPDT: 64021 / 64021, held out 14998 / 15019 (the start date as
the deciding date: 189 fewer).

## r5 → the day of the conversion

The one wrong held-out policy, BL10002438, was applied for on 2007-08-11, the day of the conversion.
`r6-search-boundary`: **S1** the conversion day belongs to Neuron NG: 64021 / 64021, held out 15019 / 15019. It
matches t1, where the schedule starts on or after the conversion event.

## Result

`projection.py` defaults: parameters on PH_APPDT, one pot, ages (days / 365 rounded, nearest birthday), rounding
(cut off, half up), the system decided by PH_APPDT on or after event 800, decimal growth with 28 digits, the
exact sum at risk, one rounding of the risk charge, impossible birth days clamped. t2_projection_year: 79040 of
79040.

The maturity value is the value after the last month (`maturity_values`): 3011 of 3019
(`reports/t2_projected_maturity_value/r1.md`). The 8 others differ by whole francs (1261 to 4855), with no
condition but an exception log entry (r1/T1 `EX_TSTMP`): changed by hand, input for t5.
