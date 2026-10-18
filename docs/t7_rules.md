# t7 The Tax Audit: le regole del nuovo motore

Documento di riferimento sulle regole che il nuovo motore (OpenCode, `opencode run --standalone "Continua con fund-based…"`)
ha scritto per la task 7. Descrive **cosa fa il codice**, riga per riga, non cosa dovrebbe fare; dove le due cose
divergono lo dice e porta la prova misurata sui dati di `legacy/`.

| | |
|---|---|
| File analizzato | `starter_kit/my_solution/t7_impl.py` |
| Snapshot | sha1 `85fa0d4cbcd48c2de560da851026deb4d60ad247`, mtime 2026-10-17 23:47:11, 17018 byte |
| Collegamento | `submission.py:16` `from t7_impl import t7_tax_payout, t7_tax_annual` (import assoluto) |
| Note del motore | `starter_kit/my_solution/analysis_t7.md` (23:32, precedente allo snapshot) |
| Stato del motore | ancora in esecuzione al momento dello snapshot: il file è cambiato 4 volte tra 23:40 e 23:47 |

> **Aggiornamento 2026-10-18.** `t7_impl.py` non esiste più: il codice è stato rifattorizzato, con output identici
> sui dati di `legacy/`, nel package `starter_kit/my_solution/taxes/`. Regole → moduli: R1 `days.py`
> (`stored_day`), R2-R3 `residence.py`, R4 `rates.py`, R5 `book.py`, R6 `fund_value.py`, R7 `amounts.py`
> (`taxable_gain`), R8 `payout.py` (`add_months`), R9 `neuron.cents`; §4 `payout.py` + `payout_event.py`,
> §5 `annual.py` + `tax_year.py` + `kis.py`. I numeri di riga qui sotto valgono solo per lo snapshot.

I numeri di riga `t7_impl.py:N` si riferiscono a questo snapshot. Se il motore modifica ancora il file, le righe si
spostano: confronta lo sha1 prima di usarle.

---

## 1. Il contratto richiesto (dal PDF `such.pdf`)

| Funzione | Chiave | Valore | Note |
|---|---|---|---|
| `t7_tax_payout(legacy_dir)` | `(policy_id, event_nr)` | `(country, taxable_base, withholding, surcharges, stamp_duty, remittance_date)` | una riga per ogni **pagamento**; `remittance_date = None` se non è stato trattenuto nulla |
| `t7_tax_annual(legacy_dir)` | `(policy_id, year)` | `(ch_stp, ch_vst, it_sos, it_bol, de_kst, de_sol, de_kis)` | **solo gli anni con almeno un importo** |

Esempi ufficiali:

```
t7_tax_payout  BL10000086,121,DE,5628.16,1407.04,77.38,0.00,2006-08-10
t7_tax_annual  BL10000044,2019,0.00,0.00,0.00,616.11,0.00,0.00,0.00
```

Scoring (`scoring.py`, `T7_TASKS`): una riga conta solo se tutte le colonne sono esatte (paese, importi al centesimo, data).
In locale non ci sono target t7 (la cartella `targets t7/` citata dal PDF non è nel repo): le uniche verifiche
possibili sono i due esempi qui sopra.

---

## 2. Tabelle usate e ignorate

