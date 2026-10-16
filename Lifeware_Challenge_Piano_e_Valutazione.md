# The Neuron Migration: verifica sui dati e piano d'azione

**Siamo sulla direzione giusta? Cosa dicono i dati, cosa cambiare e come muoverci fino a domenica alle 16:00, con due obiettivi: accuratezza al 100 % su t0–t4 e maintainability index di almeno 95**

Neural Wave AI Hackathon 2026 · Sfida Lifeware · USI Lugano
Documento di lavoro per il team · notte tra venerdì 16 e sabato 17 ottobre 2026

Fonti analizzate: `Lifeware_Challenge.pdf` (testo della sfida), `Lifeware_Challenge_Analisi_e_Strategia.pdf` (il documento della direzione, d'ora in poi "il documento"), la cartella `participants/` (27 tabelle legacy, 8 file target, `SCHEMA.md`, starter kit).

Materiale consegnato insieme a questo piano:

- `verifica_dati/verifica.py` riproduce ogni numero del documento in circa 6 secondi;
- `verifica_dati/mi_report.py` scompone il maintainability index file per file;
- `esempio_consegna/` è uno scheletro di `my_solution` con t0 e t1 già al 100 % delle righe valutate e MI 94,6.

---

## Indice

0. [Il verdetto in una pagina](#0-il-verdetto-in-una-pagina)
1. [Cosa ho fatto e come leggere il documento](#1-cosa-ho-fatto-e-come-leggere-il-documento)
2. [Il documento della direzione alla prova dei dati](#2-il-documento-della-direzione-alla-prova-dei-dati)
3. [Le scoperte che cambiano il piano](#3-le-scoperte-che-cambiano-il-piano)
4. [Regole confermate e obiettivi, task per task](#4-regole-confermate-e-obiettivi-task-per-task)
5. [Manutenibilità: come arrivare a MI 95](#5-manutenibilità-come-arrivare-a-mi-95)
6. [Come mi comporterei: il metodo operativo](#6-come-mi-comporterei-il-metodo-operativo)
7. [Il piano: le mosse fino a domenica alle 16:00](#7-il-piano-le-mosse-fino-a-domenica-alle-1600)
8. [Rischi e checklist di consegna](#8-rischi-e-checklist-di-consegna)
9. [Appendici](#9-appendici)

---

## 0. Il verdetto in una pagina

> **Verdetto.** Sì, siete sulla direzione giusta. Il metodo del documento (contare le righe esatte, costruire prima l'harness, trattare le convenzioni come dati, scomporre t3 passo per passo, affrontare t5 per ultimo) è esattamente quello che i dati premiano. L'ho applicato alla lettera per qualche ora sui dati veri e ha funzionato subito. Ma **nove punti vanno corretti**: alcuni fanno perdere ore, uno da solo farebbe sbagliare t3 su 454 polizze, e uno riguarda la manutenibilità, che il documento tratta come un vincolo mentre per noi è un obiettivo.

**Cosa ho misurato** (train, righe esatte, nessun modello statistico):

| Cosa | Risultato | Stato |
|---|---|---|
| t0 commissioni | 225.848 / 225.858 = **99,9956 %**, cioè il 100 % delle righe valutate: i 10 residui sono correzioni manuali | in `esempio_consegna/` |
| t1 prossime scadenze | 15.028 / 15.028 = **100 %** | in `esempio_consegna/` |
| **Maintainability index** dello scheletro t0 + t1 | **94,6** (lo stub vuoto fa 82,9) | in `esempio_consegna/` |
| t3, i "mattoni" dei movimenti: trade date, prezzo, importo investito, cambio, quote, admin fee | **100 %** per ciascun mattone | regole pronte |
| t3, valore di riscatto dato il valore di polizza | 4.619 / 4.635 = **99,65 %**; i 16 residui sono correzioni manuali | regola pronta |
| t4 come somma annuale dei movimenti di t3 | 34.125 / 34.145 = **99,94 %** di righe intere; i 20 residui sono correzioni manuali | regola pronta, dipende da t3 |
| t2, struttura | anni di proiezione = durata (3.019/3.019); tasso alla data di domanda (7/7 casi decisivi) | struttura chiara |
| t5, firma delle correzioni manuali | **54 su 54** sono delta di franchi interi; NREXCP ne elenca 38 (70 %) | ricetta pronta |

**I nove punti da correggere nella direzione**

1. **Lo switch COBOL → Java non si cerca: è scritto nei dati.** Evento 800 "system conversion" del **2007-08-11** (utente `CONV2007`, 946 polizze); il batch `CBLBATCH` lavora fino al 10.8.2007, `NGBATCH` dall'11.8.2007. Il "trucco dei decimali" non avrebbe trovato nulla: le quote hanno 6 decimali in entrambe le ere.
2. **"Parametri alla data della domanda" vale per t2, non per t3/t4.** Il tasso NRILLU di t2 si prende alla firma; admin fee ed entry charge seguono invece la data del movimento.
3. **I cambi vanno normalizzati.** NRFXRT contiene 80 righe con codice valuta minuscolo (`usd`, `chf`…) proprio nei giorni in cui manca la riga maiuscola. Con un lookup case-sensitive **454 polizze** hanno almeno un movimento sbagliato, quindi t3 sbagliato per tutte (conteggio su tutte le righe: `verifica.py --sample 0`; con il campione di default lo script ne vede 22).
4. **La trade date dei premi segue il calendario prezzi del fondo**, non il calendario ticinese: 100 % contro 99,52 %.
5. **Premi e prelievi usano date di cambio diverse.** Premi: ultimo fixing prima della trade date. Prelievi: fixing alla trade date.
6. **`t3_booking` è la miniera d'oro: 5 milioni di esempi etichettati.** Ogni mattone si chiude da solo, e t4 è la somma esatta di questi movimenti.
7. **t5 è più semplice di un problema positive-unlabeled.** Tutte le correzioni sono delta interi; il timestamp di NREXCP indica la riga esatta.
8. **Meno strumenti.** Mi sono bastati polars, `decimal`, `holidays` e il conteggio delle righe esatte. PySR, OpenEvolve, ShinkaEvolve, Z3 e Desbordante restano un piano B, al massimo per il risk charge.
9. **Il maintainability index è un obiettivo, non un vincolo.** Il documento suggerisce di trattarlo "come vincolo". Con un modulo per concetto di business, docstring che enunciano la regola e convenzioni come dati si arriva a **94,6 senza perdere una riga di accuratezza** (§5). Il punteggio si gioca su entrambi gli assi.

> **Cosa fare adesso.** Stanotte si copia `esempio_consegna/` in `my_solution/` (t0 e t1 già pronti, MI 94,6) e si fa il primo invio. Da domattina tutta la squadra lavora su t3, mattone per mattone contro `t3_booking`, partendo dagli unici due mattoni ancora aperti, **AMC** e **RSK**. Una persona porta avanti t2 in parallelo. Ogni merge passa due cancelli: l'harness dell'accuratezza e quello del MI.

**Il giudizio, in breve.** Metodo: giusto. Le 27 ipotesi e scelte del documento messe alla prova (§2): 12 confermate, 9 da correggere, 2 smentite, più 4 aspetti che il documento non prevedeva. Piano temporale: prudente, si può anticipare di mezza giornata. Strumenti: sovradimensionati. Manutenibilità: da promuovere a obiettivo.

---

## 1. Cosa ho fatto e come leggere il documento

**Il procedimento** è lo stesso che propongo al team nel §6.

1. Ho letto il testo della sfida, il documento, `SCHEMA.md` e lo starter kit (`README.md`, `check.py`, `scoring.py`, lo stub `submission.py`).
2. Ho caricato le 27 tabelle con un caricatore generico guidato da `NRDICT`: tipi, decimali impliciti e date si leggono dal dizionario, non si scrivono colonna per colonna.
3. Per ogni ipotesi del documento ho implementato la regola più semplice e contato le righe esatte contro target e diagnostici di train. Poi ho provato da 2 a 5 varianti e ho tenuto la migliore solo se il guadagno era netto e spiegabile in una frase.
4. Quando restavano residui, li ho raggruppati per dimensione (era, valuta, fondo, giorno, prodotto…) finché la condizione nascosta non diventava evidente.
5. Ho scritto t0 e t1 come consegna vera, li ho misurati con lo `scoring.py` ufficiale e ho alzato il maintainability index da 83,3 a 94,6 in sette passi, senza perdere accuratezza (§5.3).

**Riproducibilità.** `verifica_dati/verifica.py` stampa ogni numero di questo documento; l'output atteso è in `verifica_dati/output_atteso.txt`. Lo script legge i target, quindi è uno strumento di analisi e **non** va messo nella consegna.

**Legenda degli esiti** usata nelle tabelle:

- **CONFERMATO**: i dati danno ragione al documento.
- **DA CORREGGERE**: l'idea è giusta, ma il dettaglio è sbagliato, incompleto o più complicato del necessario.
- **SMENTITO**: i dati dicono altro.
- **NUOVO**: il documento non lo prevedeva.

**Cosa non ho fatto.** Non ho simulato t3 o t2 per intero. AMC, RSK, ripartizione dell'admin fee tra fondi e pot e la proiezione di t2 restano da chiudere: il §4 dice da dove partire. Non ho usato la leaderboard.

---

## 2. Il documento della direzione alla prova dei dati

| # | Ipotesi o scelta del documento | Cosa dicono i dati | Esito |
|---|---|---|---|
| 1 | Sintesi di programmi con vincolo di esattezza: contare le righe esatte, non gli errori medi | Ogni regola giusta arriva al 100 % cambiando una sola convenzione; le varianti sbagliate restano tra l'81 % e il 99,5 %. Il conteggio esatto le separa senza ambiguità | **CONFERMATO** |
| 2 | Il primo strumento è l'harness delle differenze | È ciò che ha reso possibile tutto il resto: ogni ipotesi diventa un numero in pochi secondi | **CONFERMATO** |
| 3 | Date `CYYMMDD` a 6 o 7 cifre, sentinelle `0` e `9999999` | Vero. In più, 10 date di nascita impossibili (30.2, 31.4, 31.6, 31.9, 31.11), 8 su polizze di train: il `day()` dello starter kit va in crash | **NUOVO** |
| 4 | Codici di origine svizzero-tedesca (LS, UB, E, L) | Vero, e c'è di più: `PS_SMOKE` usa `J`/`N` (Ja/Nein) mentre `SCHEMA.md` dice `Y`/`N`. Con `== 'Y'` nessuno risulta fumatore (749 lo sono) | **NUOVO** |
| 5 | 23 tabelle in cinque gruppi | Sono 27: manca il modulo fiscale (`NRHOLD`, `NRADDR`, `NRTAXR`, `NRTAXB`), con importi vuoti e una versione retroattiva in `NRTAXR` | **NUOVO** |
| 6 | Trovare lo switch COBOL → Java contando i decimali delle quote | Superfluo, e non funzionerebbe: lo switch è l'evento 800 del 2007-08-11 e le quote hanno 6 decimali in entrambe le ere | **SMENTITO** |
| 7 | Troncamento in COBOL, half-up in Java | Vero al 100 % su importi investiti, quote e valore di riscatto (dove il COBOL tronca il netto, non la penale) | **CONFERMATO** |
| 8 | Tariffe bloccate alla data della domanda, "da verificare tabella per tabella" | t2: sì, il tasso NRILLU è quello della firma (7/7 casi decisivi). t3/t4: no, admin fee (84 → 90 → 102 → 120 l'anno su FK) ed entry charge (tier B dal 4 % al 3 % dal 1.7.2021) seguono la data del movimento. La cautela "tabella per tabella" era giusta | **DA CORREGGERE** |
| 9 | Lookup "as-of" su NRPOLH, il broker può cambiare | Broker valido al money date (`PR_RCVDT`): 99,9956 %. Primo broker: 99,23 %. Broker attuale: 99,36 % | **CONFERMATO** |
| 10 | Escludere le rate stornate abbinando ogni evento 900 alla sua rata | Più semplice: contano le rate con `PR_STATE = 'P'` (225.858, cioè esattamente le righe di t0). `R` = addebito stornato, `O` = aperta, `W` = stralciata | **DA CORREGGERE** (semplificare) |
| 11 | Scadenzario: deriva 31 → 28 → 28, nuova ancora dopo i cambi | Vero, con la chiave: la deriva c'è solo in era COBOL, Java tiene fisso il giorno di ancoraggio. Regola ibrida 100 %; solo ancora 98,35 %; solo catena 92,60 % | **CONFERMATO** (precisato) |
| 12 | Calendario ticinese; il Venerdì Santo non è festivo | Esatto: le 158 rate LS del 26.3.2027 sono incassate il giorno stesso. 8.12, 6.1, 19.3, Lunedì dell'Angelo, Ascensione, Lunedì di Pentecoste, Corpus Domini e 29.6 spostano l'incasso | **CONFERMATO** |
| 13 | Incasso LS: primo giorno lavorativo successivo, oppure modified following, oppure anticipato di qualche giorno (LSV+) | Vale la prima ipotesi: solo in avanti, anche oltre la fine del mese (261 incassi passano al mese dopo, ad esempio 31.10.2026 → 2.11.2026). Per UB l'incasso coincide con la scadenza, anche nei festivi | **CONFERMATO** (la prima delle tre) |
| 14 | "Calendario locale per incassi e negoziazioni" | Per gli incassi sì. La trade date dei premi invece è il primo giorno, dopo il money date, in cui **quel fondo** ha un prezzo: 100 % contro 99,52 % del calendario ticinese | **DA CORREGGERE** |
| 15 | Prezzi: ultimo prezzo il giorno stesso o prima, vale l'ultima pubblicazione | Vero (664 prezzi ripubblicati). In più: i premi comprano al prezzo **ask**, i prelievi vendono al **bid**, 100 % su 5 milioni di movimenti | **CONFERMATO** |
| 16 | "Da verificare se il lookup as-of vale anche per i cambi" | Sì, ma con due sorprese: i codici minuscoli da normalizzare (§3.3) e il cambio dei premi, preso il giorno prima della trade date (§3.2) | **DA CORREGGERE** |
| 17 | Esempio di identificabilità: 103,95 = 11 × 9,45 oppure 7 × 9,45 + 5 × 7,56 | Premessa errata. Il premio è 315,00, non 236,25; nel 2021 le rate sono 9 (sospensione premi da settembre). Tier B: 6 × 12,60 + 3 × 9,45 = 103,95. I dati sciolgono l'ambiguità in un minuto | **DA CORREGGERE** |
| 18 | Artefatti dei `double` di Java | Testato sulle quote: Decimal e double danno lo stesso risultato riga per riga. I residui erano i cambi minuscoli | **SMENTITO** (per le quote) |
| 19 | t2: versione della polizza alla firma, bisezione sui valori annuali | Anni di proiezione = durata (3.019/3.019); valore finale = ultimo anno (3.011/3.019: gli 8 casi diversi sono correzioni manuali) | **CONFERMATO** |
| 20 | t3 passo per passo, ripartendo dallo stato vero | È la tecnica giusta: `t3_booking` più gli ordini del cliente in NRBOOK danno le quote esatte prima di ogni prelievo | **CONFERMATO** |
| 21 | t4 come aggregazione di t3 | Esatta: 99,94 % di righe intere sommando `t3_booking` per anno; l'entry charge va attribuito fondo per fondo | **CONFERMATO** |
| 22 | t5 come problema positive-unlabeled; studiare la firma delle correzioni | La firma è una sola: un delta di franchi interi (54/54). Il timestamp di NREXCP individua la riga | **DA CORREGGERE** (semplificare) |
| 23 | Backtesting di t1 sulle `PR_DUEDT` | Valido ma non necessario: la regola è già al 100 % sui target | **CONFERMATO** (opzionale) |
| 24 | Circa 25 strumenti (PySR, OpenEvolve, ShinkaEvolve, Z3, Desbordante, imodels, wittgenstein, PM4Py, lifelib…) | Finora non ne è servito nessuno: le regole nascoste sono convenzioni discrete (quale data, quale arrotondamento, quale calendario, quale normalizzazione) | **DA CORREGGERE** (ridurre) |
| 25 | Il maintainability index si misura "solo sui file dei task" | `scoring.py` misura **tutti** i `.py` della cartella di consegna (`rglob`): tool e visualizzazioni in `.py` dentro `my_solution` abbassano l'indice | **NUOVO** |
| 26 | Il MI è "molto sperimentale": trattarlo come vincolo, non come obiettivo | Il MI vale punti e si alza con buone pratiche: 83,3 → 94,6 sullo stesso codice di t0 e t1, a parità di accuratezza (§5) | **DA CORREGGERE** |
| 27 | Piano: t0 al 100 % sabato mattina, t1 sabato | t0 e t1 sono già scritte (`esempio_consegna/`); t3 può partire sabato alle 8 | **DA CORREGGERE** |

**Cosa il documento ha visto giusto, e conviene dirlo:** il calendario ticinese fino al Venerdì Santo, la deriva di fine mese, il troncamento COBOL, la bisezione di t2, la scomposizione di t3, t4 come aggregazione, la precisione prima di tutto in t5, le regole come dati, l'harness prima di tutto. È una base solida, e le correzioni la rendono più rapida, non diversa.

---

## 3. Le scoperte che cambiano il piano

### 3.1 L'era COBOL/Java è un dato, non un'ipotesi

| Evidenza | Valore |
|---|---|
| Evento 800 "system conversion" | 946 eventi, tutti con `EV_EFFDT = 2007-08-11`, sorgente `M` (migration), utente `CONV2007` |
| Batch COBOL `CBLBATCH` | dal 1994-01-01 al 2007-08-10 |
| Batch Java `NGBATCH` | dal 2007-08-11 al 2026-06-30 |
| Precisione delle quote | 6 decimali in tutti gli anni: il conteggio delle cifre significative non vede lo switch |

**Come usarla:** una sola costante, `ERA_SWITCH = 2007-08-11`, e una sola funzione `rounding(day)` (troncamento prima, half-up dopo). La data che decide l'era è quella dell'operazione: la trade date per i movimenti, la data di valutazione per il riscatto, la data della scadenza per lo scadenzario. Per t2 l'ipotesi naturale da testare per prima è la data di domanda, perché l'offerta fu calcolata dal sistema in vigore alla firma. Anche le commissioni di t0 seguono la regola d'era senza perdere righe: una sola politica di arrotondamento vale per tutto il sistema.

### 3.2 Quale data governa quale parametro

Gran parte delle regole nascoste consiste nello scegliere la data giusta. Il documento lo aveva detto, e questa è la tabella misurata:

| Grandezza | Data che la governa | Evidenza |
|---|---|---|
| Broker e tier per la commissione (t0) | money date `PR_RCVDT` | 99,9956 % (data di scadenza: 99,9947 %) |
| Tier ed entry charge dei premi | money date | importo investito: 100 % in entrambe le ere |
| Allocazione ai fondi (NRALLO) | money date (a parità vince la versione più alta) | idem |
| Admin fee (NRCHRG) | data del prelievo | 397.841 / 397.842 mensilità (l'eccezione è una polizza che ha esaurito il valore) |
| Tasso di crescita dell'offerta (NRILLU, t2) | data di domanda `PH_APPDT` | 7 / 7 polizze firmate prima e iniziate dopo un cambio di tasso |
| Trade date di un premio | primo giorno dopo il money date in cui **il fondo** ha un prezzo | 567.833 / 567.833 |
| Prezzo di un premio | ask alla trade date | 100 % |
| Prezzo di un prelievo | bid all'ultimo prezzo ≤ data del prelievo (che può cadere di sabato o domenica) | 100 % |
| Cambio di un premio | ultimo fixing ≤ trade date − 1 giorno | 100 % (con codici normalizzati) |
| Cambio di un prelievo | ultimo fixing ≤ trade date | 100 % (con codici normalizzati) |
| Penale di riscatto | anni compiuti da `PH_BEGDT` alla data di valutazione; nessuna penale nei periodi NRWAIV | 100 % delle righe senza correzione manuale |

### 3.3 Le trappole nei dati (nessuna era prevista dal documento)

| Trappola | Dove | Effetto se la ignori | Rimedio |
|---|---|---|---|
| 10 date di nascita impossibili (`710230` = 30.2.1971, `541131` = 31.11.1954…) | `NRPERS.PS_BIRTH`, 8 su polizze di train | crash del decoder, o età sbagliata nel risk charge | decoder tollerante (in `esempio_consegna/formats.py` diventano `None`); la convenzione d'età va scelta col test (l'aritmetica intera COBOL sulle date `YYYYMMDD` funziona anche con date impossibili) |
| `PS_SMOKE` vale `J`/`N`, non `Y`/`N` | `NRPERS` | nessun fumatore, risk charge sbagliato per 749 persone | confrontare con `'J'` |
| 80 righe di cambio con codice minuscolo | `NRFXRT.FX_CCY` | 454 polizze con almeno una quota sbagliata: t3 perso | `upper()` sul codice valuta |
| 664 prezzi ripubblicati | `NRFPRC` | prezzo sbagliato | vale l'ultima `FP_CHGTS` |
| Prezzi e cambi fino al 2026-07-31 | `NRFPRC`, `NRFXRT` | nessuno, se il lookup è as-of | non filtrare all'estrazione |
| Prelievo limitato al valore disponibile | 1 caso (BL10001005) | valore di polizza −0,03 | riscatto = `max(0, …)` |
| Modulo fiscale con importi vuoti e versione retroattiva (`IT BOL` versione 2 del 15.7.2019) | `NRTAXR`, `NRTAXB` | nessuno per t0–t4 | ignorarlo per il punteggio; vedi §3.7 |
| 10.587 movimenti PRM di train non "contati" | `NRBOOK` vs `t3_booking` | premi stornati investiti per errore | investire solo le rate `P` |

### 3.4 `t3_booking`: cinque milioni di esempi etichettati

Il file diagnostico contiene importo, prezzo e quote di 5.024.847 movimenti: 407.636 PRM, 1.827.505 ADM, 1.833.960 AMC e 955.746 RSK. È lo strumento più potente della sfida, perché trasforma la simulazione trentennale e dipendente dal percorso in milioni di equazioni indipendenti:

- **lo stato vero** prima di ogni prelievo si ricostruisce sommando le quote di `t3_booking` e degli ordini del cliente (`SWO`, `SWI`, `WDR`, `SUR` e `DTH`, completi in NRBOOK: 24.912 righe, che `legacy.table(..., "BK_BKTYP", (...))` legge in 0,8 s);
- **ogni prelievo** diventa allora un test isolato: importo = f(valore prima del prelievo, tasso, età…).

Così si chiudono AMC e RSK senza simulare nulla. Solo quando ogni mattone è al 100 % "dato lo stato vero" si incatena la simulazione completa. È esattamente la "verifica passo per passo" del documento, portata fino in fondo.

### 3.5 t4 è una somma, e lo è al centesimo

Sommando `t3_booking` per polizza e anno della trade date si ottiene il 99,94 % di righe intere. Tutte e 20 le righe diverse sono correzioni manuali dell'admin fee, con delta intero. Due dettagli contano:

- **premi** per anno del money date, **costi** per anno della data del movimento;
- l'**entry charge** si calcola per singolo fondo (quota lorda del premio meno importo investito) e va nell'anno della trade date **di quel fondo**. Un premio di fine dicembre può negoziare un fondo il 31 e un altro a gennaio. Attribuendo tutto alla prima trade date, 36 righe cadono, a coppie, a cavallo d'anno.

Conseguenza pratica: **t4 non richiede lavoro proprio**, solo t3 giusto.

### 3.6 t5: una firma sola per tutte le correzioni

| Task | Correzioni trovate nel train | Di cui in NREXCP | Firma | Come NREXCP indica la riga |
|---|---|---|---|---|
| t0 | 10 | 6 | delta intero (da +9,00 a +77,00) | rata con scadenza poco prima di `EX_TSTMP` (6/6) |
| t2 | 8 | 5 | delta intero (da −3.955,00 a +4.855,00); la traiettoria annuale resta giusta | la polizza |
| t3 | 16 | 11 | delta intero (da +15,00 a +499,00); valore di riscatto **maggiore** del valore di polizza | ultima data di valutazione prima di `EX_TSTMP` (11/11) |
| t4 | 20 | 16 | delta intero sull'admin fee (da +7,00 a +147,00) | anno = anno di `EX_TSTMP` − 1 (16/16) |
| t1 | 0 | 0 | — | — |
| **Totale** | **54** | **38 (70 %)** | **54/54 delta interi** | |

Le motivazioni in NREXCP ("manuell korrigiert 2019, Kundenkulanz" con timestamp di altri anni) sono rumore: conta il timestamp. Un t5 basato solo su NREXCP arriverebbe al massimo a F1 ≈ 0,82; con le regole al 100 % e il filtro dei delta interi si punta a 1.

### 3.7 Starter kit e valutazione: le insidie pratiche

| Fatto | Conseguenza |
|---|---|
| `scoring.py` usa `zip(strict=True)`: serve **Python ≥ 3.10**, e il Python di sistema qui è 3.9.6 | creare subito un ambiente 3.12 (`uv venv --python 3.12`) |
| Il loader `csv.DictReader` dello stub carica NRBOOK in 6,5 s ma occupa **circa 3 GB di RAM**; polars lo legge in 0,2 s | polars per l'I/O, filtro delle tabelle grandi prima della conversione, `Decimal` nell'aritmetica |
| Si valutano solo le chiavi dei target: le chiavi **in più non costano**, quelle mancanti sì | generare tutte le chiavi plausibili (scadenze, anni, date) |
| t3 viene valutato solo su `surrender_value`; `policy_value` è diagnostico | il diagnostico serve a separare valore e penale |
| I `Decimal` si confrontano per valore (2,50 = 2,5) | nessun problema di formattazione |
| Le correzioni manuali sono nei target locali ma **escluse** dalla valutazione ufficiale | in locale il 100 % è irraggiungibile su t0, t2, t3, t4: vedi i tetti nel §4.0 |
| Il maintainability index è calcolato su **tutti** i `.py` della cartella, ma il README chiede di consegnare lì anche gli strumenti | strumenti di t6 come notebook o HTML in `my_solution/tools/`; chiedere agli organizzatori (§4.7) |
| Il modulo fiscale ha `TB_AMOUNT` vuoto "come NRBOOK" | è il candidato naturale per il punteggio di **generalizzazione**: "domani il cliente chiede le tasse". Non toccarlo ora, ma progettare harness e caricatore in modo che un target nuovo si aggiunga in un'ora |

---

## 4. Regole confermate e obiettivi, task per task

### 4.0 Obiettivi di accuratezza e tetti locali

L'obiettivo è il **100 % su ogni task da t0 a t4 nella valutazione ufficiale**, che esclude le correzioni manuali. In locale, con `check.py`, le correzioni restano nei target, quindi il 100 % ufficiale corrisponde a questi tetti:

| Task | Righe di train | Correzioni manuali trovate | Tetto locale (= 100 % ufficiale) | Stato |
|---|---|---|---|---|
| t0 | 225.858 | 10 | 99,9956 % | **raggiunto** |
| t1 | 15.028 | 0 | 100 % | **raggiunto** |
| t2 | 3.019 | 8 | 99,735 % | struttura chiara, formula da chiudere |
| t3 | 6.153 | almeno 16 | 99,740 % | mattoni pronti, AMC e RSK da chiudere |
| t4 | 34.145 | 20 | 99,941 % | regola pronta, dipende da t3 |
| t5 | — | 54 | F1 → 1 | ricetta pronta |

Regola pratica: **mai inseguire una riga il cui delta è un numero intero di franchi**. È una correzione manuale, non conta per l'accuratezza e vale punti in t5.

### 4.1 t0 Commissioni: 99,9956 % (tetto raggiunto)

```text
righe         rate di NRPREM con PR_STATE = 'P'
versione      riga di NRPOLH valida al PR_RCVDT (VLDFR ≤ d ≤ VLDTO; a parità, la versione più alta)
tier          NRBROK[versione.PH_BRKNR].BR_TIER
tipo premio   6° carattere di RK_TARKEY: L periodico, E unico
tasso         NRCOMR(tier, tipo) valido al PR_RCVDT
commissione   arrotonda_era(PR_AMTRC × tasso, 2)       (in pratica sempre half-up: nessuna riga cambia)
```

| Variante | Righe esatte |
|---|---|
| broker al money date, half-up | **225.848 / 225.858 (99,9956 %)** |
| broker al money date, half-even | 225.847 |
| broker al money date, troncamento | 225.846 |
| broker alla data di scadenza, half-up | 225.846 |
| broker attuale | 224.418 (99,36 %) |
| primo broker | 224.130 (99,23 %) |

I 10 residui hanno tutti delta intero e 6 sono in NREXCP: sono correzioni manuali, quindi **non si toccano** (Appendice B). Implementazione: `esempio_consegna/commission.py`, 1,1–2,1 s.

### 4.2 t1 Prossime scadenze: 100 %

```text
popolazione  polizze con versione valida all'estrazione in PH_STATE = 10 e PH_FREQ ≠ 'E'
periodo      M = 1, Q = 3, H = 6, J = 12 mesi
ancora       se PH_BEGDT ≥ 2007-08-11: ancora = PH_BEGDT
             altrimenti: catena COBOL da PH_BEGDT (scadenza precedente + periodo, giorno limitato
             a fine mese, quindi con deriva) fino all'ultima scadenza prima del 2007-08-11;
             quella data è l'ancora Java
scadenze     ancora + k × periodo, giorno dell'ancora limitato a fine mese (nessuna deriva)
finestra     estrazione < scadenza ≤ estrazione + 1 anno, e scadenza < PH_ENDDT
incasso      LS: primo giorno lavorativo ticinese ≥ scadenza (lun–ven, festivi TI, Venerdì Santo lavorativo)
             UB: uguale alla scadenza
```

| Regola dello scadenzario | Righe esatte |
|---|---|
| solo ancora da `PH_BEGDT` | 14.780 / 15.028 (98,35 %) |
| solo catena da `PH_BEGDT` (deriva sempre) | 13.916 / 15.028 (92,60 %) |
| **ibrida COBOL/Java** | **15.028 / 15.028 (100 %)** |

Il calendario si genera con `holidays.CH(subdiv="TI")`, che funziona offline anche per il 2027 e coincide con quello di Neuron su tutte le date verificate. Nessuna correzione manuale in t1. La data di estrazione arriva come parametro, quindi niente date fisse nel codice. Implementazione: `esempio_consegna/schedule.py` e `collection.py`, 0,7 s.

### 4.3 t2 Valore proiettato: la struttura è chiara, la formula va chiusa

**Cosa è certo:**

- una riga per anno di polizza, e il numero di anni è uguale alla durata (3.019/3.019);
- il valore finale coincide con l'ultimo anno della traiettoria (3.011/3.019): gli 8 casi diversi sono correzioni manuali con delta intero;
- **il tasso di crescita è quello NRILLU alla data di domanda.** Le 7 polizze a premio unico firmate prima di un cambio di tasso e iniziate dopo crescono al tasso della firma. Ad esempio BL10000598 (firma 7.12.2011 al 4 %, inizio 2.1.2012 al 3 %) cresce di 1,0304 l'anno, come le polizze al 4 % (mediana 1,0309);
- la crescita netta mediana delle polizze a premio unico al secondo anno è 1,0102 / 1,0154 / 1,0205 / 1,0309 / 1,0413 per tassi del 2 / 2,5 / 3 / 4 / 5 %, cioè il tasso meno circa lo 0,9–1 % di costi: management charge del pot 2, admin fee e rischio.

**Ordine dei test consigliato** (sui premi unici prima, perché hanno meno gradi di libertà):

1. tasso mensile `(1+i)^(1/12) − 1` oppure `i/12`, sul primo anno delle polizze FLSP senza accordi;
2. entry charge per tier alla data di domanda, poi admin fee e AMC alla data di domanda contro quelli al mese proiettato (il testo della sfida insiste sui "parametri validi alla data della domanda");
3. ordine delle operazioni nel mese (crescita, poi costi, o viceversa) e arrotondamento mensile, con l'era decisa dalla data di domanda;
4. risk charge con età crescente, poi i premi periodici e il pot iniziale (`PD_INIMON`: 24 mesi FK, 12 FX, 0 FS);
5. bisezione: per ogni polizza, il primo anno in cui la traiettoria diverge indica la regola mancante. Raggruppare quegli anni per prodotto, frequenza ed era.

### 4.4 t3 Valore di riscatto: i mattoni pronti e quelli da chiudere

**Mattoni verificati** (righe esatte su `t3_booking`, `NRBOOK` e `t3_surrender_value`):

```text
arrotonda_era   troncamento se la data < 2007-08-11, altrimenti half-up
trade date PRM  primo giorno dopo il money date in cui il fondo ha un prezzo in NRFPRC     567.833/567.833
prezzo PRM      ask del fondo alla trade date (ultima pubblicazione)                        407.636/407.636
importo PRM     arrotonda_era(PR_AMTRC × quota allocazione × (1 − entry rate), 2)           100 % per era
                entry rate = NRAGRE 'ENT' valido al money date, altrimenti NRENTC(tier al money date)
                quota allocazione = NRALLO valida al money date (versione più alta)
cambio          cross via CHF, non arrotondato: (CHF per valuta polizza) / (CHF per valuta fondo)
                codici valuta in maiuscolo; premi: ultimo fixing ≤ trade date − 1; prelievi: ≤ trade date
quote           arrotonda_era(importo × cambio / prezzo, 6), negative per i prelievi            100 %
prezzo prelievi bid all'ultima data di prezzo ≤ data del prelievo                            100 %
admin fee       la somma dei pezzi per fondo e pot = CG_ADMFEE valido alla data del prelievo  397.841/397.842
riscatto        max(0, arrotonda_era(PV × (1 − penale), 2))                                  4.619/4.635
                penale = NRSURR(scala del prodotto, anni compiuti da PH_BEGDT); 0 nei periodi NRWAIV
                (la data di valutazione 2020-04-30 cade nel waiver COVID: nessuna penale)
```

**Ordine e date dei movimenti, già verificati:**

- dentro una corsa mensile (evento 300) i movimenti hanno ID crescenti fondo per fondo e pot per pot, nell'ordine **ADM → AMC → RSK**;
- i prelievi cadono sull'**anniversario mensile** della data d'inizio. Per chi inizia il 29, 30 o 31 il giorno è limitato a fine mese ma torna al giorno d'inizio nei mesi lunghi: **nessuna deriva, nemmeno in era COBOL**, a differenza dello scadenzario dei premi (56.948 corse su 56.948; in totale 517.711 corse sul giorno d'inizio e 15.949 limitate a fine mese);
- vanno **ignorati**: i 208 switch stornati (SWO/SWI di eventi 200 annullati da un 900), i 123 SWI delle correzioni tecniche (990) e i 14.284 PRM di premi stornati.

**Mattoni da chiudere**, ciascuno con le ipotesi da testare per prime, sempre "dato lo stato vero":

| Mattone | Ipotesi da testare | Etichette disponibili |
|---|---|---|
| **AMC** management charge | base = valore della posizione del fondo e pot (quote × bid × cambio) prima o dopo l'ADM; tasso `CG_AMCP1` per il pot 1 e `CG_AMCP2` per il pot 2, oppure l'accordo NRAGRE `AMC` valido alla data (un tasso solo: vale per entrambi i pot?); mensile `tasso/12` oppure `(1+tasso)^(1/12) − 1` | 1.833.960 righe |
| **RSK** risk charge | capitale sotto rischio per opzione: A = 1 % del valore (prestazione 101 %, `RK_SUMIN` = 0 per tutte le 1.836 polizze A), B = max(somma assicurata − valore, 0), C = somma assicurata; qx da NRMORT (tabella `CG_MORTTB` per generazione: M94U per 01/02, M12U per 03/04; sesso: M → 1, W → 2, U → sesso della persona); età all'ultimo compleanno, al più vicino o per aritmetica intera; fattore `(1 + RK_LOAD)`; × `CG_SMKFAC` = 1,5 se `PS_SMOKE = 'J'`; qx/12 | 955.746 righe |
| **Ripartizione ADM** (e di AMC/RSK) tra fondi e pot | proporzionale al valore di ogni posizione; a chi va il resto dell'arrotondamento (pezzo più grande? ultimo fondo?) | 1.827.505 righe |
| **Pot 1 e pot 2** | pot 1 per i premi dei primi `PD_INIMON` mesi (24 FK, 12 FX, 0 FS): per data di scadenza o per trade date? | colonna `BK_POTCD` di NRBOOK |
| **Inizio dei prelievi** | il primo anniversario mensile con quote in portafoglio (BL10000001: prima rata non pagata, primo prelievo a maggio e non ad aprile) | date dei prelievi in NRBOOK |
| **Ordine nella giornata** | premio, corsa dei prelievi e ordine del cliente nello stesso giorno: in che ordine? (dentro la corsa l'ordine è già noto) | `t3_holding` |
| **Valore di polizza** | quote × bid all'ultimo prezzo ≤ data di valutazione × cambio, sommato su fondi e pot; arrotondamento per posizione o sul totale | `t3_holding`, `policy_value` |
| **Stati 60/70** | riscatto o decesso prima della data di valutazione: valore 0 (1.518 righe target sono a 0) | `t3_surrender_value` |

### 4.5 t4 Estratto annuale: aggregazione esatta di t3

```text
premiums         Σ PR_AMTRC delle rate 'P', per anno del PR_RCVDT                          100 %
entry_charges    Σ, movimento PRM per movimento PRM, di (PR_AMTRC × quota allocazione −
                 importo investito), per anno della trade date di quel movimento             100 %
admin_fees       Σ importi ADM per anno della data del prelievo                               99,94 % (20 correzioni manuali)
management_fees  Σ importi AMC per anno                                                       100 %
risk_charges     Σ importi RSK per anno                                                       100 %
total_charges    entry + admin + management + risk
anni             dall'anno d'inizio all'anno del riscatto o del decesso, al più tardi il 2025
```

### 4.6 t5 Outlier: la ricetta

```text
1. calcola con le regole tutti i valori dei task per le polizze presenti in targets_dir
2. candidati = righe in cui target − valore calcolato ≠ 0
3. tieni solo i candidati con delta di franchi interi       ← firma comune alle 54 correzioni trovate
4. aggiungi le righe indicate da NREXCP, mappate col timestamp:
      t4: anno = anno(EX_TSTMP) − 1;  t3: ultima data di valutazione < EX_TSTMP;
      t0: rata con scadenza appena prima di EX_TSTMP (confermata dal delta intero);  t2: la polizza
5. precisione prima di tutto: un delta non intero è una regola mancante, non una correzione
```

Le chiavi devono avere il formato dei target: `("t3_surrender_value", ("BL…", date))`, `("t4_annual_statement", ("BL…", anno))`, `("t0_commission", ("BL…", due_nr))`, `("t2_projected_maturity_value", "BL…")`.

### 4.7 t6 Visualizzazioni e strumenti: cosa consegnare

t6 non si fa domenica: **si costruisce mentre si lavora**, perché ogni strumento serve prima di tutto a trovare le regole. Domenica si impacchetta. Ognuno di questi ha guidato una scoperta di stasera o guiderà quelle di domani:

| # | Strumento | Cosa rende visibile | Stato |
|---|---|---|---|
| 1 | **Harness di verifica** (`verifica.py`) | ogni ipotesi diventa un numero; tabella delle varianti per task | pronto |
| 2 | **MI file per file** (`mi_report.py`) | dove intervenire sulla manutenibilità, come i residui per l'accuratezza | pronto |
| 3 | **Residui per era e per data di elaborazione** | il salto al 2007-08-11 (t1, importi PRM, riscatto) | da impacchettare |
| 4 | **Heatmap a calendario degli incassi LS** | i festivi ticinesi e il Venerdì Santo "lavorativo" | da fare (sabato, P4) |
| 5 | **Timeline di una polizza**: premi, prelievi, quote, valore, stato | il primo strumento da costruire per t3 (BL10000013 e BL10000001 sono ottimi casi) | da fare (sabato mattina, P2) |
| 6 | **Waterfall dell'estratto annuale**: premi → entry → admin → AMC → rischio | la coerenza tra t3 e t4 | da fare (sabato sera, P2) |
| 7 | **Istogramma dei delta per task** | i delta interi delle correzioni manuali contro gli errori di regola (±0,01, derive): è la spiegazione visiva di t5 | da fare (domenica, P1) |

**Dove e in che formato.** Il README dello starter kit chiede di consegnare gli strumenti **dentro** `my_solution`, ma `scoring.py` calcola il MI su **tutti** i `.py` di quella cartella, mentre il testo della sfida dice che contano solo i file dei task. Finché gli organizzatori non chiariscono: strumenti in `my_solution/tools/` come **notebook (`.ipynb`) e pagine HTML**, che non entrano nel calcolo, e la domanda agli organizzatori fatta sabato mattina. Se gli strumenti devono essere `.py`, vanno scritti con le stesse regole del §5.

---

## 5. Manutenibilità: come arrivare a MI 95

### 5.1 Come radon calcola l'indice (verificato sul codice sorgente di radon 6.0.1)

`scoring.py` calcola, per ogni file `.py` della cartella di consegna (anche nelle sottocartelle):

```text
MI = (171 − 5,2·ln V − 0,23·G − 16,2·ln LLOC + 50·sin(√(2,46 · C in radianti))) · 100 / 171,  limitato a [0, 100]
```

e poi la **media dei file pesata per righe di codice**. I quattro ingredienti:

| Simbolo | Cosa misura | Come pesa | Fatto misurato |
|---|---|---|---|
| **LLOC** | righe logiche (istruzioni) del file | il termine più pesante: raddoppiare il file costa ~6,6 punti | lo stesso codice in un file unico fa **11,3**, diviso in 8 moduli coesi fa **66,8** per file |
| **V** | volume di Halstead: operatori e operandi aritmetici, logici e di confronto | logaritmico | **le chiamate di funzione non contano**: un file di sole chiamate ha V = 0 e MI 100 |
| **G** | complessità ciclomatica totale (if, for, while, and, or, except, comprehension) | lineare, 0,13 punti per ramo | conta, ma meno degli altri |
| **C** | righe di commento `#` + righe di docstring **multi-riga**, in % delle righe di codice | fino a **+29 punti**, con un massimo intorno al 55 % | una docstring di **una riga vale zero**: stessa funzione, MI 81,1 con docstring di una riga, 100 con due righe |

**La curva dei commenti** (stessa funzione da 20 righe, docstring sempre più lunga):

| Righe di commento/docstring rispetto al codice | 0 % | 18 % | 36 % | **55 %** | 73 % | 109 % | 182 % | 273 % |
|---|---|---|---|---|---|---|---|---|
| MI | 50,9 | 73,0 | 78,2 | **79,7** | 79,1 | 74,7 | 60,4 | 42,4 |

Troppi commenti fanno **scendere** l'indice. La fascia buona è tra il 40 % e l'80 %.

**Un modulo di soli dati** (convenzioni, tabelle) ha V = 0 e MI 100: le "regole come dati" del documento sono anche la scelta migliore per l'indice.

### 5.2 Le dieci regole di scrittura

1. **Un modulo per concetto di business**, al massimo circa 30 righe logiche. Se cresce, si divide per concetto (`premiums`, `collection`, `valuation`…), mai a caso.
2. **Docstring multi-riga** per ogni modulo e ogni funzione non banale: la regola in linguaggio di business e l'evidenza ("225.848 righe esatte su 225.858"). Sono ciò che legge l'auditor e alzano l'indice.
3. **Rapporto commenti/codice tra il 40 % e l'80 % per file**, misurato con `mi_report.py`: né scarno né prolisso.
4. **Le convenzioni sono dati** in `conventions.py`, ciascuna con un commento che cita la fonte: MI 100 e una pagina sola per l'auditor.
5. **L'aritmetica sta in pochi helper** (`money.py`, `months.py`, `business_days.py`); i moduli di regola compongono chiamate, che non pesano nel volume.
6. **Tabelle al posto di catene di `if`**: `{"D": day, "N": number}.get(kind, str.strip)`.
7. **Funzioni con complessità ≤ 5**: comprehension, `filter` e `itertools` al posto di cicli annidati con condizioni.
8. **Librerie standard per problemi standard**: `relativedelta` per i mesi con fine mese, `strptime` per le date, `holidays` per i festivi. Meno codice, meno volume, più fiducia dell'auditor.
9. **Nomi del dominio**: `paid_items`, `version_on`, `collection_day`, `pays_premiums`.
10. **Nessun `.py` di tool o sonde dentro `my_solution`**: `scoring.py` misura tutti i `.py` della cartella. Le sonde stanno fuori; gli strumenti da consegnare per t6 vanno in `my_solution/tools/` come notebook o HTML (§4.7).

**Cosa non fare:** riempire di commenti vuoti (oltre l'80–120 % l'indice scende e l'auditor se ne accorge); frammentare in moduli da tre righe senza un concetto; nascondere logica in stringhe o `eval`; togliere controlli di correttezza per abbassare la complessità. L'indice deve salire perché il codice migliora, non al posto di migliorarlo.

### 5.3 La dimostrazione: t0 e t1 da 83,3 a 94,6 senza perdere una riga

Ogni passo è misurato con `check.py` (accuratezza) e `scoring.maintainability` (MI) ufficiali:

| Passo | Cosa è cambiato | MI | t0 | t1 |
|---|---|---|---|---|
| 1 | prima versione funzionante, sette moduli | 83,3 | 99,9956 % | 100 % |
| 2 | docstring con regola ed evidenza, rapporto commenti al 55–65 % | 86,8 | = | = |
| 3 | moduli coesi: `formats` (formati legacy), `lookup` (validità), `portfolio` (versioni) | 90,4 | = | = |
| 4 | librerie standard: `strptime` (CYYMMDD + 19.000.000), `relativedelta`; incasso in `collection` | 91,7 | = | = |
| 5 | concetti riusabili: `premiums` (rate pagate, tipo premio), `pays_premiums` nel portafoglio | 92,6 | = | = |
| 6 | `dates` diviso in `months` e `business_days`; `submission` fa solo composizione, le regole lavorano su una rata o una polizza | 93,2 | = | = |
| 7 | rapporto commenti riportato tra il 40 % e l'80 % nei file piccoli (con troppe docstring l'indice scendeva) | **94,6** | **99,9956 %** | **100 %** |

Il MI file per file alla fine:

| Modulo | MI | Modulo | MI | Modulo | MI |
|---|---|---|---|---|---|
| `submission.py` | 100 | `conventions.py` | 100 | `money.py` | 100 |
| `months.py` | 100 | `collection.py` | 99,5 | `premiums.py` | 98,5 |
| `lookup.py` | 97,8 | `commission.py` | 96,2 | `formats.py` | 89,9 |
| `business_days.py` | 89,9 | `portfolio.py` | 89,5 | `legacy.py` | 89,3 |
| `schedule.py` | 88,6 | | | | |

### 5.4 L'architettura della consegna completa, con il budget di ogni modulo

| Modulo | Concetto | Task | Budget LLOC |
|---|---|---|---|
| `submission.py` | le 6 funzioni, solo composizione | tutti | 25 |
| `conventions.py` | le manopole (Appendice C), solo dati | tutti | libero (MI 100) |
| `formats.py`, `legacy.py`, `lookup.py` | formati, lettura, validità | tutti | 20–25 ciascuno |
| `portfolio.py`, `premiums.py` | polizze e versioni; rate | tutti | 20 ciascuno |
| `money.py`, `months.py`, `business_days.py`, `collection.py` | arrotondamenti e importi; mesi; giorni lavorativi; incasso | tutti | 20 ciascuno |
| `commission.py`, `schedule.py` | t0, t1 | t0, t1 | 20–25 |
| `market.py` | prezzi ask/bid all'ultima pubblicazione, giorni di prezzo, cambi as-of in maiuscolo | t3 | 25 |
| `investment.py` | premio → quote: trade date, entry, allocazione, pot | t3, t4 | 25 |
| `charges.py` | ADM e AMC: importi e ripartizione tra fondi e pot | t3, t4 | 25 |
| `risk.py` | RSK: capitale sotto rischio, qx, età | t2, t3 | 25 |
| `orders.py` | ordini del cliente da NRBOOK | t3 | 15 |
| `accounting.py` | posizioni per fondo e pot nel tempo | t3, t4 | 30 |
| `valuation.py` | valore di polizza, penale, riscatto | t3 | 20 |
| `statement.py` | somme annuali | t4 | 20 |
| `projection.py` | proiezione dell'offerta | t2 | 30 |
| `outliers.py` | delta interi e NREXCP | t5 | 25 |

Con questi budget e le regole del §5.2 la stima è un MI complessivo intorno a 95: lo scheletro con 13 moduli è già a 94,6.

### 5.5 Il cancello della manutenibilità nel processo

- **Prima di ogni merge:** `python $PIANO/verifica_dati/mi_report.py $DATI/starter_kit/my_solution` (variabili come nell'Appendice D). Il MI complessivo **non scende mai sotto 94** (obiettivo finale ≥ 95); nessun file sotto 85; un file sopra 30 righe logiche si divide per concetto.
- **Il MI si mantiene, non si recupera.** Due ore di refactoring domenica non bastano per un monolite da 300 righe (MI 11 nel test del §5.1). Si scrive già nello stile giusto.
- **Lo stesso rigore dell'accuratezza:** ogni intervento sul MI si misura, e se l'accuratezza scende di una riga si torna indietro.

---

## 6. Come mi comporterei: il metodo operativo

### 6.1 Il ciclo da 30–45 minuti

1. **Isola il sotto-problema più piccolo che ha un'etichetta.** "Quote dei PRM in valuta estera", non "t3".
2. **Scrivi la regola più semplice** che segue dalla descrizione del task.
3. **Conta le righe esatte.** Solo il conteggio decide.
4. **Se non è 100 %, raggruppa i residui** per era, anno, prodotto, valuta, fondo, tier, frequenza, giorno del mese, giorno della settimana, festivo, stato. La dimensione in cui si concentrano è la condizione nascosta. Tre esempi di stasera: i residui di t1 erano tutti su giorni 29–31 e in era COBOL; quelli delle quote erano su valute diverse in date precise, cioè i codici minuscoli; quelli della trade date cadevano tutti nei giorni senza prezzo del fondo.
5. **Formula da 2 a 5 varianti concrete** e misurale tutte nello stesso run.
6. **Accetta una variante solo se** migliora nettamente, non peggiora altre righe e si spiega in una frase di business. Poi la registri nel registro delle ipotesi e in `conventions.py`.
7. **Scrivila subito nello stile del §5**: modulo del suo concetto, docstring con regola ed evidenza, MI misurato.
8. **Se restano poche righe isolate con delta intero, fermati**: sono correzioni manuali e vanno in t5.

### 6.2 Le regole d'ingaggio

- **Nessuna discussione senza un numero.** "Secondo me è half-even" non è un argomento; "225.847 contro 225.848" sì.
- **Una manopola per volta, ma tutte le sue varianti insieme.**
- **Mai piegare una regola per una riga isolata.** Le correzioni manuali sono escluse dall'accuratezza e valgono punti in t5.
- **La leaderboard pubblica è un termometro, non una bussola.** Si guarda dopo ogni invio, non si usa per scegliere le regole.
- **Nessun parametro cablato.** Date di valutazione e di estrazione arrivano come argomenti; le date di regime vivono in `conventions.py`.
- **Time-box di 45 minuti per famiglia di ipotesi.** Se nulla si muove, si cambia sotto-problema o si chiama un secondo paio d'occhi.
- **Due cancelli per ogni merge:** l'harness dell'accuratezza e `mi_report.py`.
- **Una sola fonte di verità per le convenzioni**, condivisa da tutti: ogni scoperta migliora subito i numeri degli altri.

### 6.3 Il registro delle ipotesi

Una tabella in Markdown, aggiornata a ogni giro: diventa il cuore del README e la prova del metodo per il punteggio di generalizzazione. Le prime righe sono quelle di stasera:

| ID | Ipotesi | Test | Risultato | Decisione |
|---|---|---|---|---|
| H01 | Broker valido al money date | t0, 4 basi × 3 arrotondamenti | 99,9956 % contro 99,9947 % (data di scadenza) | adottata |
| H02 | Scadenzario: catena COBOL, ancora Java | t1, 3 regole | 100 % contro 98,35 % e 92,60 % | adottata |
| H03 | LS al primo giorno lavorativo TI, anche oltre fine mese | t1 | 100 % (261 incassi passano al mese dopo) | adottata |
| H04 | Importo PRM troncato in COBOL, half-up in Java | 60.000 PRM | 100 % / 100 % | adottata |
| H05 | Trade date = primo giorno con prezzo del fondo | 567.833 PRM | 100 % (calendario TI: 99,52 %) | adottata |
| H06 | Codici valuta in maiuscolo | 1.548.688 movimenti cross-valuta | 100 % (case-sensitive: 99,87 %, 454 polizze) | adottata |
| H07 | Artefatti double nelle quote | 120.000 movimenti | nessuna differenza | scartata |
| H08 | NRILLU alla data di domanda | 7 polizze a cavallo | 7/7 | adottata (t2) |
| H09 | Arrotondamento d'era anche per le commissioni | t0 | 225.848, invariato | adottata: una sola politica |

### 6.4 L'AI nel ciclo

- **L'LLM scrive le sonde, l'harness decide.** Il prompt che rende di più contiene il comando dell'harness, il report dei residui raggruppati, `conventions.py`, il registro delle ipotesi e la richiesta di "tre varianti con la regola in una frase, implementate come configurazione".
- **Una sonda, un'ipotesi, un numero.** Stasera ne ho fatte una trentina in poche ore; nessuna richiedeva PySR, Z3 o un algoritmo evolutivo.
- **L'LLM è utile anche per il MI:** gli si passa l'output di `mi_report.py` e il modulo, chiedendo di dividere per concetto e di scrivere le docstring con la regola. Poi si rimisurano accuratezza e MI.
- **Gli strumenti pesanti restano piano B.** Se il risk charge resiste alla griglia (età × tabella × fattori × arrotondamento), allora sì: ragionamento a intervalli per il caricamento implicito (vedi il documento), alberi decisionali sui residui (`scikit-learn`), e solo dopo Z3 o la ricerca simbolica.
- **Mai far entrare in consegna codice generato senza i due cancelli.**

### 6.5 I ruoli

**In quattro:**

| Persona | Responsabilità | Venerdì notte | Sabato | Domenica |
|---|---|---|---|---|
| **P1, dati, harness e qualità** | `legacy.py`, `conventions.py`, harness, `mi_report`, invii, tempi | copia dello scheletro, primo invio | ricostruzione dello stato vero per P2 e P3; integrazione; guardiano del MI | t5, robustezza, invio finale |
| **P2, contabilità a quote** | `market`, `investment`, `orders`, `accounting`, `valuation` | ambiente e lettura del §4.4 | motore t3, `t3_holding`, valore di polizza | riscatto e t4 (`statement`) |
| **P3, prelievi** | `charges`, `risk` | ambiente e lettura del §4.4 | AMC e RSK al 100 % dato lo stato vero | supporto t3, docstring |
| **P4, proiezione** | `projection`, poi t6 e README | ambiente e sonda sul tasso mensile | t2 con la bisezione; condivide `risk` con P3 | t6, README, registro delle ipotesi |

**In tre:** P1 prende anche t2; P2 e P3 restano su t3.

**Rituale:** ogni tre ore, dieci minuti davanti alle due tabelle (accuratezza per task e MI per file): cosa è cambiato, cosa è bloccato, chi aiuta chi. **Definizione di "fatto"** per un mattone: almeno il 99,9 % sul suo diagnostico, residui spiegati (delta interi o casi noti) e modulo con MI ≥ 85.

---

## 7. Il piano: le mosse fino a domenica alle 16:00

### 7.0 La copertura dei sette task

Il piano porta a termine **tutti e sette i task**: i cinque valutati per accuratezza e i due bonus.

| Task | Dove si chiude | Chi | Criterio di uscita | Stato venerdì alle 23:45 |
|---|---|---|---|---|
| **t0** Commissioni | Mossa 1 | P1 | tetto locale 99,9956 % | **fatto** (`esempio_consegna/`) |
| **t1** Prossime scadenze | Mossa 1 | P1 | 100 % | **fatto** (`esempio_consegna/`) |
| **t2** Valore proiettato | Mosse 3–5, in parallelo | P4 | tetto locale 99,735 % (= 100 % ufficiale) | struttura e tasso noti; formula mensile da chiudere |
| **t3** Valore di riscatto | Mosse 2–5 | P2 + P3 | tetto locale 99,740 % | tutti i mattoni al 100 % tranne AMC e RSK |
| **t4** Estratto annuale | Mossa 5 | P2 | tetto locale 99,941 % | regola verificata; arriva con t3 |
| **t5** Outlier (bonus) | Mossa 6 | P1 | sul train ritrova le 54 correzioni note, nessun falso positivo | ricetta pronta (§4.6) |
| **t6** Visualizzazioni e strumenti (bonus) | costruiti durante il lavoro, impacchettati nella Mossa 7 | P4 | i sette strumenti del §4.7 consegnati e citati nel README | due su sette pronti (`verifica.py`, `mi_report.py`) |

La sequenza segue le dipendenze: **t4 dipende da t3**, **t5 dipende dalle regole di tutti gli altri task** (ogni riga che non torna è un candidato), e **t2 condivide con t3 le formule dei costi** (`risk.py`, `charges.py`). Per questo t3 è il percorso critico e t5 arriva per ultimo.

| Quando | Mossa | Obiettivo | Finita quando |
|---|---|---|---|
| ven 23:30 – 01:30 | **1. Fondamenta e primi punti** | ambiente comune, `esempio_consegna/` copiato in `my_solution/`, primo invio | `check.py`: t0 99,9956 %, t1 100 %; MI ≥ 94; leaderboard aggiornata |
| sab 08:00 – 09:30 | **2. Lo stato vero** | posizioni ricostruite da `t3_booking` e ordini; harness "passo per passo" | ogni prelievo ha il suo valore "prima" calcolato |
| sab 09:30 – 13:00 | **3. I mattoni aperti** | AMC, RSK, ripartizione, pot; avvio di t2 | ogni tipo di movimento ≥ 99,9 % dato lo stato vero |
| sab 14:00 – 19:00 | **4. La catena** | simulazione mese per mese; `t3_holding`, valore di polizza; t2 con la bisezione | `t3_holding` ≥ 99,5 %; t2 annuale ≥ 99 %; MI ≥ 94 |
| sab 19:00 – 23:00 | **5. Riscatto e t4** | valore di riscatto, t4 per somma, secondo invio; chiusura t2 | t3 e t4 ai tetti del §4.0; MI ≥ 94 |
| dom 08:00 – 11:00 | **6. t5 e robustezza** | ricetta t5; date di valutazione diverse; nessun crash; tempi | t5 trova le 54 del train; esecuzione completa misurata |
| dom 11:00 – 13:00 | **7. Rifinitura** | docstring, README, t6, MI verso 95 e oltre | MI ≥ 95, README con il registro delle ipotesi |
| dom 13:00 – 14:00 | **8. Candidato finale** | invio, controllo in leaderboard | numeri coerenti con quelli locali |
| dom 14:00 – 16:00 | **9. Margine** | solo correzioni di bug, consegna entro le 15:00 | consegnato |

### Mossa 1: fondamenta e primi punti (stanotte)

- **Perché adesso:** t0 e t1 sono già scritte e misurate (`esempio_consegna/`). Inviarle subito vale punti e il bonus "perfect match" su t1, e collauda tutta la catena: Python dell'evaluatore, `requirements.txt`, tempi.
- **Come:**
  1. impostare `PIANO` e `DATI` e creare l'ambiente 3.12 come nell'Appendice D;
  2. `python $PIANO/verifica_dati/verifica.py --data $DATI` (deve riprodurre `output_atteso.txt`);
  3. copiare `$PIANO/esempio_consegna/*` in `$DATI/starter_kit/my_solution/`;
  4. da `$DATI/starter_kit`: `python check.py --tasks t0_commission t1_next_due_dates` e `python $PIANO/verifica_dati/mi_report.py my_solution`;
  5. invio.
- **Rischio:** voler riscrivere lo scheletro. Va bene così: si estende, non si rifà.

### Mossa 2: lo stato vero (sabato mattina presto)

- **Perché:** è il moltiplicatore di tutto il sabato. Con le posizioni vere prima di ogni prelievo, AMC e RSK diventano test isolati al posto di una simulazione trentennale.
- **Come:** per ogni polizza, ordinare i movimenti di `t3_booking` e gli ordini del cliente di NRBOOK per data e ID di prenotazione; somma cumulata delle quote per fondo e pot; valore = quote × bid alla data prezzo del movimento. È uno strumento di analisi che legge i target, quindi resta fuori da `my_solution` (anche per il MI).
- **Finita quando:** l'harness stampa, per ogni tipo di prelievo, la percentuale esatta "dato lo stato vero".

### Mossa 3: i mattoni aperti (sabato mattina)

- **Perché:** AMC e RSK sono le sole incognite vere di t3. Tutto il resto è già al 100 %.
- **Come:** la griglia del §4.4, una manopola per volta, residui raggruppati. Per RSK si parte dalle polizze con opzione A (capitale sotto rischio = 1 % del valore, nessuna somma assicurata), non fumatori, senza caricamento medico: il caso più pulito. Poi si aggiungono fumo (`J`), caricamento ed età. Ogni mattone chiuso entra subito nel suo modulo (`charges.py`, `risk.py`) con la sua docstring.
- **Rischio:** convenzione d'età e date di nascita impossibili. Le 8 polizze di train con date impossibili sono il test decisivo per scegliere tra aritmetica intera e aritmetica di calendario.

### Mossa 4: la catena (sabato pomeriggio)

- **Perché:** solo ora conviene simulare, perché ogni passo è già giusto dato lo stato giusto.
- **Come:** un motore a eventi per polizza: premi (trade date, prezzo ask, pot), prelievi mensili (date, prezzo bid, ordine), ordini del cliente presi da NRBOOK, esclusione di storni (900) e correzioni tecniche (990). Confronto con `t3_holding` alle tre date; il primo scarto per polizza indica il passo sbagliato.
- **In parallelo:** P4 chiude t2 con la bisezione annuale.

### Mossa 5: riscatto e t4 (sabato sera)

- **Perché:** con le posizioni giuste, riscatto e t4 sono formule già verificate (§4.4, §4.5).
- **Come:** valore di polizza → regola del riscatto; t4 come somma per anno. Secondo invio.

### Mossa 6: t5 e robustezza (domenica mattina)

- **t5:** la ricetta del §4.6, con precisione prima di tutto.
- **Robustezza:** le date di valutazione private possono essere altre. Vanno provate date dentro il waiver del 2008, a cavallo dello switch (2007-08-10 e 2007-08-11), un sabato, prima della prima rata, dopo un riscatto. Il codice non deve mai andare in crash su una polizza: si registra l'errore e si continua.
- **Tempi:** esecuzione completa misurata sull'intero dataset, con margine rispetto al limite (ignoto: chiederlo agli organizzatori).

### Mossa 7: rifinitura (domenica a fine mattina)

- **MI ≥ 95:** `mi_report.py`, poi intervento sui due o tre file più bassi, come nel §5.3.
- **t6:** i sette strumenti del §4.7 in `my_solution/tools/`, ciascuno con una riga nel README su quale regola ha aiutato a trovare.
- **README:** approccio, regole trovate, registro delle ipotesi, strumenti di t6.

### Mosse 8 e 9: candidato finale e margine (domenica dalle 13)

Dopo le 14 entrano solo correzioni di bug con un test che le dimostra. L'ultimo invio va fatto entro le 15:00, non alle 15:55.

---

## 8. Rischi e checklist di consegna

| Rischio | Probabilità | Impatto | Contromisura |
|---|---|---|---|
| Un mattone sbagliato rovina intere polizze in t3 (dipendenza dal percorso) | alta | alto | validare ogni mattone "dato lo stato vero" prima di incatenare (Mosse 2–4) |
| Date di valutazione private diverse da quelle di train | media | alto | parametri; test su date speciali (Mossa 6) |
| Limite di tempo dell'evaluatore superato | media | alto | polars, filtro delle tabelle grandi, misura dal primo giorno, chiedere il limite agli organizzatori |
| Ambiente diverso (Python < 3.10, versioni delle librerie) | media | medio | `requirements.txt` con versioni fissate, prova in un ambiente pulito |
| MI che crolla quando arriva il motore di t3 | alta | alto | budget di righe per modulo (§5.4), cancello MI a ogni merge |
| Tool e sonde `.py` dentro `my_solution` | alta | medio | sonde fuori dalla cartella; strumenti di t6 come notebook o HTML; domanda agli organizzatori |
| t6 lasciato a domenica pomeriggio | media | medio | strumenti costruiti durante il lavoro (§4.7), solo impacchettati nella Mossa 7 |
| Overfitting sulla leaderboard pubblica | media | medio | regole scelte solo sul train; la leaderboard serve da controllo |
| Divergenza tra i membri del team | media | medio | un solo harness, un solo `conventions.py`, merge piccoli e frequenti |
| Crash su una polizza con dati anomali | media | alto | try/except per polizza con log; test sulle 10 date impossibili e sui codici minuscoli |
| Lettura dei target fuori da t5 | bassa | squalifica | revisione del codice prima dell'invio finale |

**Checklist prima di ogni invio:**

- [ ] `python check.py` (Python ≥ 3.10) gira su tutti i task senza errori
- [ ] ogni task è al suo tetto locale (§4.0) o il residuo è spiegato
- [ ] `mi_report.py my_solution`: MI ≥ 95, nessun file sotto 85, nessun file sopra 30 righe logiche
- [ ] tempo totale misurato sull'intero dataset
- [ ] nessuna lettura di file target, tranne in t5 (`targets_dir`)
- [ ] `valuation_dates` ed `extract_date` presi dagli argomenti
- [ ] nessun `float` negli importi
- [ ] `requirements.txt` con versioni fissate, provato in un ambiente pulito
- [ ] nessun tool o sonda `.py` dentro `my_solution`; strumenti di t6 in `my_solution/tools/` come notebook o HTML
- [ ] README e registro delle ipotesi aggiornati

---

## 9. Appendici

### A. I numeri del dataset

| Voce | Valore |
|---|---|
| Tabelle legacy | 27 (23 del perimetro della sfida + 4 del modulo fiscale) |
| Polizze nell'export | 4.011: 3.019 di train (con target) e 992 pubbliche; circa 989 private non visibili |
| Prodotti | FLKL (famiglia FK, pot iniziale 24 mesi, scala 1), FLFX (FX, 12 mesi, scala 2), FLSP (FS, premio unico, scala 3) |
| Stati attuali | 10: 2.744 · 20: 91 · 30: 5 · 60: 1.096 · 70: 75 |
| Valute delle polizze | CHF 2.538 · EUR 1.074 · GBP 199 · USD 200; fondi anche in SEK |
| Frequenze | M 2.159 · Q 715 · H 100 · J 276 · E 761 |
| Pagamento | LS 3.269 · UB 742 |
| NRBOOK | 6.797.112 movimenti (409 MB); i calcolati (PRM, ADM, AMC, RSK) hanno importi vuoti; 24.912 ordini del cliente |
| NREVNT | 872.039 eventi; 946 conversioni; 8.130 storni |
| Target | t0 225.858 · t1 15.028 · t2 3.019 (+79.040 annuali) · t3 6.153 (+31.578 posizioni, +5.024.847 movimenti) · t4 34.145 |

### B. Le 54 correzioni manuali trovate nel train

Sono il seme del t5 e la prova che le regole sono giuste: tutte hanno un delta di franchi interi. (N) indica che la riga è elencata in NREXCP.

**t0 (polizza, rata, delta):** BL10000237 / 41 / +44,00 (N) · BL10001299 / 103 / +74,00 · BL10001328 / 1 / +77,00 · BL10001567 / 6 / +27,00 (N) · BL10002438 / 11 / +68,00 · BL10002462 / 5 / +16,00 (N) · BL10003175 / 247 / +9,00 (N) · BL10004049 / 6 / +36,00 (N) · BL10004554 / 35 / +11,00 · BL10004722 / 1 / +34,00 (N)

**t2 (polizza, delta tra valore finale e ultimo anno):** BL10000128 +4.855,00 (N) · BL10001762 +1.574,00 (N) · BL10002196 +1.726,00 · BL10002973 +1.498,00 · BL10003323 +1.947,00 (N) · BL10003583 −1.261,00 (N) · BL10003808 −3.955,00 (N) · BL10004278 +3.294,00

**t3 (polizza, data di valutazione, delta):** BL10000321 / 2025-12-31 / +175,00 · BL10000694 / 2025-12-31 / +358,00 (N) · BL10000768 / 2020-04-30 / +117,00 · BL10001063 / 2020-04-30 / +34,00 (N) · BL10001080 / 2020-04-30 / +158,00 · BL10001756 / 2025-12-31 / +215,00 (N) · BL10001820 / 2025-12-31 / +228,00 (N) · BL10001897 / 2020-04-30 / +114,00 (N) · BL10002328 / 2020-04-30 / +499,00 · BL10002704 / 2025-12-31 / +15,00 (N) · BL10003429 / 2020-04-30 / +498,00 (N) · BL10003599 / 2025-12-31 / +484,00 (N) · BL10004276 / 2025-12-31 / +189,00 (N) · BL10004585 / 2025-12-31 / +262,00 (N) · BL10004896 / 2025-12-31 / +474,00 · BL10004914 / 2020-04-30 / +29,00 (N)

**t4, admin fee (polizza, anno, delta):** BL10000099 / 2001 / +147,00 (N) · BL10000139 / 2014 / +136,00 (N) · BL10000151 / 2015 / +123,00 (N) · BL10000182 / 2014 / +45,00 (N) · BL10000595 / 2024 / +30,00 (N) · BL10002682 / 2004 / +48,00 (N) · BL10002708 / 2013 / +132,00 (N) · BL10003181 / 2018 / +121,00 (N) · BL10003208 / 2010 / +115,00 (N) · BL10003421 / 2023 / +7,00 (N) · BL10003489 / 2016 / +23,00 (N) · BL10003550 / 2011 / +21,00 (N) · BL10003698 / 2025 / +136,00 (N) · BL10003860 / 2019 / +45,00 (N) · BL10003910 / 2024 / +21,00 · BL10004031 / 2013 / +96,00 · BL10004781 / 2009 / +66,00 (N) · BL10004816 / 2007 / +56,00 (N) · BL10004844 / 2018 / +46,00 · BL10004909 / 2017 / +53,00

### C. Le manopole (`conventions.py`) con i valori trovati

| Manopola | Valore | Fonte |
|---|---|---|
| `ERA_SWITCH` | 2007-08-11 | NREVNT evento 800 |
| `ROUNDING_COBOL` | troncamento (`ROUND_DOWN`) | importi PRM, quote, riscatto |
| `ROUNDING_JAVA` | half-up (`ROUND_HALF_UP`) | importi PRM, quote, riscatto, commissioni |
| `UNIT_DECIMALS` | 6 | NRBOOK |
| `PAID` (rate che contano) | `P` | t0, t4 |
| `COMMISSION_BROKER_DATE` | money date | t0 |
| `ENTRY_RATE_DATE`, `ALLOCATION_DATE` | money date | importi PRM |
| `ADMIN_FEE_DATE` | data del prelievo | ADM, t4 |
| `ILLUSTRATION_RATE_DATE` | data di domanda | t2 |
| `PREMIUM_TRADE_DATE` | primo giorno con prezzo del fondo dopo il money date | NRBOOK |
| `PREMIUM_PRICE` / `CHARGE_PRICE` | ask / bid | `t3_booking` |
| `PREMIUM_FX_DATE` / `CHARGE_FX_DATE` | trade date − 1 / trade date (ultimo fixing ≤) | `t3_booking` |
| `FX_CODE_CASE` | maiuscolo | NRFXRT |
| `PRICE_PUBLICATION` | l'ultima `FP_CHGTS` | NRFPRC |
| `SCHEDULE_COBOL` / `SCHEDULE_JAVA` | catena con deriva / ancora fissa | t1 |
| `COLLECTION_LS` / `COLLECTION_UB` | primo giorno lavorativo TI ≥ scadenza / scadenza | t1 |
| `HOLIDAY_COUNTRY`, `HOLIDAY_REGION` | `CH`, `TI` | t1 |
| `SURRENDER_PENALTY` | NRSURR(scala, anni compiuti da `PH_BEGDT`); 0 in NRWAIV; minimo 0 | t3 |
| `SMOKER_CODE` | `J` | NRPERS |
| `CENTURY_OFFSET` | 19.000.000 (CYYMMDD + 19.000.000 = YYYYMMDD) | SCHEMA.md |

### D. Come riprodurre

Questa cartella (il repository del team) e i dati della sfida stanno in posti diversi: due variabili, da adattare
alla propria macchina, tengono i comandi indipendenti dai percorsi.

```bash
export PIANO=~/Documents/Neural-Wave/ch-Fable-7.4             # questa cartella
export DATI=~/Downloads/LifewareChallenge/participants        # i dati della sfida (legacy/, targets/, starter_kit/)
uv venv --python 3.12 .venv && source .venv/bin/activate
uv pip install -r $PIANO/esempio_consegna/requirements.txt radon
python $PIANO/verifica_dati/verifica.py --data $DATI              # circa 6 s; confronto con verifica_dati/output_atteso.txt
python $PIANO/verifica_dati/verifica.py --data $DATI --sample 0   # tutte le righe nei controlli riga per riga (circa 30 s)
cd $DATI/starter_kit
python check.py --submission $PIANO/esempio_consegna --tasks t0_commission t1_next_due_dates
python $PIANO/verifica_dati/mi_report.py $PIANO/esempio_consegna
```

### E. Glossario rapido

- **Era COBOL / era Java:** il periodo in cui Neuron girava in COBOL (fino al 10.8.2007) e quello di Neuron NG in Java (dall'11.8.2007).
- **As-of:** il valore valido a una certa data, cioè l'ultimo pubblicato quel giorno o prima.
- **Money date / trade date:** il giorno in cui arrivano i soldi / il giorno in cui si comprano o vendono le quote.
- **Mattone:** un singolo passo del calcolo verificabile da solo (per esempio "importo investito di un premio").
- **Stato vero:** le quote effettive prima di un movimento, ricostruite dai diagnostici.
- **Delta intero:** differenza tra target e regola pari a un numero intero di unità di valuta, la firma delle correzioni manuali.
- **Tetto locale:** la massima accuratezza ottenibile con `check.py`, che conta anche le correzioni manuali; corrisponde al 100 % della valutazione ufficiale.
- **LLOC, V, G, C:** le quattro componenti del maintainability index (§5.1).
