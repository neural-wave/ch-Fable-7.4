# t6 visualization: plan

Three views, all fed by the same lab artifacts, collected in one offline `lab/runs/atlas.html`:

1. **Before / after** of every rule found: switch one rule off, score again, show where the wrong rows were.
2. **Policy timeline**: one policy month by month (premiums, charges, units, value) against the diagnostic files,
   with a marker on the first divergence.
3. **The journey of 100 francs**: a scrolling story for a person who knows nothing about computers or insurance,
   in English with an Italian toggle. Chapters 1-7 explain what Neuron does with the customer's money, 8-9 how the
   rules were found and what the manual corrections are.

## Decisions

- Everything lives in `lab` (`neuronlab/viz.py`, `lab viz`) and reads only pipeline artifacts, so it works for a
  new target too.
- A rule is switched off by a **rule card** (`lab/rules/<task>.json`): a text replacement in a scratch copy of the
  submission, scored with `lab score --submission`, as `tests/test_score.py` already does. The submission itself
  is never changed, so its maintainability index stays the same.
- Plotly, with plotly.js embedded once: the atlas opens without a network.

## Tasks (15 hours, 2 of them buffer)

| hours | task | done when |
|---|---|---|
| 0-1 | T1 `lab score` writes `diffs.parquet` (key, target, computed, numeric difference) | t0: 225858 rows, difference 0 on every ok row |
| | T2 `lab viz` skeleton, `atlas.html`, chart: distribution of differences per task | opens offline, smoke test |
| 1-4 | T3 rule cards and ablation: system change 2007 (all tasks), tier on money date (t0), nearest birthday (t2), entry charge by trade year and risk cap (t4) | each card: before N wrong rows, after 0, chart of where they were |
| | T4 contribution of each rule (leave one out) | one bar chart per task |
| | **checkpoint 1**: review the before / after charts | |
| 4-7 | T5a trace subclass of `FundAccounting` (no change to the submission) | events per month for one policy |
| | T5b `lab viz policy <id>` with the diagnostic overlays and the first divergence | exact policy: no marker; outlier: marker in the right month |
| | **checkpoint 2**: try two policies | |
| 7-11 | S1 `story.json`: a real policy picked automatically (crosses 2007, monthly, a holiday shift, exact everywhere) | |
| | S2 the story page, EN/IT, light/dark, phone width | |
| | S3 "grandma test": a fresh agent reads it as a lay person; banned-word list, glossary | no unexplained term left |
| | **checkpoint 3**: read the story | |
| 11-13 | T6 atlas index, T7 README section and PNGs, T8 `package.sh`, size < 15 MB, `check.py` | |
| 13-15 | buffer | |

Minimum if time runs out: T1, T2, T3, T5a, S1, S2, T8.