| Tabella / colonna | Usata? | Come |
|---|---|---|
| `NRTAXB` TB_POLNR, TB_EVTNR, TB_TAXTP, TB_EFFDT | sì | definisce le chiavi e i tipi di imposta |
| `NRTAXB` TB_USRID, TB_CHGTS | **no** | ignora le correzioni `TAXFIX19` (375 righe) e i batch `NGBATCH`/`CBLBATCH` |
| `NRHOLD` HD_POLNR → HD_PERNR | sì | **senza** HD_VLDFR/HD_VLDTO/HD_VRSNR (vedi R2) |
| `NRADDR` AD_VLDFR, AD_VLDTO, AD_CNTRY | sì | paese di residenza |
| `NRADDR` AD_REGIO, AD_TAXST, AD_CHURCH | **no** | regione, stato fiscale e appartenenza alla chiesa non entrano mai |
| `NRTAXR` TX_TAXTP, TX_VLDFR, TX_VLDTO, TX_RATE, TX_THRSH | sì | aliquota e soglia |
| `NRTAXR` TX_CNTRY, TX_REGIO, TX_VRSNR, TX_CHGTS | **no** | paese, regione, versione e data di inserimento ignorati |
| `NRBOOK` BK_POLNR, BK_EVTNR, BK_AMTPC | sì | importo del pagamento (vedi R5) |
| `NRPREM` (via `FundAccounting.premiums`) | sì | premi pagati (vedi R6) |
| `NRPREM` (via `_load_table`) | sì | solo in `t7_tax_annual` per KST, con un bug (vedi D9) |
| `FundAccounting` (`funds/`) | sì | replay delle quote per il valore del fondo (vedi R6) |
| `NREVNT` | **no** | il tipo evento (110/400/410/500) non è mai letto |

Tipi di imposta presenti nei dati e trattamento nel codice:

| TB_TAXTP | righe NRTAXB | eventi (EV_EVTTP) | in NRTAXR | gestito da `t7_tax_payout` | gestito da `t7_tax_annual` |
|---|---|---|---|---|---|
| BOL | 5919 | 5785 con TB_EVTNR=0, 127×410, 7×500 | sì (6 righe, 2 versioni nel 2017-19) | solo se paese IT e nessun SOS nel gruppo | sì (IT) |
| STP | 454 | tutte 110 (incasso premio) | sì | solo se paese CH | sì (CH) |
| BOC | 295 | 151×400, 136×410, 8×500 | **no** | **no** | **no** |
| VST | 257 | 144×410, 102×400, 11×500 | sì | solo se paese CH | sì ma sempre 0 (D11) |
| SOS | 153 | 77×410, 76×400 | sì | solo se paese IT | **no** (sempre 0) |
| KST | 88 | 46×410, 40×400, 2×500 | sì | solo se paese DE | sì ma sempre 0 (D9) |
| SOL | 88 | come KST | sì | solo se paese DE | sì ma sempre 0 (D9) |
| KIS | 29 | 15×400, 14×410 | sì (generale + BY + BW) | solo se paese **LU** (D7) | **no** (sempre 0) |
| HEV, TFS | 0 | | sì | | |

---

## 3. Regole comuni (helper)

### R1. Date: `_parse_date` (`t7_impl.py:16`)

Legge le date grezze dei CSV (non usa `neuron.table`, che le tipizza già da NRDICT).

| Formato | Interpretazione | Esempio |
|---|---|---|
| vuoto, `9999999`, `1111231` | `None` | `1111231` → `None` |
| 6 cifre `YYMMDD` | `YY ≥ 50` → 19YY, altrimenti 20YY | `950417` → 1995-04-17 |
| 7 cifre `CYYMMDD` | `C = 1` → 20YY, altrimenti 19YY | `1060717` → 2006-07-17 |
| 8 cifre `YYYYMMDD` | diretta | |
| altro o data impossibile | `None` | |

`1111231` è una data vera (2011-12-31): è la fine di validità di `IT SOS 12.5%` in NRTAXR e compare in 1 riga di
NRHOLD. Trattarla come "senza fine" è sbagliato (D3).

### R2. Titolare: `hold_map` (`t7_impl.py:205`, `:349`)

`{HD_POLNR: HD_PERNR}` costruito su tutte le righe di NRHOLD: **vince l'ultima riga in ordine di file**, a prescindere
dalla validità. 116 polizze hanno più versioni, e in tutte e 116 il titolare cambia (D4).

### R3. Paese di residenza: `_country_at_date` (`t7_impl.py:38`)

