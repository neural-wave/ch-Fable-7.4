# score of t2_projected_maturity_value (code:aa8de95b9eda)

Exact rows: 3011 / 3019 (holdout 622 / 622); keys computed for target policies but not in the target: 0; 1.7 s

## maturity_value

ok 3011, missing 0, noise 4 (policies listed in NREXCP: 4)
| label | rows | examples |
|---|---|---|
| x1.01 | 4 | [('BL10000128',), ('BL10002196',), ('BL10002973',)] |
| noise | 4 | [('BL10001762',), ('BL10003323',), ('BL10003583',)] |
Where it is wrong: optimal tree errors 3, leaves 4 on {PH_FREQ, RK_TARKEY[3], BR_CHNL}
  PH_FREQ = H and RK_TARKEY[3] = M and BR_CHNL = DI -> x1.01 (1 rows, 0 of them not x1.01), e.g. [('BL10002196',)]
  conflicting vector {'PH_FREQ': 'M', 'RK_TARKEY[3]': 'W', 'BR_CHNL': 'BR'}: {'ok': 224, 'x1.01': 1}; example ['BL10000128']
  conflicting vector {'PH_FREQ': 'M', 'RK_TARKEY[3]': 'M', 'BR_CHNL': 'BR'}: {'ok': 212, 'x1.01': 1}; example ['BL10004278']
  conflicting vector {'PH_FREQ': 'Q', 'RK_TARKEY[3]': 'W', 'BR_CHNL': 'BR'}: {'ok': 74, 'x1.01': 1}; example ['BL10002973']
