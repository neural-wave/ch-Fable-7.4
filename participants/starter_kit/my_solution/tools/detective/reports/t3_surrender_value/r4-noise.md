# t3_surrender_value, r4-noise

The differences that remain with the final rule.

## Findings

- **t3_surrender_value/r4-noise/N1** isolated 3 of 16 differences as anomalies, 3 of them in whole francs
- **t3_surrender_value/r4-noise/N2** NREXCP lists 11 of the differing entities: 2 isolated, 9 not

## Isolated (most common differences)

- surrender_value: [{'DIFF': -1500, 'ROWS': 1}, {'DIFF': -49800, 'ROWS': 1}, {'DIFF': -49900, 'ROWS': 1}]
- policy_value: [{'DIFF': 0, 'ROWS': 3}]

## Not isolated (most common differences)

- surrender_value: [{'DIFF': -17500, 'ROWS': 1}, {'DIFF': -3400, 'ROWS': 1}, {'DIFF': -48400, 'ROWS': 1}, {'DIFF': -15800, 'ROWS': 1}, {'DIFF': -2900, 'ROWS': 1}]
- policy_value: [{'DIFF': 0, 'ROWS': 13}]
