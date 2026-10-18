# lab: rule discovery for the Neuron migration

The lab finds the formulas of a target with a generic pipeline:
1. profiling of keys and joins (Desbordante);
2. clustering of target/input relations;
3. optimal decision trees;
4. a pool of candidate rules with exact scores;
5. a language model, Claude Code run headless (`claude -p`), only where the trees need a feature that is not in the
   data yet;
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

On Windows, Desbordante has no wheels (only cp312 for Linux and macOS): install the locked packages without it
(`uv export --frozen --all-groups --no-emit-project | grep -v desbordante > req.txt`, then `uv venv`,
`uv pip install -r req.txt` and `uv pip install --no-deps -e .`). Without Desbordante, `lab profile` mines keys and
inclusion dependencies by exact counting and set inclusion (`profile.exact_uccs`, `profile.exact_inds`): the same
minimal keys up to three columns and the same unary inclusions, slower (about 25 s for the legacy extract, once; the
result is cached). On t0 the profile and every later artifact are identical to the ones made with Desbordante.

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
| `lab suggest <task> [--ablate GLOB] [--dry-run]` | step 5 in batch: one request to Claude Code (`claude -p`), at most 3 validated features, exact score before and after |
| `lab freeze <run> [candidate]` | writes the function of the winner into `submission.py` and runs `check.py` |
| `lab score <task> [name=expr ...] [--submission DIR]` | runs the task function of `submission.py` behind a firewall on the target files, gives its exact score and explains its wrong rows with the optimal trees (`score.md`) |
| `lab show <table> COL=VALUE ...` | at most 40 typed rows of a legacy table or target file |
| `lab ablate <task> [card ...]` | switches each rule card of `rules/<task>.json` off in a scratch copy of the submission and scores it with `lab score --submission`: how many rows each rule makes right, and where they are (`ablation.json`) |
| `lab viz [task ...]` | `runs/atlas.html`, one offline page with the three views below |
| `lab viz policy <id> ... [--submission DIR]` | `runs/policies/<id>.json`: one policy month by month, replayed by the submission and compared with the diagnostic files |
| `lab viz story` | `runs/story.json`: the journey of 100 francs, on a policy the rules pick themselves |
| `lab llm ping` | checks that Claude Code answers for step 5 |
| `lab agent [task ...]` | Claude Code with the skill rule-discovery, one headless session per task (default t1 to t4), trace in `runs/<task>/agent-<time>.jsonl` |
| `lab serve [--port 8765]` | Ergo, the pages of the lab on `http://127.0.0.1:8765`: runs, steps, control flow, new tasks (below) |
| `lab task init\|show\|check <task>` · `lab task add <file.json>` | the definition `tasks/<task>.json` of a task: drafted from its artifacts, shown, checked, saved |
| `lab suggest <task> --max-features N` | step 5 with at most N features per request (1 to 3) |

## Artifacts of a task (`runs/<task>/`)

| File | Step | Content |
|---|---|---|
| `profile.json` | 1 | keys (UCC), inclusion dependencies, joins (plain or temporal), grain, filter |
| `frame.parquet`, `frame.json` | 1 | one row per target row with every reachable column; lineage of every column |
| `clusters.json`, `labels.parquet` | 2 | best relation, cluster centers, the rounding modes that reproduce each row, noise |
| `histograms.json` | 2 | the relations tried, binned on their precise rows, for the page of step 2 |
| `trees.json` | 3 | optimal trees, smallest feature sets, equivalent features, conflicting vectors, CART |
| `pool.json` | 4 | cards (leaves) and candidates with exact scores, ties |
| `ledger.jsonl` | 6 | every scored candidate: discovery and holdout score, fingerprint of the right rows |
| `residuals.json`, `outliers.json` | 7 | residuals by kind, noise rows cross-checked with NREXCP |
| `report.md` | – | the summary that a person or the language model reads |
| `score.md` | 6 | `lab score`: exact score of the written function, labels of its wrong rows, where it is wrong |
| `llm/*.json` | 5 | prompt hash, raw answers, validated proposals, score before and after |
| `diffs.parquet` | 6 | `lab score`: per target row the keys, the target, the computed value and their difference |
| `ablation.json`, `ablation.parquet` | 6 | `lab ablate`: per rule card the wrong rows with and without the rule, the rows it makes right per value, examples, what the trees say; per target row whether it is exact with and without each rule and the card's `where` feature |

