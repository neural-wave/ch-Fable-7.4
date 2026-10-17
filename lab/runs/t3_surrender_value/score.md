# score of t3_surrender_value (code:216aee470009)

Exact rows: 6137 / 6153 (holdout 1238 / 1241); keys computed for target policies but not in the target: 0; 30.9 s

## surrender_value

ok 6137, missing 0, noise 4 (policies listed in NREXCP: 2)
| label | rows | examples |
|---|---|---|
| x1.00 | 7 | [('BL10000321', datetime.date(2025, 12, 31)), ('BL10000694', datetime.date(2025, 12, 31)), ('BL10001063', datetime.date(2020, 4, 30))] |
| x1.01 | 5 | [('BL10000768', datetime.date(2020, 4, 30)), ('BL10001756', datetime.date(2025, 12, 31)), ('BL10004276', datetime.date(2025, 12, 31))] |
| noise | 4 | [('BL10001080', datetime.date(2020, 4, 30)), ('BL10001820', datetime.date(2025, 12, 31)), ('BL10002328', datetime.date(2020, 4, 30))] |
Where it is wrong: optimal tree errors 11, leaves 3 on {BR_REGIO@RK_ENDDT, BR_REGIO@valuation_date}
  BR_REGIO@RK_ENDDT = SUD and BR_REGIO@valuation_date = NRD -> x1.00 (1 rows, 0 of them not x1.00), e.g. [('BL10004914', datetime.date(2020, 4, 30))]
  conflicting vector {'BR_REGIO@RK_ENDDT': 'MIT', 'BR_REGIO@valuation_date': 'MIT'}: {'ok': 1365, 'x1.00': 2}; example ['BL10000694', datetime.date(2025, 12, 31)]
  conflicting vector {'BR_REGIO@RK_ENDDT': 'OST', 'BR_REGIO@valuation_date': 'OST'}: {'ok': 1233, 'x1.00': 1, 'x1.01': 1}; example ['BL10001897', datetime.date(2020, 4, 30)]
  conflicting vector {'BR_REGIO@RK_ENDDT': 'SUD', 'BR_REGIO@valuation_date': 'SUD'}: {'ok': 1232, 'x1.00': 1}; example ['BL10001063', datetime.date(2020, 4, 30)]
