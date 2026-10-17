# t4_annual_statement, r1-noise

The differences of round r1 (the entry charge in the year of the first trade date): an unfound rule (r2-search-entry) and hand edits together.

## Findings

- **t4_annual_statement/r1-noise/N1** isolated 19 of 56 differences as anomalies, 12 of them in whole francs
- **t4_annual_statement/r1-noise/N2** NREXCP lists 16 of the differing entities: 10 isolated, 6 not

## Isolated (most common differences)

- premiums: [{'DIFF': 0, 'ROWS': 19}]
- entry_charges: [{'DIFF': 0, 'ROWS': 12}, {'DIFF': 102, 'ROWS': 1}, {'DIFF': -86, 'ROWS': 1}, {'DIFF': -436320, 'ROWS': 1}, {'DIFF': -102, 'ROWS': 1}]
- admin_fees: [{'DIFF': 0, 'ROWS': 7}, {'DIFF': -13600, 'ROWS': 2}, {'DIFF': -4500, 'ROWS': 2}, {'DIFF': -2100, 'ROWS': 2}, {'DIFF': -2300, 'ROWS': 1}]
- management_fees: [{'DIFF': 0, 'ROWS': 19}]
- risk_charges: [{'DIFF': 0, 'ROWS': 19}]
- total_charges: [{'DIFF': -4500, 'ROWS': 2}, {'DIFF': -2100, 'ROWS': 2}, {'DIFF': -13600, 'ROWS': 2}, {'DIFF': -14700, 'ROWS': 1}, {'DIFF': -86, 'ROWS': 1}]

## Not isolated (most common differences)

- premiums: [{'DIFF': 0, 'ROWS': 37}]
- entry_charges: [{'DIFF': 0, 'ROWS': 8}, {'DIFF': -822, 'ROWS': 1}, {'DIFF': 510, 'ROWS': 1}, {'DIFF': 162, 'ROWS': 1}, {'DIFF': -162, 'ROWS': 1}]
- admin_fees: [{'DIFF': 0, 'ROWS': 29}, {'DIFF': -5600, 'ROWS': 1}, {'DIFF': -6600, 'ROWS': 1}, {'DIFF': -11500, 'ROWS': 1}, {'DIFF': -5300, 'ROWS': 1}]
- management_fees: [{'DIFF': 0, 'ROWS': 37}]
- risk_charges: [{'DIFF': 0, 'ROWS': 37}]
- total_charges: [{'DIFF': -36, 'ROWS': 1}, {'DIFF': -30, 'ROWS': 1}, {'DIFF': 162, 'ROWS': 1}, {'DIFF': -340, 'ROWS': 1}, {'DIFF': -12300, 'ROWS': 1}]
