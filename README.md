# Wave · Lifeware Challenge

Progetto Python + Jupyter per il reverse engineering di Neuron (Neural Wave AI Hackathon, vedi
`Lifeware_Challenge.pdf`).

## Struttura

```
wave/
├── Lifeware_Challenge.pdf      testo della challenge
├── Lifeware_Challenge_Analisi_e_Strategia.pdf   analisi e strategia (guida l'EDA)
├── participants/               dati e starter kit degli organizzatori
│   ├── legacy/                 export Neuron NR*.csv
│   ├── targets/                target del train set (solo per esplorare, mai nella submission)
│   ├── SCHEMA.md
│   └── starter_kit/
│       ├── check.py, scoring.py
│       └── my_solution/        LA CONSEGNA, come chiede la traccia (vedi il suo README.md)
│           ├── submission.py, legacy.py, money.py, requirements.txt
│           ├── tools/neuron/   i tool: load, codes, policy, targets, schema/ (Desbordante), solver/ (Z3)
│           └── notebooks/      00_explore.ipynb (EDA), 01_t0_commission.ipynb (regola t0 e prove Z3)
└── cache/<versione>/           parquet e CSV di profilazione generati dai tool (ignorati da git)
```

Il package `neuron` vive dentro la consegna (una sola copia). `pyproject.toml` lo installa in modalità editable
insieme ai moduli della submission, quindi `import neuron`, `import legacy` e `import submission` funzionano in
tutto il progetto.

## Setup

Serve [uv](https://docs.astral.sh/uv/):

```
uv sync                  # crea .venv con tutte le dipendenze
uv run jupyter lab       # apre i notebook
```

## Uso in un notebook

```python
from neuron.load import load
from neuron.codes import label
from neuron.policy import timeline
from neuron.targets import target, score, mismatches

pol = load("NRPOLH")                       # tipi decodificati da NRDICT
raw = load("NRPOLH", raw=True)             # gli interi memorizzati, come li legge la submission (legacy.table)
ev = label(load("NREVNT"), "EV_EVTTP")     # + EV_EVTTP_TXT da NRCODE (PR_STATE usa il dominio PRSTAT)
tl = timeline("BL10000013")                # tutte le righe della polizza, per tabella
target("t4_annual_statement", "BL10000013")
score("t0_commission", predictions)        # (corrette, totali) con lo scoring ufficiale

from neuron.schema.keys import key_report
from neuron.schema.relations import relations
from neuron.schema.graph import relation_graph
from neuron.schema.diagram import plot_relations
key_report()                               # chiavi documentate vs chiavi trovate da HyUCC
rel = relations()                          # IND trovate da Faida/Spider, verificate, con flag `relation`
plot_relations(relation_graph(rel))
```

Le relazioni tra tabelle non sono scritte a mano: [Desbordante](https://github.com/Desbordante/desbordante-core)
trova le dipendenze di inclusione (anche su coppie di colonne, es. `POLNR+EVTNR`), ogni IND viene verificata in
modo esatto, e la regola `schema.relations.is_relation` tiene quelle che possono essere chiavi esterne.

Il primo `load` di NRBOOK (390 MB) scrive il parquet in `cache/<versione>/`; dopo si carica in meno di un
secondo. La versione è la data di modifica del CSV più recente: un export cambiato riceve una cartella nuova.
Dopo aver cambiato un decoder in `neuron/load.py`, cancella `cache/`.

## Verifica della submission

```
cd participants/starter_kit
uv run --project ../.. python check.py --tasks t0_commission
```

`check.py` stampa l'accuratezza e il maintainability index (radon) di tutti i `.py` della consegna, tool
compresi. La submission calcola tutto da `legacy_dir` (niente target, niente cache).

## Trappole trovate nei dati

- `NRPERS.PS_BIRTH`: 10 date impossibili (es. `541131` = 31/11/1954), decodificate come `null`.
- `NRCODE`: i testi inglesi stanno in `CD_TXTDE`, `CD_TXTEN` è vuota; righe CRLF.
- `PS_SMOKE` usa `J`/`N`, non `Y`/`N`, e non ha un dominio in NRCODE; `PS_SEX` è `1`/`2`.
- `PR_STATE` non segue la convenzione dei codici: il suo dominio è `PRSTAT`, non `STATE`.
- `NRFXRT`: valute anche in minuscolo (`eur`, `chf`, …) nei giorni che mancano alla serie maiuscola: normalizzare.
- `NRFPRC`: `FP_FNDID, FP_PRCDT` non è unico (prezzi ripubblicati, conta l'ultima pubblicazione).
- Conversione COBOL → Java (evento 800) nella notte dell'11.8.2007, su tutte le 946 polizze allora vive.
- Incasso LS spostato nei weekend e nei festivi ticinesi (Venerdì Santo escluso); UB sempre il giorno stesso.
- Un intero `0` nelle colonne di riferimento (`EV_REVNR`, `PR_EVTNR`, `TB_EVTNR`) vuol dire "nessun riferimento".
- 4011 polizze nell'export: 3019 train (con target), 992 public.
