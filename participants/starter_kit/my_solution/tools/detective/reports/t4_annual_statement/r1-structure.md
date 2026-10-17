# t4_annual_statement, r1-structure

Round r1 of the annual statement (the entry charge in the year of the first trade date): where to look first.

wrong: 56 of 34145

## Permutation importance (wrong rows)

- **t4_annual_statement/r1-structure/I1** EX_TARGET=t4_annual_statement.admin_fees: the ROC AUC drops by 0.079 (± 0.000)
- **t4_annual_statement/r1-structure/I2** EX_TSTMP: the ROC AUC drops by 0.016 (± 0.000)
- **t4_annual_statement/r1-structure/I3** EV_EFFDT@last: the ROC AUC drops by 0.012 (± 0.008)
- **t4_annual_statement/r1-structure/I4** year: the ROC AUC drops by 0.007 (± 0.004)
- **t4_annual_statement/r1-structure/I5** PS_BIRTH@RK_BEGDT: the ROC AUC drops by 0.006 (± 0.006)
- **t4_annual_statement/r1-structure/I6** PH_VLDFR@RK_ENDDT:day: the ROC AUC drops by 0.004 (± 0.001)
- **t4_annual_statement/r1-structure/I7** PH_VLDFR@RK_ENDDT: the ROC AUC drops by 0.004 (± 0.000)
- **t4_annual_statement/r1-structure/I8** PH_CHGTS@last: the ROC AUC drops by 0.003 (± 0.000)
- **t4_annual_statement/r1-structure/I9** PS_BIRTH@RK_BEGDT:year: the ROC AUC drops by 0.002 (± 0.000)
- **t4_annual_statement/r1-structure/I10** EV_EFFDT:last:day: the ROC AUC drops by 0.002 (± 0.001)

## Clusters of the policies

- **t4_annual_statement/r1-structure/K1** 17 policies, wrong 11.0%; apart: EX_TARGET=t4_annual_statement.admin_fees +12.9 sd, EX_TSTMP +7.7 sd, WRONG_SHARE +6.1 sd
- **t4_annual_statement/r1-structure/K2** 1906 policies, wrong 0.1%; apart: PH_VLDFR@RK_ENDDT +0.6 sd, EV_EFFDT@last +0.6 sd, PH_CHGTS@last +0.6 sd
- **t4_annual_statement/r1-structure/K3** 1096 policies, wrong 0.1%; apart: PH_VLDFR@RK_ENDDT -1.1 sd, EV_EFFDT@last -1.1 sd, PH_CHGTS@last -1.1 sd