Each artifact depends only on the ones before it.

Tasks are the scored targets and the diagnostic files (`t2_projection_year`, `t3_holding`, `t3_booking`). The key
of a diagnostic file is the shortest unique prefix of its header, and its decimal columns are the values. Targets
above one million rows are sampled: a fixed fifth of the policies.

Relations: ratio and difference with an amount, days and months with a date, a constant. The values that come
before it in the target file are inputs too. When nothing gives dense clusters, the value is related to
`previous(value)`, the value of the same policy one step before. The report also lists exact sums among the values,
and approximate relations that no constant reproduces to the cent.

## Ergo: `lab serve`

`lab serve` serves the pages of the canvas "Ergo — Task definition" with the standard library only
(`neuronlab/web/`: `server.py`, view models in `api.py` and `legacy.py`, layouts in `layout.py`; the page is plain ES
modules in `web/static/`, no build step). It listens on 127.0.0.1; every POST needs the header `X-Ergo: 1`, and the
Host header must name this machine.

- **Runs**: every run, newest first. Jobs started from the pages are recorded in `runs/_history.jsonl`; runs made
  before, or on the command line, are rebuilt from their ledger (a burst of pool evaluations is a run, a `code:` entry
  a `lab score`) and from the traces of `lab agent`. Rebuilt runs have no step durations.
- **Run**: scores, the seven steps, the candidates with Freeze (disabled, with the reason, where `freeze` has no
  template: tasks with several values, features without a join path), the wrong rows by kind, the proposals of step 5.
- **Run in progress**: the steps and the log stream from the job (server-sent events). The child gets
  `NEURON_EVENTS`, the file where `events.py` writes the step events and the scoring progress of the pool; without
  the variable the pipeline writes nothing more than before. Jobs run one at a time from a queue: a run, step 5, a
  score, an ablation, a freeze, or one Claude Code session of `lab agent` per task. Cancel stops the job and its
  children; "Stop after this job" empties the queue.
