# Neuron migration

Two things live in this repository:

- **Ergo**: the web pages of the rule-discovery lab (`lab serve`).
- **The submission**: `starter_kit/my_solution/`, the code that computes every task from the legacy data.

## Where the data goes

The data is not versioned. Put the challenge files in the root of the repository:

```
ch-Fable-7.4/
├── legacy/       NRADDR.csv ... NRWAIV.csv   (27 tables, about 470 MB)
├── targets/      t0_commission.csv ... t4_annual_statement.csv   (about 250 MB)
├── SCHEMA.md
├── lab/
├── starter_kit/
└── scripts/
```

Data somewhere else? Set `NEURON_LEGACY` and `NEURON_TARGETS` to the two folders.

---

## 1. Start Ergo

### Requirements

| What | Why |
|---|---|
| [uv](https://docs.astral.sh/uv/) | installs Python 3.12 and the packages of the lab |
| macOS or Linux | Desbordante has wheels only there (Windows: see `lab/README.md`) |
| [Claude Code](https://claude.com/claude-code) (`claude` on PATH, logged in once) | only for step 5 (`lab suggest`) and the agent; the rest of Ergo works without it |

### Steps

```bash
cd lab
uv sync                      # once: Python 3.12 and the packages
uv run lab ingest            # once: typed copies of the data in lab/.cache/
uv run lab run t0_commission # optional: a first run to look at (about 16 s)
uv run lab serve             # Ergo on http://127.0.0.1:8765
```

Another port: `uv run lab serve --port 9000`.

### A different model (optional)

Copy the variables into `.env.llm` in the root of the repository (not versioned), then restart `lab serve`:

```
ANTHROPIC_BASE_URL=https://your-endpoint
ANTHROPIC_AUTH_TOKEN=your-key
ANTHROPIC_MODEL=your-model
LLM_MODEL=your-model      # step 5
AGENT_MODEL=your-model    # the agent
```

Without `.env.llm`, Claude Code uses its own login and default model.

---

## 2. Submission

### Requirements

| What | Why |
|---|---|
| Python 3 | the submission uses only the standard library (`requirements.txt` is empty) |
| `legacy/` and `targets/` in place | see above |

### Score it

```bash
cd starter_kit
python3 check.py                              # every task
python3 check.py --tasks t0_commission        # one task
```

The train targets still contain the values corrected by hand (task t5), so the local score stays a little below
100 %.

### Build the hand-in

```bash
scripts/package.sh
```

It writes `dist/my_solution/` (the code, `README.md`, and every tool in `tools/`), checks it is below 15 MB and runs
`check.py` on it. Only files git does not ignore are copied: **`git add` new modules first**, or they are missing.

---

## More

- `lab/README.md`: every command of the lab, its artifacts and the tests.
- `starter_kit/my_solution/README.md`: the approach and the rules found.
