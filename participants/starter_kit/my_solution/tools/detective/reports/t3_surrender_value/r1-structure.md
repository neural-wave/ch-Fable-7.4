# t3_surrender_value, r1-structure

Round r1 of the surrender value (the penalty rounded like the value): where to look first.

wrong: 252 of 6153

## Permutation importance (wrong rows)

- **t3_surrender_value/r1-structure/I1** BR_REGIO@RK_BEGDT=NRD: the ROC AUC drops by 0.001 (± 0.000)
- **t3_surrender_value/r1-structure/I2** valuation_date-RK_BEGDT:days: the ROC AUC drops by 0.001 (± 0.000)
- **t3_surrender_value/r1-structure/I3** EX_TARGET=t3_surrender_value.surrender_value: the ROC AUC drops by 0.000 (± 0.000)
- **t3_surrender_value/r1-structure/I4** PH_APPDT@RK_BEGDT: the ROC AUC drops by 0.000 (± 0.000)
- **t3_surrender_value/r1-structure/I5** PR_RCVDT:first:day: the ROC AUC drops by 0.000 (± 0.000)
- **t3_surrender_value/r1-structure/I6** PS_BIRTH@valuation_date:month: the ROC AUC drops by 0.000 (± 0.000)
- **t3_surrender_value/r1-structure/I7** HD_CHGTS@RK_ENDDT: the ROC AUC drops by 0.000 (± 0.000)
- **t3_surrender_value/r1-structure/I8** RK_ENDDT: the ROC AUC drops by 0.000 (± 0.000)
- **t3_surrender_value/r1-structure/I9** RK_BEGDT: the ROC AUC drops by 0.000 (± 0.000)
- **t3_surrender_value/r1-structure/I10** EX_TSTMP: the ROC AUC drops by 0.000 (± 0.000)

## Clusters of the policies

- **t3_surrender_value/r1-structure/K1** 1397 policies, wrong 5.6%; apart: valuation_date-RK_BEGDT:days +0.9 sd, RK_BEGDT -0.9 sd, PH_APPDT@RK_BEGDT -0.9 sd
- **t3_surrender_value/r1-structure/K2** 11 policies, wrong 63.6%; apart: EX_TARGET=t3_surrender_value.surrender_value +16.5 sd, EX_TSTMP +9.8 sd, WRONG_SHARE +5.7 sd
- **t3_surrender_value/r1-structure/K3** 1611 policies, wrong 0.4%; apart: valuation_date-RK_BEGDT:days -0.8 sd, RK_BEGDT +0.8 sd, PH_APPDT@RK_BEGDT +0.8 sd