- **Clusters, Trees, Control flow**: step 2 with the histogram of each relation; the optimal tree with the path of
  a leaf; the candidate as a graph and as the code `freeze` writes, replayed on a row of the target or on values typed
  in. The value of a replay is computed by `evaluate.predicted`, the exact interpreter of the pool; the page only
  animates it. Tasks written by hand (t1-t4) show their function instead: it works on whole tables, not row by row.
  Trees and graphs speak plain language by default ("Is the premium frequency monthly?", "2 % of the amount
  received"), with the code under each sentence and a switch to codes only. `neuronlab/labels.py` takes every word
  from the extract: NRDICT for what a column is (and the codes some descriptions list), NRCODE for what a code means
  (domain = the column's abbreviation, or its table alias followed by it: `PR_STATE` -> PRSTAT), the position tables
  of SCHEMA.md for fixed-width codes, the frame names for dates and calendar features, the rule for constants. A
  code the extract does not explain stays a code (`tests/test_labels.py` lists the ones left in t0-t4).
- **New task** in four steps: legacy data, task description, test pairs, review and run. The result is
  `tasks/<id>.json` (schema `neuron-task/1`, `neuronlab/taskdef.py`).

A task definition is optional: without one every step infers what it needs, as before. With one:

| Field | Read by |
|---|---|
| `task.keys`, `task.values` | `store.target_columns` instead of the header of the target file |
| `examples.target_file.path` | `store.target`: the target file can live anywhere |
| `legacy.joins` (`keep: false`, `origin: hand`) | `profile.profile`: rejected relationships leave the join graph, added ones join it |
| `task.scope.tables` | `frame.build`: only these tables are joined |
| `legacy.tables[].columns[].type` | `frame.build`: legacy columns without a type in NRDICT are cast |
| `task.scope.tasks` | `frame.build`: the values of another task are inputs (`<task>__<column>`, summed when finer) |
| `task.values[].rounding` | `pool.run`: a known rounding mode replaces the rounding variants |
| `task.description`, notes in `task.hints` | `suggest`: added to the prompt of step 5 |
| features in `task.hints` | the run of the review page adds them with `lab feature` |
| `examples.pairs`, `pairs_use` | `lab score` checks acceptance pairs (`## acceptance pairs` in score.md); discovery pairs join the target rows |

A target file the cached legacy profile does not know gets its inclusion dependencies by set inclusion
(`profile.target_inds`), without mining the legacy tables again. New tasks are scored by the lab only: the official
`scoring.py` and `check.py` know t0-t4, and `freeze` writes only functions the submission has. COBOL copybooks are
not read (a schema file is JSON or SQL DDL, and becomes the NRDICT.csv of the upload), and a hand pair must point at
keys that exist in the legacy data.

## Visualizations (t6): `lab viz`

`runs/atlas.html` is one offline page; plotly.js is embedded once, gzip-compressed, and the browser unpacks it. Every
view reads only the artifacts of the pipeline, so it works for a new target too. Charts follow the light and dark
theme of the system, with a switch.

1. **Before / after.** A rule card switches one rule off. The page shows the wrong rows without the rule and with it,
   the rows the rule makes right, and where those rows are on the card's `where` axis: every row of the task above,
   the rows that go wrong without the rule below. The optimal trees of `lab score` on the wrong rows, the examples and
   the change itself are one click away. One chart per task gives the contribution of each rule (leave one out).
2. **Policy timeline.** `neuronlab/trace.py` subclasses the `FundAccounting` of the submission: its replay is the
   submission's own code, and the subclass writes down every booking. The bookings are matched with NRBOOK and
   t3_booking on (event, type, fund, pot); the units with t3_holding; the policy values with t3_surrender_value; the
   projection of the offer with t2_projection_year; and the rows of every task with their `diffs.parquet`. Value,
   money in and out, and the differences share one time axis; a red line marks the first divergence. BL10000001 has
   none; on BL10000321 every booking matches, and the line falls on 2025-12-31, where the surrender value is 175.00
   francs off: a value typed by hand.
3. **The journey of 100 francs.** A story in nine chapters, in English with an Italian switch, for a reader who knows
   nothing about computers or insurance. Chapters 1-7 follow one real policy (picked automatically: it crosses the
   system change of 2007, pays monthly by direct debit, has a premium a holiday moves, and every value of it is exact);
   8 and 9 explain how the rules were found and what the values typed by hand are. `tests/test_story.py` checks that
   no word of the trade appears and that every term in bold is in the glossary.

A rule card in `rules/<task>.json`:

```json
{"id": "nearest-birthday",
 "rule": "Neuron NG takes the age at the nearest birthday",
 "off": "the age at the last birthday",
 "edits": [{"file": "policies/insured.py", "old": "return age(self.birth, add_months(start, 6))",
            "new": "return age(self.birth, start)"}],
 "where": "birthday_days(PS_BIRTH, PH_BEGDT)",
 "where_label": "days from the begin date to the next birthday"}
```

`old` must be found exactly once in the file of the submission (`tests/test_ablate.py` checks every card), and
`where` is an expression of the DSL of step 5 on the frame of the task. The scratch copies live in `.cache/ablate/`
and the scored runs in `runs/<task>~on` and `runs/<task>~off-<card>` (not versioned).

## Exactness

- Amounts are decimals all the way: `N(s)` columns become `Decimal(38, s)`.
- Rounding is done on 128-bit integers in the 7 modes of the `decimal` module. It was checked against `decimal` on
  20,006 values with 0 differences.
- A row counts only if it equals the target, with the same semantics as `scoring.accuracy`.
- One policy in five (`crc32(policy_id) % 5 == 0`) is the holdout.

## Step 5 and the agent: Claude Code or an open-weights model

`llm.py` sends the prompt of step 5 to one of two backends, chosen by `LLM_BACKEND` (environment or `../.env.llm`):
- `claude` (default): Claude Code in headless mode (`claude -p`): no tools, no skills, no MCP servers, no saved
  session, and the system prompt of step 5 instead of the one of Claude Code. It uses the login of the `claude` CLI
  (subscription or `ANTHROPIC_API_KEY`). `LLM_MODEL` picks the model, e.g. `opus`; without it Claude Code uses its
  default model. There is no temperature setting, so two runs may propose different features.
- `open`: the open-weights endpoint of `../.env.llm` (`OPEN_PROTOCOL`, `OPEN_BASE_URL`, `OPEN_API_KEY`,
  `OPEN_MODEL`, overridden by `LLM_*`), at temperature 0, with the OpenAI chat API or the Anthropic Messages API.
In `lab serve` the model menu offers both: Claude Code's models when `claude` is on the PATH, and the models the
endpoint lists at `<base>/models`. Either way the model can only propose expressions of the DSL in
`neuronlab/dsl.py`, parsed with a restricted `ast` and never evaluated as Python; each one is scored exactly.

The agent follows the protocol in `../.claude/skills/rule-discovery/SKILL.md`. `lab agent [task ...]` runs it
without supervision: one headless session per task (default t1 to t4), one after the other, with the trace in
`runs/<task>/agent-<time>.jsonl`, closed by a `result` line (answer, turns, cost, duration). `AGENT_BACKEND` picks
the agent:
- `opencode` (default): OpenCode (`npm i -g @opencode/cli`, a program of its own, not a Python dependency) on the
  endpoint of `../.env.llm`, `AGENT_MODEL` overriding `OPEN_MODEL`. It runs `opencode run --standalone --auto` with
  the configuration `../scripts/opencode-open.jsonc`: the provider of `.env.llm` and no other, and guardrails, since
  `--auto` approves every action not denied there. Denied: files outside the repository, the network, questions,
  reading or writing `.env` files, edits outside `starter_kit/my_solution/`, `lab/runs/` and `lab/rules/`, and
  commands that push, commit, reset, check out, stash, delete in bulk, install, download or start another agent.
  The tool rules go under `"permissions"`: OpenCode 2 reads `"policies"` only for providers. The prompt names the
  skill file, so OpenCode needs no skill discovery.
- `claude`: Claude Code in auto permission mode (its classifier denies the actions it finds risky), `AGENT_MODEL`
  e.g. `opus`, `MAX_BUDGET_USD` a cap per session.
A session whose trace gets no new event for `AGENT_IDLE_TIMEOUT` seconds (default 900, 0 turns it off) or that runs
longer than `AGENT_TIMEOUT` seconds (off by default) is stopped with every process it started: exit code 124, a
`result` that says why, and the next task starts. With a remote open-weights model a session can hang without a
word; this keeps the queue of `lab serve` moving.
`neuronlab/agent.py` uses the standard library only, so `python lab/neuronlab/agent.py [task ...]` works without
installing the lab, and `../scripts/claude-tasks.sh` is a wrapper around it.

## Tests

```bash
uv run pytest -q                  # about 40 s
NEURON_FULL=1 uv run pytest -q    # also compares the two loaders on NRBOOK (6.8 M rows)
NEURON_LLM=1 uv run pytest -q tests/test_suggest.py   # the acceptance test of step 5 with Claude Code (metered)
```

The tests cover five things:
- the parity of the stdlib loader of the submission with the Polars loader;
- the t0 pipeline from grain to residuals;
- the submission against `scoring.accuracy`, with a firewall check that no task function reads target files;
- step 5 with a scripted model, and with Claude Code when `NEURON_LLM=1`;
- the rule cards (each still applies to the submission, one is scored), the trace of an exact policy and of one with
  a value typed by hand, the atlas offline in both themes, and the words of the story.
