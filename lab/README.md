# lab: rule discovery for the Neuron migration

The lab finds the formulas of a target with a generic pipeline:
1. profiling of keys and joins (Desbordante);
2. clustering of target/input relations;
3. optimal decision trees;
4. a pool of candidate rules with exact scores;
5. an open-weights language model, only where the trees need a feature that is not in the data yet;
6. exact scoring;
7. a second pass on the residuals.

The winner becomes code in `starter_kit/my_solution/submission.py` through deterministic templates.

## Setup

```bash
cd lab
uv sync                 # Python 3.12, polars, desbordante, scikit-learn, pytest, radon
uv run lab ingest       # typed Parquet copies of legacy/*.csv and targets/*.csv in lab/.cache/
uv run lab audit        # data quality findings
```

The data folders are `../legacy` and `../targets`. The environment variables `NEURON_LEGACY` and `NEURON_TARGETS`
point elsewhere.

## Commands

| Command | What it does |
|---|---|
| `lab run <task>` | steps 1–4, 6, 7 and `report.md` in one go (t0: about 16 s) |
| `lab profile` · `frame` · `cluster` · `tree` · `pool` · `iterate` · `report <task>` | one step |
| `lab pool show <task>` | candidates with their exact scores |
| `lab pool eval <task> <file.json>` | scores a candidate written by hand or by a model |
| `lab feature <task> <name> "<expr>"` | adds one feature in the DSL (e.g. `at(BR_TIER, PR_RCVDT)`) and reruns steps 3, 4 and 7 in `<task>~llm` |
| `lab suggest <task> [--ablate GLOB] [--dry-run]` | step 5 in batch: one request to the open-weights model, at most 3 validated features, exact score before and after |
| `lab freeze <run> [candidate]` | writes the function of the winner into `submission.py` and runs `check.py` |
| `lab score <task> [name=expr ...] [--submission DIR]` | runs the task function of `submission.py` behind a firewall on the target files, gives its exact score and explains its wrong rows with the optimal trees (`score.md`) |
| `lab show <table> COL=VALUE ...` | at most 40 typed rows of a legacy table or target file |
| `lab llm ping` | checks the endpoint and model of step 5 |

## Artifacts of a task (`runs/<task>/`)

| File | Step | Content |
|---|---|---|
| `profile.json` | 1 | keys (UCC), inclusion dependencies, joins (plain or temporal), grain, filter |
| `frame.parquet`, `frame.json` | 1 | one row per target row with every reachable column; lineage of every column |
| `clusters.json`, `labels.parquet` | 2 | best relation, cluster centers, the rounding modes that reproduce each row, noise |
| `trees.json` | 3 | optimal trees, smallest feature sets, equivalent features, conflicting vectors, CART |
| `pool.json` | 4 | cards (leaves) and candidates with exact scores, ties |
| `ledger.jsonl` | 6 | every scored candidate: discovery and holdout score, fingerprint of the right rows |
| `residuals.json`, `outliers.json` | 7 | residuals by kind, noise rows cross-checked with NREXCP |
| `report.md` | – | the summary that a person or the language model reads |
| `score.md` | 6 | `lab score`: exact score of the written function, labels of its wrong rows, where it is wrong |
| `llm/*.json` | 5 | prompt hash, raw answers, validated proposals, score before and after |

Each artifact depends only on the ones before it.

Tasks are the scored targets and the diagnostic files (`t2_projection_year`, `t3_holding`, `t3_booking`). The key
of a diagnostic file is the shortest unique prefix of its header, and its decimal columns are the values. Targets
above one million rows are sampled: a fixed fifth of the policies.

Relations: ratio and difference with an amount, days and months with a date, a constant. The values that come
before it in the target file are inputs too. When nothing gives dense clusters, the value is related to
`previous(value)`, the value of the same policy one step before. The report also lists exact sums among the values,
and approximate relations that no constant reproduces to the cent.

## Exactness

- Amounts are decimals all the way: `N(s)` columns become `Decimal(38, s)`.
- Rounding is done on 128-bit integers in the 7 modes of the `decimal` module. It was checked against `decimal` on
  20,006 values with 0 differences.
- A row counts only if it equals the target, with the same semantics as `scoring.accuracy`.
- One policy in five (`crc32(policy_id) % 5 == 0`) is the holdout.

## Step 5 with an open-weights model

The protocol, endpoint, key and model are in `../.env.llm` (template: `../.env.llm.example`). The default is an
endpoint with the OpenAI API, such as vLLM on a vast.ai instance. `llm.py` speaks that protocol, or the Anthropic
Messages API with `OPEN_PROTOCOL=anthropic`. The model can only propose expressions of the DSL in
`neuronlab/dsl.py`. They are parsed with a restricted `ast`, never evaluated as Python.

OpenCode runs on the same model with `../scripts/opencode-open.sh`. It finds the protocol in
`../.claude/skills/rule-discovery/SKILL.md` as the skill `rule-discovery`. `../scripts/opencode-tasks.sh [task ...]`
runs it without supervision: for each task (default t1 to t4) the script runs `lab run`, `lab suggest` when the
report shows a missing feature, and `lab score` itself, writes their output to `runs/<task>/pipeline.md`, and only
then starts an OpenCode session that continues the loop from that file (trace: `runs/<task>/agent-<time>.jsonl`).

## Tests

```bash
uv run pytest -q                  # about 40 s
NEURON_FULL=1 uv run pytest -q    # also compares the two loaders on NRBOOK (6.8 M rows)
NEURON_LLM=1 uv run pytest -q tests/test_suggest.py   # the acceptance test of step 5 with the real model (metered)
```

The tests cover four things:
- the parity of the stdlib loader of the submission with the Polars loader;
- the t0 pipeline from grain to residuals;
- the submission against `scoring.accuracy`, with a firewall check that no task function reads target files;
- step 5 with a scripted model, and with the real one when `.env.llm` is filled in.
