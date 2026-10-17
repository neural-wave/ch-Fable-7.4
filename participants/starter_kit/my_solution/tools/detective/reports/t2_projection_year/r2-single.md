# t2_projection_year, r2-single

Round 2 on the single premium policies after 2007-08-16: nearest age, half up, decimal growth (r1-search-single/S1).

## Rows

right: 10142, wrong: 322

## Most common differences

- value: 1 (171), -1 (82), 2 (41), -2 (6), 3 (4), -3 (2), 149 (1), 61 (1)

## Conditions (decision tree on the wrong rows)


## Change points

- **t2_projection_year/r2-single/C1** PS_BIRTH between 1958-02-26 and 1958-07-09: wrong 11.6% before, 1.2% after (explains 5.1%)
- **t2_projection_year/r2-single/C2** PS_BIRTH@RK_BEGDT between 1960-09-09 and 1960-09-16: wrong 9.1% before, 1.3% after (explains 3.5%)
- **t2_projection_year/r2-single/C3** PS_BIRTH@RK_ENDDT between 1960-09-09 and 1960-09-16: wrong 8.7% before, 1.4% after (explains 3.0%)
- **t2_projection_year/r2-single/C4** EV_EFFDT:last between 2026-06-02 and 2026-06-03: wrong 3.3% before, 2.1% after (explains 1.5%)
- **t2_projection_year/r2-single/C5** AD_VLDFR@RK_BEGDT between 2017-09-16 and 2017-10-09: wrong 3.1% before, 0.0% after (explains 1.2%)
- **t2_projection_year/r2-single/C6** BR_SINCE@last between 1998-01-28 and 1998-02-26: wrong 2.8% before, 3.4% after (explains 1.0%)
- **t2_projection_year/r2-single/C7** BR_SINCE@RK_BEGDT between 1998-01-28 and 1998-02-26: wrong 2.8% before, 3.4% after (explains 1.0%)
- **t2_projection_year/r2-single/C8** BR_SINCE@RK_ENDDT between 1998-01-28 and 1998-02-26: wrong 2.8% before, 3.4% after (explains 1.0%)
- **t2_projection_year/r2-single/C9** AD_CHGTS@RK_BEGDT between 2018-07-25T12:37:46.000000 and 2018-07-26T08:35:08.000000: wrong 3.1% before, 0.0% after (explains 1.0%)
- **t2_projection_year/r2-single/C10** AL_VLDTO:first between 2018-01-17 and 2018-03-23: wrong 3.0% before, 3.1% after (explains 1.0%)
