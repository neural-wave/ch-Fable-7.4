# score of t0_commission (code:7591098ba6b8)

Exact rows: 224418 / 225858 (holdout 43880 / 44052); keys computed for target policies but not in the target: 0; 1.7 s

## amount

ok 224418, missing 0, noise 76 (policies listed in NREXCP: 6)
| label | rows | examples |
|---|---|---|
| x0.67 | 515 | [('BL10000309', 1), ('BL10000309', 2), ('BL10000309', 3)] |
| x2.00 | 424 | [('BL10000058', 1), ('BL10000058', 2), ('BL10000612', 1)] |
| x1.33 | 164 | [('BL10000758', 1), ('BL10000758', 2), ('BL10000758', 3)] |
| x1.50 | 141 | [('BL10002422', 1), ('BL10002422', 2), ('BL10002422', 3)] |
| x0.75 | 120 | [('BL10003331', 1), ('BL10003331', 2), ('BL10003331', 13)] |
| noise | 76 | [('BL10000237', 41), ('BL10000968', 1), ('BL10000968', 2)] |
Where it is wrong: optimal tree errors 121, leaves 7 on {EC_RATE@PR_RCVDT, BR_TIER}
  EC_RATE@PR_RCVDT = 0.050000 and BR_TIER != A and BR_TIER = B -> x1.33 (165 rows, 1 of them not x1.33), e.g. [('BL10000758', 1), ('BL10000758', 2)]
  EC_RATE@PR_RCVDT = 0.050000 and BR_TIER != A and BR_TIER != B -> x2.00 (424 rows, 0 of them not x2.00), e.g. [('BL10000058', 1), ('BL10000058', 2)]
  EC_RATE@PR_RCVDT != 0.050000 and EC_RATE@PR_RCVDT = 0.020000 and BR_TIER = B -> x0.67 (515 rows, 0 of them not x0.67), e.g. [('BL10000309', 1), ('BL10000309', 2)]
  EC_RATE@PR_RCVDT != 0.050000 and EC_RATE@PR_RCVDT != 0.020000 and BR_TIER != B -> x1.50 (260 rows, 120 of them not x1.50), e.g. [('BL10002422', 1), ('BL10002422', 2)]
  conflicting vector {'EC_RATE@PR_RCVDT': '0.050000', 'BR_TIER': 'B'}: {'x1.33': 164, 'x1.50': 1}; example ['BL10004187', 1]