Prima riga di NRADDR della persona, **in ordine di file**, con `AD_VLDFR ≤ data ≤ AD_VLDTO` (VLDTO `None` = aperta).
Restituisce `AD_CNTRY`. Ignora AD_VRSNR e AD_CHGTS: con le 291 coppie di versioni sovrapposte presenti in NRADDR
il risultato dipende dall'ordine delle righe (D4).

Data usata: `TB_EFFDT` della **prima** riga del gruppo in `t7_tax_payout`; il **1° gennaio** dell'anno in
`t7_tax_annual`.

### R4. Aliquota: `_tax_rate_for` (`t7_impl.py:95`)

1. Considera le righe di NRTAXR con `TX_TAXTP` uguale, `TX_VLDFR ≤ data` e (`TX_VLDTO` `None` oppure `≥ data`).
2. Tra queste prende quella con `TX_VLDFR` più recente; a parità vince **la prima in ordine di file** (`>` stretto,
   riga 119).
3. `rate = TX_RATE / 10000`, `threshold = TX_THRSH / 100` (`None` se vuoto).

Aliquote effettivamente restituite (valore come lo usa il codice):

| TB_EFFDT | 1995-04-17 | 1997-12-31 | 1998-01-01 | 1998-04-01 | 2006-07-17 | 2009-01-01 | 2011-12-31 | 2012-01-01 | 2014-07-01 | 2017-12-31 | 2019-06-30 | 2019-07-01 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| STP | – | – | – | 2.5 | 2.5 | 2.5 | – | 2.5 | 2.5 | 2.5 | 2.5 | 2.5 |
| VST | 8 | 8 | 8 | 8 | 8 | 8 | – | 8 | 8 | 8 | 8 | 8 |
| SOS | 12.5 | 12.5 | 12.5 | 12.5 | 12.5 | 12.5 | – | 20 | 26 | 26 | 26 | 26 |
| BOL | – | – | – | – | – | – | – | 0.1 | 0.2 | **0.15** | **0.15** | 0.2 |
| KST | 25 | 25 | 25 | 25 | 25 | 25 | – | 25 | 25 | 25 | 25 | 25 |
| SOL | 7.5 | 7.5 | 5.5 | 5.5 | 5.5 | 5.5 | – | 5.5 | 5.5 | 5.5 | 5.5 | 5.5 |
| KIS | – | – | – | – | – | 9 | – | 9 | 9 | 9 | 9 | 9 |

Tre fatti da questa tabella:

- **Scala sbagliata di 100 volte** (D1). NRDICT dichiara `TX_RATE N(9,6)`: `250000` è `0.250000` = 25 %. Il codice
  restituisce `25` e poi moltiplica: `withholding = 25 × base`. La soglia invece è giusta (`TX_THRSH N(11,2)`,
  `500000` → 5000.00).
- **BOL 2017-01-01 … 2019-06-30 = 0.15** (versione 1). La versione 2 della stessa riga (`TX_VRSNR = 2`, 2000,
  inserita 2019-07-15) è la correzione retroattiva che corrisponde alle 375 righe `TAXFIX19`: il codice non la
  vede mai (D5).
- **KIS = sempre 9** (riga generale). Le aliquote regionali BY e BW (8) non vengono mai scelte (D6).
- Al 2011-12-31 nessuna aliquota: la data è letta come `None` (R1). Oggi nessuna riga NRTAXB ha quella data,
  quindi l'effetto è solo potenziale.

### R5. Importo del pagamento: `payouts` (`t7_impl.py:221`)

`payout(pol, evt) = Σ |BK_AMTPC| / 100` su **tutte** le righe NRBOOK con quella polizza e quell'evento, di qualsiasi
`BK_BKTYP` (SUR, WDR, PRM, DTH) e di qualsiasi fondo/pot. Il valore assoluto è preso riga per riga, quindi
storni e contro-registrazioni si sommano invece di compensarsi.

Copertura: solo 1134 dei 1794 gruppi `(pol, evt)` di NRTAXB hanno righe in NRBOOK; gli altri 660 hanno
`payout = 0` (tra questi tutti i gruppi `(pol, 0)` dei BOL annuali).

