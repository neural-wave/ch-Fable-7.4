# t3_surrender_value, r1-noise

The differences of round r1 (the penalty rounded like the value): an unfound rule (the old system rounding the penalty up, r2-search-penalty) and hand edits together.

## Findings

- **t3_surrender_value/r1-noise/N1** isolated 26 of 252 differences as anomalies, 16 of them in whole francs
- **t3_surrender_value/r1-noise/N2** NREXCP lists 12 of the differing entities: 12 isolated, 0 not

## Isolated (most common differences)

- surrender_value: [{'DIFF': -1, 'ROWS': 5}, {'DIFF': 1, 'ROWS': 4}, {'DIFF': -3, 'ROWS': 1}, {'DIFF': -17500, 'ROWS': 1}, {'DIFF': -49800, 'ROWS': 1}]
- policy_value: [{'DIFF': 0, 'ROWS': 26}]

## Not isolated (most common differences)

- surrender_value: [{'DIFF': 1, 'ROWS': 226}]
- policy_value: [{'DIFF': 0, 'ROWS': 226}]
