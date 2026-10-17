# t0 commission: the discovery loop on real data

Copia dell'esempio del piano, con gli script delle appendici salvati come file eseguibili dalla root del repo:

| Script | Cosa mostra |
|---|---|
| `appendix_a_cluster_cart.py` | clustering del rapporto `target / PR_AMTRC`, albero CART, pool, score esatto (solo libreria standard) |
| `appendix_b_optimal_tree.py` | albero ottimo con l'obiettivo di GOSDT (programmazione dinamica esatta) contro CART, insiemi minimi di feature |
| `appendix_c_inclusion_dependencies.py` | inclusion dependency e copertura inversa: grana, join, chiavi della tabella parametri |

```bash
python3 docs/examples/appendix_a_cluster_cart.py
python3 docs/examples/appendix_b_optimal_tree.py
python3 docs/examples/appendix_c_inclusion_dependencies.py
```

Gli stessi passi, generici e per qualsiasi task, sono in `lab/` (`uv run lab run t0_commission`).

## Esempio completo su t0 (dati reali, solo libreria standard, script nelle appendici)

| Passo | Chi | Cosa succede su t0 |
|---|---|---|
| 1 Profilazione e frame | Desbordante + harness | Grana NRPREM (copertura 94,8 % contro 34,9 %), filtro `PR_STATE = P`, join temporale su NRPOLH, colonne tier attuale / alla scadenza / all'incasso, relazione `target / PR_AMTRC` |
| 2 Clustering | DBSCAN 1D + assegnazione esatta | 6 cluster: 0,005 (137 righe), 0,01 (253), 0,015 (185), 0,02 (53.683), 0,03 (102.865), 0,04 (68.725), più **10 punti di rumore** |
| 3 Albero ottimo | GOSDT (qui DP esatta) | 0 errori, 6 foglie; insieme minimo {tier@RCVDT, tipo di premio}. Per confronto, CART: 6 foglie e 3 feature mescolate |
| 4 Pool | harness | 6 schede (es. "tier A e tipo L → 4 % di `PR_AMTRC`"), ognuna pura al 100 %. Le 6 costanti sono in `NRCOMR.CR_RATE` con le chiavi `(CR_TIER, CR_PAYTP)` |
| 5 LLM | nessuno | Non serve: il codice esce dai template del freeze. La data di riferimento e le chiavi della lookup le decidono i passi 1 e 3; l'arrotondamento lo decide lo scorer (HALF_UP batte HALF_EVEN su una riga: BL10000869 #1, 399,205 → 399,21). Il modello open-weights può solo migliorare nomi e docstring |
| 6 Score | scorer esatto | **225.848 / 225.858** |
| 7 Iterazione | harness | I 10 residui sono i punti di rumore, tutti con una differenza positiva di unità intere. 6 sono in NREXCP, 4 no (BL10001299, BL10001328, BL10002438, BL10004554). Vanno a t5 e il loop si ferma |

Il codice finale in `submission.py`:

```python
def t0_commission(legacy_dir):
    """Commission = received premium x NRCOMR rate of the broker's tier on the money date, rounded half up."""
    policies = grouped(table(legacy_dir, "NRPOLH"), "PH_POLNR")
    tiers = {b["BR_BRKNR"]: b["BR_TIER"] for b in table(legacy_dir, "NRBROK")}
    paytypes = {r["RK_POLNR"]: r["RK_TARKEY"][5] for r in table(legacy_dir, "NRRISK")}
    rates = {(r["CR_TIER"], r["CR_PAYTP"]): r["CR_RATE"] for r in table(legacy_dir, "NRCOMR")}
    commission = {}
    for item in table(legacy_dir, "NRPREM"):
        if item["PR_STATE"] == "P":
            policy = valid(policies[item["PR_POLNR"]], "PH", item["PR_RCVDT"])
            rate = rates[tiers[policy["PH_BRKNR"]], paytypes[item["PR_POLNR"]]]
            commission[item["PR_POLNR"], item["PR_DUENR"]] = cents(item["PR_AMTRC"] * rate)
    return commission
```