Per STP (evento 110, incasso premio) le righe NRBOOK dell'evento sono 808 righe `PRM`, **tutte con `BK_AMTPC`
vuoto** (colonna calcolata, mancante come in tutto l'estratto): il "payout" vale quindi 0 e `stamp_duty` è 0 in
tutti i 443 gruppi CH/STP (D15). Il premio incassato c'è, in NRPREM (`PR_EVTNR` = evento, `PR_AMTRC`), ma il codice
non lo legge.

### R6. Valore del fondo: `_fund_value` (`t7_impl.py:70`)

1. `FundAccounting(legacy_dir)` costruito una volta e messo in cache (`_get_fund_accounting`).
2. `replay(policy_id, [data])`; le quote sono quelle dello snapshot **a fine giornata** di `data`.
3. Per ogni `(fondo, pot)` con quote > 0: `quote × prezzo bid(data) × fx(data)`, arrotondato a 0.01 con il
   contesto di default (`ROUND_HALF_EVEN`), poi sommato.
4. Restituisce anche `total_premiums = Σ PR_AMTRC` dei premi `PR_STATE = "P"` con `PR_RCVDT` valorizzato, **di tutta
   la vita della polizza** (non fino a `data`). Qui PR_AMTRC è già in valuta (letto con `neuron.table`).

Conseguenza: per un riscatto totale le quote a fine giornata sono 0, quindi `fund_value = 0` (misurato su
BL10000086, evento 121).

### R7. Guadagno imponibile: `_fund_gain` (`t7_impl.py:146`)

```
se fund_value > total_premiums e total_premiums > 0:
    gain = payout × (fund_value − total_premiums) / fund_value
altrimenti:
    gain = max(0, payout − total_premiums)
```

Il docstring la chiama "Anwartschaftsverhältnis"; non è derivata dai dati.

### R8. Data di versamento: `_remittance_date` (`t7_impl.py:49`)

Il **10 del mese successivo** a `TB_EFFDT` (dicembre → 10 gennaio dell'anno dopo). È **sempre** valorizzata,
anche quando non è stato trattenuto nulla (D8).

### R9. Arrotondamento: `cents` (`t7_impl.py:139`)

`ROUND_HALF_UP` a 0.01, applicato **solo all'output**. I passaggi intermedi non sono arrotondati: SOL è calcolato
sulla KST non arrotondata.

---

## 4. `t7_tax_payout` (`t7_impl.py:185`)

### Chiavi

Un risultato per **ogni** gruppo `(TB_POLNR, TB_EVTNR)` di NRTAXB (1794 gruppi), compresi i gruppi `(pol, 0)` che
raccolgono tutte le righe BOL annuali di una polizza e i gruppi solo BOC. Il gruppo è scartato solo se la data,
il titolare o il paese mancano (con i dati attuali: nessuno). `event_nr = int(TB_EVTNR)`.

Gruppi per paese (calcolati con R2/R3): IT 924, CH 768, DE 96, LU 6.

### Base imponibile

| Paese | `taxable_base` |
|---|---|
| CH | `payout` (R5) |
| tutti gli altri | `_fund_gain(payout, fund_value(TB_EFFDT), total_premiums)` (R6, R7) |

### Imposte per paese

Il ramo è scelto **solo dal paese** (R3), non dal tipo di imposta presente in NRTAXB. `TB_EFFDT` di ogni riga
seleziona l'aliquota (R4).

| Paese | Tipo in NRTAXB | Regola nel codice | Riga |
|---|---|---|---|
| DE | KST | `withholding = rate_KST × taxable_base` | 275 |
| DE | SOL | `surcharges = rate_SOL × withholding` (la withholding già calcolata, quindi dipende dall'ordine delle righe NRTAXB: KST deve precedere SOL) | 279 |
| DE | KIS, BOL, BOC, STP, SOS | ignorati | |
| CH | VST | `withholding = rate_VST × max(0, payout − threshold)`, `threshold = 5000` se TX_THRSH vuoto | 290 |
| CH | STP | `stamp_duty = rate_STP × payout` | 299 |
| CH | BOL, BOC, KST, SOL, SOS | ignorati | |
| IT | SOS presente | `withholding = rate_SOS × taxable_base` | 307 |
| IT | BOL presente e nessun SOS | `surcharges = rate_BOL(TB_EFFDT della 1ª riga) × fund_value(TB_EFFDT della 1ª riga)` | 310-313 |
| IT | BOC, STP, KST, SOL, KIS | ignorati | |
| LU | KIS | `withholding = rate_KIS × taxable_base` | 320 |
| LU | BOL, VST, STP, BOC | ignorati | |

`stamp_duty` è non nullo solo per CH; `surcharges` solo per DE (SOL) e IT (BOL).

Output: `(country, cents(taxable_base), cents(withholding), cents(surcharges), cents(stamp_duty), remittance_date)`.

---

## 5. `t7_tax_annual` (`t7_impl.py:338`)

### Chiavi

Una riga per ogni `(TB_POLNR, anno di TB_EFFDT)` presente in NRTAXB, **per tutti i tipi** (anche STP/VST dei
pagamenti), **anche se tutti gli importi sono 0** (il filtro "almeno un importo" della versione precedente è stato
tolto). 6393 chiavi: IT 5244, CH 982, DE 145, LU 22 (paese al 1° gennaio).

### Regole

| Colonna calcolata | Condizione | Regola | Riga |
|---|---|---|---|
| `ch_stp` | STP nell'anno e paese CH | `rate_STP(31.12) × fund_value(31.12)` | 389-393 |
| `it_bol` | BOL nell'anno e paese IT | `rate_BOL(31.12) × fund_value(31.12)` | 395-400 |
| `ch_vst` | VST nell'anno e paese CH | `rate_VST × max(0, 0 − 5000)` = **sempre 0** (`payout = 0` fisso) | 403-411 |
| `de_kst` | KST nell'anno e paese DE | `rate_KST(31.12) × _fund_gain(P, fv, P)` con `P = _total_premiums_up_to(...)` → **sempre 0** (D9) | 414-421 |
| `de_sol` | SOL nell'anno, paese DE, `de_kst ≠ 0` | `rate_SOL(31.12) × de_kst` → sempre 0 | 423-426 |
| `de_kis` | LU e KIS | placeholder 0 | 429 |
| `it_sos` | | placeholder 0 | 433 |

### Ordine delle colonne in uscita (D10)

Il codice restituisce `(ch_stp, ch_vst, de_kst, de_sol, de_kis, it_bol, 0)`, il contratto vuole
`(ch_stp, ch_vst, it_sos, it_bol, de_kst, de_sol, de_kis)`. `it_bol` finisce nella colonna `de_sol`.

---

## 6. Verifica sugli esempi del PDF

### BL10000086, evento 121 (DE, riscatto totale 2006-07-17)

Dati misurati: 8 righe NRBOOK `SUR` (4 fondi × 2 pot), `payout = 12107.36`; premi pagati `11760.00`;
`fund_value(2006-07-17) = 0` (quote già azzerate a fine giornata); titolare P0000080, residenza DE/BY dal 1990.

| Colonna | Atteso | Codice | Perché |
|---|---|---|---|
| country | DE | DE | ✓ |
| taxable_base | 5628.16 | 347.36 | `fund_value = 0` → fallback `payout − premi` |
| withholding | 1407.04 | 8684.00 | `25 × 347.36` (scala ×100, D1) |
| surcharges | 77.38 | 47762.00 | `5.5 × 8684.00` |
| stamp_duty | 0.00 | 0.00 | ✓ |
| remittance_date | 2006-08-10 | 2006-08-10 | ✓ |

Riga **errata** (3 colonne su 6). Osservazione dall'esempio, utile per la regola giusta: `1407.04 = 0.25 × 5628.16`
esatto, e `0.055 × 1407.04 = 77.3872` → atteso `77.38`, cioè SOL è **troncato**, non arrotondato half-up: anche con
base e scala corrette `cents()` darebbe 77.39.

### BL10000044, 2019 (IT, BOL)

Dati misurati: residenza IT dal 1990; `fund_value(2019-12-31) = 167242.38`; nel 2019 ci sono due righe BOL
(`1190720` utente `TAXFIX19`, `1191231` utente `TAXBATCH`).

| Colonna | Atteso | Codice |
|---|---|---|
| ch_stp | 0.00 | 0.00 |
| ch_vst | 0.00 | 0.00 |
| it_sos | 0.00 | 0.00 (colonna occupata da `de_kst`) |
| it_bol | 616.11 | 0.00 (colonna occupata da `de_sol`) |
| de_kst | 0.00 | 0.00 (colonna occupata da `de_kis`) |
| de_sol | 0.00 | **33448.48** (`it_bol = 0.2 × 167242.38`) |
| de_kis | 0.00 | 0.00 |

Riga **errata**. Anche con scala e ordine corretti: `0.002 × 167242.38 = 334.48 ≠ 616.11`. Il fatto che la
differenza cada nell'anno della correzione `TAXFIX19` suggerisce che 616.11 includa il conguaglio 2017-2019 della
versione 2 di BOL; il codice non lo modella (D5).

### Esecuzione completa (snapshot `85fa0d4c`, su `legacy/`)

Entrambe le funzioni terminano senza errori. Le versioni precedenti dello stesso file andavano in crash
(`TypeError` str/date in `_tax_rate_for`, poi `NameError: type_entries` nel ramo CH): sono state corrette dal motore
alle 23:47.

| | `t7_tax_payout` | `t7_tax_annual` |
|---|---|---|
| righe | 1794 | 6393 |
| tempo | 27.5 s (1708 replay del fondo, 20.1 s) | 80.9 s (5708 replay, 40.7 s) |
| righe con tutti gli importi a 0 | 803 | 896 |
| altre righe da scartare | 660 righe `(pol, 0)` dei BOL annuali | |
| `remittance_date = None` | 0 | |
| colonne sempre 0 | `stamp_duty` | posizioni 2, 3, 4, 5, 7 |
| righe con la colonna ≠ 0 | withholding 345, surcharges 643 | pos. 1 `ch_stp` 433; pos. 6 (per il contratto `de_sol`, contiene `it_bol`) 5064 |

Esempi di righe prodotte, per mostrare l'ordine di grandezza dovuto alla scala ×100:

```
t7_tax_payout  BL10000003,201,CH,46495.39,331963.12,0.00,0.00,2005-05-10     # VST: 8 × (46495.39 − 5000)
t7_tax_payout  BL10000044,0,IT,0.00,0.00,10200.91,0.00,2013-01-10            # gruppo (pol, 0): tutti i BOL 2012-2025 in una riga, BOL 0.1 × fondo al 31.12.2012
t7_tax_payout  BL10001969,295,CH,509230.08,4033840.64,0.00,0.00,2024-10-10   # withholding massima
t7_tax_annual  BL10000044,2019,0.00,0.00,0.00,0.00,0.00,33448.48,0
```

Nessuna delle due righe d'esempio del PDF è riprodotta.

---

## 7. Difetti, in ordine di impatto

| # | Difetto | Dove | Effetto misurato |
|---|---|---|---|
| D1 | `TX_RATE / 10000` invece di `/ 1 000 000` (NRDICT `N(9,6)`) | :124 | ogni imposta ×100: KST 25 invece di 0.25 |
| D2 | `fund_value` letto a fine giornata del pagamento | :253, :76-77 | riscatti totali: `fund_value = 0`, base = `payout − premi` (BL10000086: 347.36 invece di 5628.16) |
| D3 | `1111231` letto come "nessuna data" | :19 | IT SOS 12.5 % considerato valido per sempre (oggi mascherato dalle righe successive); al 2011-12-31 nessuna aliquota |
| D4 | titolare = ultima riga di NRHOLD, residenza = prima riga valida di NRADDR, senza versioni | :205, :38 | 116 polizze con cambio titolare, 291 coppie di indirizzi sovrapposte: paese dipendente dall'ordine del file |
| D5 | versioni NRTAXR e correzioni `TAXFIX19` ignorate | :119 | BOL 2017-01-01…2019-06-30 a 0.15 invece della versione 2 (0.2); nessun conguaglio |
| D6 | TX_REGIO e AD_REGIO/AD_CHURCH ignorati | :95, :38 | KIS sempre 9 %, mai 8 % (BY, BW), applicato anche a chi non è membro della chiesa |
| D7 | ramo scelto dal paese, non dal tipo di imposta | :265-320 | KIS dei residenti DE (25 gruppi) ignorato; KST/SOL di residenti CH/IT (12 gruppi: CH 6, IT 6) ignorati; BOC (295 righe) mai gestito |
| D8 | `remittance_date` sempre valorizzata | :322 | il contratto vuole `None` se non c'è trattenuta |
| D9 | `_total_premiums_up_to` non filtra la polizza e non divide per 100 | :175-180 | `P = 15 448 691 500` (tutti i premi di tutte le polizze in centesimi) → `de_kst = de_sol = 0` sempre |
| D10 | ordine delle colonne di `t7_tax_annual` | :432-433 | `it_bol` nella colonna `de_sol`; ogni riga IT con BOL è sbagliata |
| D11 | `ch_vst`, `it_sos`, `de_kis` annuali fissi a 0 | :409, :429, :433 | colonne mai calcolate |
| D12 | chiavi non filtrate | :324, :431 | payout: righe `(pol, 0)` dei BOL annuali e gruppi solo BOC; annual: righe tutte a zero |
| D13 | `payout` = somma dei valori assoluti di tutte le righe NRBOOK dell'evento | :221 | storni sommati invece che compensati; 660 gruppi senza NRBOOK → 0 |
| D14 | arrotondamento solo finale, half-up | :139 | SOL dell'esempio richiede troncamento (77.38) |
| D15 | stamp duty calcolata su NRBOOK, dove le righe PRM hanno `BK_AMTPC` vuoto | :299, :221 | `stamp_duty = 0` in tutte le 1794 righe; il premio è in NRPREM (`PR_EVTNR`, `PR_AMTRC`) |

---

## 8. Affermazioni di `analysis_t7.md` che i dati smentiscono

| Affermazione | Dato reale |
|---|---|
| "Rate format: raw_value / 10000 = percentage" | NRDICT: `TX_RATE N(9,6)`, cioè frazione con 6 decimali |
| Tipi "BOS (Italian); BOG (corrections)" | non esistono in NRTAXB; esiste **BOC** (295 righe), non citato |
| "German KST/SOL events are always event types 400 or 410" | 2 eventi KST/SOL sono di tipo 500 (sinistro morte) |
| "1794 unique (policy, event, tax_type) combinations" | 1794 sono le coppie `(policy, event)`; le triple sono di più (625 duplicate) |
| "`it_bol = fund_value × rate`, 3080.55 × 0.20 = 616.11" | 3080.55 non è derivato da nessun dato; il valore del fondo al 31.12.2019 è 167242.38 |
| "Rules confirmed: KST withholding = rate × taxable_base" ecc. | nessuna riga del codice riproduce uno dei due esempi |

---

## 9. Come riprodurre

```bash
cd starter_kit
python3 check_t7.py          # carica submission.py ed esegue le due funzioni (nessun target locale)
python3 check.py --tasks t0_commission   # verifica che l'import di t7 non rompa le altre task
```

Per le singole regole: importare `my_solution.t7_impl` con `starter_kit/` e `starter_kit/my_solution/` in
`sys.path` e chiamare `_tax_rate_for`, `_fund_value`, `_fund_gain` sui casi delle sezioni 3 e 6.
