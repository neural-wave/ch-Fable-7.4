"""The words of the story (`story.py`), in English and Italian, for a reader who knows nothing about computers or
insurance.

Every text is a template: `{name}` is replaced by a number or a date of `runs/story.json`, already formatted for the
language. Every term a lay reader may not know is in bold where it first appears and is explained there and in the
GLOSSARY; BANNED lists the words of the trade that must not appear at all (`tests/test_story.py` checks both
languages). A first draft was read by a fresh agent playing a reader of 75 with no background (step S3 of the plan);
this version answers every point of its report.
"""
LANGUAGES = ("en", "it")

BANNED = [  # words of computers, data and this project that a lay reader would not know; none may appear
    "COBOL", "Java", "NRBOOK", "NRPOLH", "NREVNT", "parquet", "JSON", "CSV", "SQL", "DSL", "Python", "algorithm",
    "algoritmo", "dataset", "ablation", "holdout", "cluster", "regression", "regressione", "batch", "legacy", "schema",
    "pipeline", "target", "submission", "decimal", "boolean", "query", "timestamp", "API", "lab ", "t0_", "t1_",
    "t2_", "t3_", "t4_", "t5_", "booking", "Decimal", "ROUND_", "NGBATCH", "CBLBATCH", "outlier", "F1", "switch off",
    "spegn",
]

TITLE = {
    "en": "The journey of 100 francs",
    "it": "Il viaggio di 100 franchi",
}
SUBTITLE = {
    "en": "What a computer program called Neuron did with the money of one real customer, month after month, from "
          "{start_year} to the end of {last_year}. Written for someone who has never worked with computers or insurance.",
    "it": "Che cosa ha fatto un programma per computer chiamato Neuron con i soldi di una persona reale, mese dopo "
          "mese, dal {start_year} alla fine del {last_year}. Scritto per chi non ha mai lavorato con i computer o con "
          "le assicurazioni.",
}
NEURON = {
    "en": "<strong>Neuron</strong> is the computer program that an insurance company has used for decades to manage its "
          "contracts and do all the calculations. It is being replaced by a new program, which must give exactly the "
          "same results. We are the team that builds the new program. All amounts are in Swiss francs, written "
          "<strong>CHF</strong>.",
    "it": "<strong>Neuron</strong> è il programma per computer che una compagnia di assicurazioni usa da decenni per "
          "gestire i suoi contratti e fare tutti i calcoli. Viene sostituito da un programma nuovo, che deve dare "
          "esattamente gli stessi risultati. Noi siamo la squadra che costruisce il programma nuovo. Tutti gli importi "
          "sono in franchi svizzeri, scritti <strong>CHF</strong>.",
}
SWITCH = {"en": "Italiano", "it": "English"}
SWITCH_LABEL = {"en": "Leggi in italiano", "it": "Read in English"}

CHAPTERS = [
    {"id": "promise",
     "title": {"en": "A promise for the future", "it": "Una promessa per il futuro"},
     "body": {
         "en": "<p>On {applied}, a customer aged {age} signed a contract with an insurance company. Such a contract "
               "is called a <strong>policy</strong>. The customer promised to pay {premium} every month for {years} "
               "years, from {begin} until {end}. Each of these monthly payments is called a <strong>premium</strong>."
               "</p><p>In return, the company promised two things. First, the company invests the money so that it "
               "can grow: this money is the customer's <strong>savings</strong>. Second, if the customer dies before "
               "{end}, the family receives money: this protection is called <strong>life cover</strong>. In this "
               "policy {cover}</p>"
               "<p>When the customer signed, the company showed what the savings could be worth at the end: "
               "<strong>{maturity}</strong>, if the investments grew by {growth} every year. That figure is a "
               "<strong>projection</strong>: an estimate, not a guarantee.</p>",
         "it": "<p>Il {applied} una persona di {age} anni ha firmato un contratto con una compagnia di assicurazioni. "
               "Un contratto così si chiama <strong>polizza</strong>. La persona assicurata si è impegnata a pagare "
               "{premium} al mese per {years} anni, dal {begin} al {end}. Ognuno di questi pagamenti mensili si chiama "
               "<strong>premio</strong>.</p>"
               "<p>In cambio la compagnia si è impegnata a due cose: primo, a investire i soldi perché possano "
               "crescere, e questi soldi sono i <strong>risparmi</strong> dell'assicurato; secondo, se la persona muore "
               "prima del {end}, a versare del denaro alla sua famiglia. Questa protezione si chiama <strong>copertura "
               "in caso di morte</strong>. In questa polizza {cover}</p>"
               "<p>Alla firma la compagnia ha mostrato quanto avrebbero potuto valere i risparmi alla fine: "
               "<strong>{maturity}</strong>, se gli investimenti fossero cresciuti del {growth} all'anno. Quella cifra "
               "è una <strong>proiezione</strong>: una stima, non una garanzia.</p>"}},
    {"id": "due",
     "title": {"en": "The day the money is due", "it": "Il giorno in cui si paga"},
     "body": {
         "en": "<p>Every month has a <strong>due date</strong>, the day the premium must be paid: here the {day} of "
               "the month. The customer pays by <strong>direct debit</strong>: they have allowed their bank to take "
               "the premium from their account automatically.</p>"
               "<p>Banks do this only on a <strong>bank working day</strong>. When the due date falls on a Saturday, a "
               "Sunday or a public holiday, the money is taken on the next working day. Which days are holidays "
               "depends on the region. This company follows the holidays of the canton of Ticino, where Good Friday "
               "is a normal working day, but days such as St Joseph (19 March) or Corpus Christi are holidays.</p>"
               "<p>Neuron has already planned the next payments. One of them: the premium due on <strong>{due}"
               "</strong>, {holiday}, will be taken on <strong>{collected}</strong>.</p>",
         "it": "<p>Ogni mese ha una <strong>scadenza</strong>, il giorno in cui il premio va pagato: qui il {day} del "
               "mese. Si paga con <strong>addebito diretto</strong>: la persona ha autorizzato la sua banca a prelevare "
               "il premio dal conto automaticamente.</p>"
               "<p>Le banche lo fanno solo in un <strong>giorno lavorativo bancario</strong>. Quando la scadenza cade "
               "di sabato, di domenica o in un giorno festivo, il premio viene addebitato il primo giorno lavorativo "
               "successivo. Quali giorni siano festivi dipende dalla regione. Questa compagnia segue i giorni festivi "
               "del Canton Ticino, dove il Venerdì Santo è un giorno lavorativo normale, mentre giorni come San "
               "Giuseppe (19 marzo) o il Corpus Domini sono festivi.</p>"
               "<p>Neuron ha già previsto i prossimi pagamenti. Uno di questi: il premio che scade il <strong>{due}"
               "</strong>, {holiday}, verrà addebitato il <strong>{collected}</strong>.</p>"}},
    {"id": "hundred",
     "title": {"en": "Where 100 francs go", "it": "Dove vanno 100 franchi"},
     "body": {
         "en": "<p>Take 100 francs of one premium. Before anything is invested, the company keeps an <strong>entry "
               "charge</strong>. For this customer it is {entry} out of every 100 francs{agreed}. The other "
               "<strong>{net}</strong> are invested.</p>"
               "<p>Neuron also works out the pay of the <strong>broker</strong>, the person who sold the policy. This "
               "pay is called a <strong>commission</strong>: here {commission} for every 100 francs the customer "
               "paid. The company pays it; it is not taken out of the customer's 100 francs. The company sorts its "
               "brokers into a few levels and pays each level a different amount per 100 francs: what counts is the "
               "level the broker had on the day the money arrived.</p>",
         "it": "<p>Prendiamo 100 franchi di un premio. Prima di investire, la compagnia trattiene un importo, la "
               "<strong>spesa d'entrata</strong>. Per questa polizza è di {entry} ogni 100 franchi{agreed}. Gli altri "
               "<strong>{net}</strong> vengono investiti.</p>"
               "<p>Neuron calcola anche il compenso dell'<strong>intermediario</strong>, la persona che ha venduto la "
               "polizza. Questo compenso si chiama <strong>provvigione</strong>: qui {commission} ogni 100 franchi "
               "pagati. La paga la compagnia; non viene tolta dai 100 franchi dell'assicurato. La compagnia divide i "
               "suoi intermediari in pochi livelli e paga a ogni livello un importo diverso per 100 franchi: conta il "
               "livello che l'intermediario aveva il giorno in cui sono arrivati i soldi.</p>"}},
    {"id": "units",
     "title": {"en": "Buying small pieces of a fund", "it": "Comprare piccole parti di un fondo"},
     "body": {
         "en": "<p>The invested money goes into {funds}. A <strong>fund</strong> is a big basket of investments, for "
               "example pieces of large companies, that many people own together. Owning part of a fund means owning "
               "<strong>units</strong>: small, equal parts of the basket. On every working day the fund publishes the "
               "<strong>price</strong> of one unit.</p>"
               "<p>The premium due on {premium_due} reached the company on {received}, {delay} later: a direct debit "
               "takes a few days. The money bought units on {traded}, the first day after its arrival on which the fund "
               "published a price. {bought}</p>"
               "<p>The value of the savings is the number of units multiplied by the price of the day. Prices go up "
               "and down, so the value moves even in a month without any payment.</p>"
               "<p>By the end of {last_year} the customer had paid in <strong>{paid}</strong>: {paid_count} premiums, "
               "because {unpaid_count} of the {due_count} premiums due were never paid{odd_amounts}. The "
               "savings were worth <strong>{value}</strong>. {why}</p>",
         "it": "<p>I soldi investiti vanno in {funds}. Un <strong>fondo</strong> è un grande paniere di investimenti, "
               "per esempio parti di grandi aziende, che molte persone possiedono insieme. Possedere una parte di un "
               "fondo vuol dire possedere delle <strong>quote</strong>: piccole parti uguali del paniere. Ogni "
               "giorno lavorativo il fondo pubblica il <strong>prezzo</strong> di una quota.</p>"
               "<p>Il premio che scadeva il {premium_due} è arrivato alla compagnia il {received}, {delay} dopo: un "
               "addebito diretto richiede qualche giorno. Con quei soldi sono state comprate quote il {traded}, il primo "
               "giorno dopo il loro arrivo in cui il fondo ha pubblicato un prezzo. {bought}</p>"
               "<p>Il valore dei risparmi è il numero di quote moltiplicato per il prezzo del giorno. I prezzi salgono "
               "e scendono, quindi il valore cambia anche in un mese senza pagamenti.</p>"
               "<p>Alla fine del {last_year} erano stati versati <strong>{paid}</strong>: {paid_count} premi, perché "
               "{unpaid_count} dei {due_count} premi dovuti non sono mai stati pagati{odd_amounts}. I risparmi "
               "valevano <strong>{value}</strong>. {why}</p>"}},
    {"id": "charges",
     "title": {"en": "A little goes out every month", "it": "Ogni mese se ne va un po'"},
     "body": {
         "en": "<p>Every month the company takes three charges. Neuron works them out and sells a few of the "
               "customer's units to pay them. In {month} they were:</p><ul>"
               "<li>an <strong>administration fee</strong>, the same every month: {admin};</li>"
               "<li>a <strong>management fee</strong> for looking after the funds, about {management_rate} of the "
               "value in a year: {management};</li>"
               "<li>the price of the life cover, the <strong>risk charge</strong>: {risk} that month. It depends on "
               "the age of the customer: in the whole of {risk_first_year} it came to {risk_first} in total, in the "
               "whole of {last_year}, at {age_now}, to {risk_last}.</li></ul>",
         "it": "<p>Ogni mese la compagnia addebita tre spese. Neuron le calcola e vende alcune quote dell'assicurato "
               "per pagarle. A {month} erano:</p><ul>"
               "<li>una <strong>spesa amministrativa</strong>, uguale ogni mese: {admin};</li>"
               "<li>una <strong>spesa di gestione</strong> per occuparsi dei fondi, circa il {management_rate} del "
               "valore in un anno: {management};</li>"
               "<li>il prezzo della copertura in caso di morte, il <strong>costo del rischio</strong>: {risk} in quel mese. "
               "Dipende dall'età della persona: in tutto il {risk_first_year} è stato in totale di {risk_first}, in "
               "tutto il {last_year}, a {age_now} anni, di {risk_last}.</li></ul>"}},
    {"id": "change",
     "title": {"en": "Two programs, one policy", "it": "Due programmi, una polizza"},
     "body": {
         "en": "<p>In fact there have been two Neurons, one program after the other. Until {change}, an older program did all "
               "the calculations; on that day a new one took over. This policy began on {begin}, so the "
               "{old_months} premiums paid before {change} were handled by the old program, and everything after them "
               "by the new one.</p>"
               "<p>The two programs calculate some things differently. The old one simply dropped any part of a cent: "
               "12.349 francs became 12.34. The new one rounds to the nearest cent: 12.349 becomes 12.35. The old one "
               "also worked out the management fee from the number of days in the month; the new one takes one "
               "twelfth of the yearly percentage. A cent here and there sounds like nothing, but the program that "
               "replaces Neuron must not get a single cent wrong, for every policy and every month, back to "
               "{first_year}, when the oldest policies began.</p>",
         "it": "<p>In realtà dietro Neuron ci sono stati due programmi, uno dopo l'altro. Fino al {change} un programma più vecchio "
               "faceva tutti i calcoli; quel giorno è subentrato uno nuovo. Questa polizza è iniziata il {begin}, "
               "quindi i {old_months} premi pagati prima del {change} sono stati calcolati dal programma vecchio, e "
               "tutto il resto da quello nuovo.</p>"
               "<p>I due programmi calcolano alcune cose in modo diverso. Il vecchio eliminava ogni frazione di "
               "centesimo: 12.349 franchi diventavano 12.34. Il nuovo arrotonda al centesimo più vicino: 12.349 diventa "
               "12.35. Il vecchio calcolava anche la spesa di gestione in base ai giorni del mese; il nuovo prende un "
               "dodicesimo della percentuale annua. Un centesimo qua e là sembra niente, ma il programma che sostituisce "
               "Neuron non deve sbagliare nemmeno un centesimo, per nessuna polizza e per nessun mese, risalendo fino al "
               "{first_year}, quando sono iniziate le polizze più vecchie.</p>"}},
    {"id": "letter",
     "title": {"en": "The yearly letter, and stopping early", "it": "La lettera annuale e l'uscita anticipata"},
     "body": {
         "en": "<p>Every year the customer receives an <strong>annual statement</strong>, a letter that adds up the "
               "year. For {year}: <strong>{premiums}</strong> paid in ({year_paid} of the {year_due} premiums due), and "
               "{total} taken in charges: {entry} entry charge, {admin} administration, {management} management and {risk} for "
               "the life cover.{entry_cents}</p>"
               "<p>The customer may also stop early and take the money out. The amount they would get is the "
               "<strong>surrender value</strong>: the value of the savings minus a <strong>penalty</strong>, which gets "
               "smaller with every year of the contract. On {surrender_date} the savings were worth {surrender_worth}; "
               "{surrender_text}</p>",
         "it": "<p>Ogni anno l'assicurato riceve un <strong>estratto annuale</strong>, una lettera che riassume "
               "l'anno. Per il {year}: <strong>{premiums}</strong> versati ({year_paid} dei {year_due} premi dovuti), e {total} "
               "di spese: {entry} di spesa d'entrata, {admin} di amministrazione, {management} di gestione e "
               "{risk} per la copertura in caso di morte.{entry_cents}</p>"
               "<p>Si può anche disdire il contratto in anticipo e ritirare i soldi. Quello che si riceve è il "
               "<strong>valore di riscatto</strong>: il valore dei risparmi meno una <strong>penale</strong>, che "
               "diminuisce di anno in anno. Il {surrender_date} i risparmi valevano "
               "{surrender_worth}; {surrender_text}</p>"}},
    {"id": "rules",
     "title": {"en": "How the rules were found", "it": "Come sono state trovate le regole"},
     "body": {
         "en": "<p>Nobody ever wrote down all of Neuron's rules. What we had were Neuron's <strong>results</strong> "
               "for {policies} policies, {rows} numbers in all, and the information they were worked out from. So we "
               "worked like detectives. We wrote down a first guess for each calculation, asked a computer to compare "
               "it with Neuron's results, and looked only at the cases where the guess was wrong. When all the wrong "
               "cases have something in common (they all belong to policies that began before August 2007, or the "
               "due date falls on a holiday) that common thing is a new rule.</p>"
               "<p>To be sure that a rule is real, we take it away and count how many of Neuron's numbers we "
               "then get wrong. A real rule is needed for exactly the numbers it explains, and for no other:</p>"
               "<ul>{examples}</ul>"
               "<p>Today the rules give exactly the same result as Neuron, to the cent and to the day, for "
               "<strong>{exact}</strong> of its {rows} results.</p>",
         "it": "<p>Nessuno ha mai scritto tutte le regole di Neuron. Avevamo i <strong>risultati</strong> di Neuron per "
               "{policies} polizze, {rows} numeri in tutto, e le informazioni da cui erano stati calcolati. Così "
               "abbiamo lavorato come detective. Abbiamo scritto una prima ipotesi per ogni calcolo, abbiamo chiesto a "
               "un computer di confrontarla con i risultati di Neuron e abbiamo guardato solo i casi in cui l'ipotesi "
               "era sbagliata. Quando tutti i casi sbagliati hanno qualcosa in comune (riguardano tutti polizze "
               "iniziate prima dell'agosto 2007, o la scadenza cade in un giorno festivo) quella cosa in comune è una "
               "nuova regola.</p>"
               "<p>Per essere sicuri che una regola sia giusta, la togliamo e contiamo quanti numeri di Neuron "
               "diventano sbagliati. Una regola giusta serve esattamente per i numeri che spiega, e per nessun altro:</p>"
               "<ul>{examples}</ul>"
               "<p>Oggi le regole danno esattamente lo stesso risultato di Neuron, al centesimo e al giorno, per "
               "<strong>{exact}</strong> dei suoi {rows} risultati.</p>"}},
    {"id": "corrections",
     "title": {"en": "Numbers changed by hand", "it": "Numeri cambiati a mano"},
     "body": {
         "en": "<p>For the other {wrong} results no rule gives Neuron's number. Look at how they differ: mostly not by "
               "a cent, but by whole francs. An example from another customer's policy, number {example_policy}: "
               "Neuron says the commission of one premium was {example_neuron}, the rules say {example_rules}, exactly "
               "{example_gap} apart.</p>"
               "<p>Over the years, people changed some numbers by hand, directly in Neuron. We do not know why; there "
               "may be a good reason, such as a special arrangement with a customer. No rule can guess such a change, "
               "so the new program does not try to: it lists these numbers, and a person checks each one.</p>",
         "it": "<p>Per gli altri {wrong} risultati nessuna regola dà il numero di Neuron. Guardate come differiscono: "
               "quasi sempre non di un centesimo, ma di franchi interi. Un esempio dalla polizza di un altro cliente, "
               "numero {example_policy}: secondo Neuron la provvigione di un premio era di {example_neuron}, secondo le "
               "regole di {example_rules}: esattamente {example_gap} di differenza.</p>"
               "<p>Negli anni qualcuno ha cambiato alcuni numeri a mano, direttamente in Neuron. Non sappiamo perché; "
               "può esserci un buon motivo, per esempio un accordo particolare con un cliente. Nessuna regola può "
               "indovinare un cambiamento così, quindi il programma nuovo non ci prova: elenca questi numeri, e una "
               "persona li controlla uno per uno.</p>"}},
]

COVER = {  # RK_TARKEY[6]: what the family receives
    "A": {"en": "the family would receive the value of the savings plus 1%.",
          "it": "la famiglia riceverebbe il valore dei risparmi più l'1%."},
    "B": {"en": "the family would receive the value of the savings, and at least {sum_insured}.",
          "it": "la famiglia riceverebbe il valore dei risparmi, e almeno {sum_insured}."},
    "C": {"en": "the family would receive the value of the savings plus {sum_insured}.",
          "it": "la famiglia riceverebbe il valore dei risparmi più {sum_insured}."},
}
AGREED = {"en": ", less than usual thanks to a special agreement", "it": ", meno del solito grazie a un accordo particolare"}
FUNDS = {"en": ["one fund", "{n} funds"], "it": ["un fondo", "{n} fondi"]}
BOUGHT = {
    "en": "For each 100 francs, the {net} invested bought <strong>{units} units</strong> at {price} each.",
    "it": "Per ogni 100 franchi, i {net} investiti hanno comprato <strong>{units} quote</strong> a {price} l'una.",
}
BOUGHT_SPLIT = {
    "en": "The {net} invested out of every 100 francs were split between the funds the customer had chosen, "
          "{shares}: {split}. In the first fund, these {share} bought <strong>{units} units</strong> at {price} each.",
    "it": "I {net} investiti per ogni 100 franchi sono stati divisi tra i fondi scelti dall'assicurato, {shares}: "
          "{split}. Nel primo fondo, questi {share} hanno comprato <strong>{units} quote</strong> a {price} l'una.",
}
SPLIT_AND = {"en": " and ", "it": " e "}
DIRECTION = {"en": ["less", "more"], "it": ["inferiore", "superiore"]}
DAYS = {"en": ["one day", "{n} days"], "it": ["un giorno", "{n} giorni"]}
ODD_AMOUNTS = {"en": ", and {n} payments were a little different from {premium}",
               "it": ", e {n} pagamenti erano un po' diversi da {premium}"}
WHY = {
    "loss": {"en": "That is less than what was paid in, for two reasons. Over the years the charges took {charges} "
                   "(chapters 3 and 5). And the funds lost {market}: overall, their prices ended lower than when the "
                   "units were bought. The projection shown at the signature had expected {projected} by then.",
             "it": "È meno di quanto versato, per due motivi. Negli anni le spese sono costate in tutto {charges} "
                   "(capitoli 3 e 5). E i fondi hanno perso {market}: nel complesso i loro prezzi sono finiti più in basso di quando "
                   "le quote erano state comprate. La proiezione mostrata alla firma prevedeva {projected} per quel "
                   "momento."},
    "gain": {"en": "Over the years the charges took {charges} (chapters 3 and 5), and the funds gained {market}: "
                   "overall, their prices ended higher than when the units were bought. The projection shown at the "
                   "signature had expected {projected} by then.",
             "it": "Negli anni le spese sono costate in tutto {charges} (capitoli 3 e 5), e i fondi hanno guadagnato {market}: "
                   "nel complesso i loro prezzi sono finiti più in alto di quando le quote erano state comprate. La "
                   "proiezione mostrata alla firma prevedeva {projected} per quel momento."},
}
ENTRY_CENTS = {
    "en": " The entry charge is {gap} {direction} than {rate} of {premiums}: for every premium, the part for each "
          "fund is rounded to the cent, and these small differences add up to {gap}.",
    "it": " La spesa d'entrata è di {gap} {direction} al {rate} di {premiums}: per ogni premio la parte destinata "
          "a ciascun fondo è arrotondata al centesimo, e sommate queste piccole differenze fanno {gap}.",
}
SURRENDER = {
    "penalty": {"en": "after a penalty of {penalty}, the customer would have received <strong>{surrender}</strong>.",
                "it": "dopo una penale di {penalty}, l'assicurato avrebbe ricevuto <strong>{surrender}</strong>."},
    "none": {"en": "after so many years there was no penalty any more, so the customer would have received all of it: "
                   "<strong>{surrender}</strong>.",
             "it": "dopo tanti anni non c'era più nessuna penale, quindi l'assicurato avrebbe ricevuto tutto: "
                   "<strong>{surrender}</strong>."},
}
RULE_EXAMPLES = {  # (task, rule card) of `lab ablate` -> what goes wrong without the rule, for a lay reader
    ("t0_commission", "tier-on-money-date"): {
        "en": "<strong>{n}</strong> of {of} commissions come out wrong if we use the level the broker has today "
              "instead of the level on the day the money arrived.",
        "it": "<strong>{n}</strong> provvigioni su {of} diventano sbagliate se usiamo il livello che l'intermediario "
              "ha oggi invece di quello del giorno in cui sono arrivati i soldi."},
    ("t1_next_due_dates", "good-friday"): {
        "en": "<strong>{n}</strong> of {of} days on which a premium is taken come out wrong if Good Friday is treated "
              "as a holiday.",
        "it": "<strong>{n}</strong> giorni di addebito su {of} diventano sbagliati se il Venerdì Santo è considerato "
              "festivo."},
    ("t2_projected_maturity_value", "nearest-birthday"): {
        "en": "<strong>{n}</strong> of {of} projections come out wrong if the age is counted from the last birthday "
              "instead of the nearest one: someone who is 40 and a half counts as 41, not 40.",
        "it": "<strong>{n}</strong> proiezioni su {of} diventano sbagliate se l'età è contata dall'ultimo compleanno "
              "invece che da quello più vicino: chi ha 40 anni e mezzo conta come 41, non 40."},
    ("t4_annual_statement", "system-change"): {
        "en": "<strong>{n}</strong> of {of} annual statements come out wrong if we forget that the old program "
              "calculated differently before August 2007.",
        "it": "<strong>{n}</strong> estratti annuali su {of} diventano sbagliati se dimentichiamo che prima "
              "dell'agosto 2007 il programma vecchio calcolava in un altro modo."},
}

FIGURES = {
    "hundred_entry": {"en": "entry charge", "it": "spesa d'entrata"},
    "hundred_net": {"en": "invested", "it": "investiti"},
    "week_due": {"en": "due", "it": "scade"},
    "week_paid": {"en": "taken", "it": "addebito"},
    "week_off": {"en": "closed", "it": "chiuso"},
    "week_caption": {"en": "{months}. In grey, the days the banks are closed.",
                     "it": "{months}. In grigio i giorni in cui le banche sono chiuse."},
    "weekdays": {"en": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
                 "it": ["lun", "mar", "mer", "gio", "ven", "sab", "dom"]},
    "value": {"en": "value of the savings", "it": "valore dei risparmi"},
    "paid": {"en": "paid in so far", "it": "versato finora"},
    "charges_admin": {"en": "administration", "it": "amministrazione"},
    "charges_management": {"en": "management", "it": "gestione"},
    "charges_risk": {"en": "life cover", "it": "copertura in caso di morte"},
    "letter_paid": {"en": "paid in", "it": "versato"},
    "letter_entry": {"en": "entry charge", "it": "spesa d'entrata"},
    "letter_left": {"en": "paid in minus charges", "it": "versato meno spese"},
    "chart_value": {"en": "Value of the savings each month, and what was paid in so far",
                    "it": "Valore dei risparmi ogni mese, e quanto era stato versato fino ad allora"},
    "chart_letter": {"en": "The annual statement of {year}", "it": "L'estratto annuale del {year}"},
    "glossary": {"en": "Words used in this story", "it": "Le parole di questa storia"},
    "chapter": {"en": "Chapter", "it": "Capitolo"},
    "data": {"en": "The numbers of the chart", "it": "I numeri del grafico"},
}

HOLIDAYS = {  # (month, day) or days after Easter -> the name of a bank holiday of Ticino
    (1, 1): {"en": "New Year's Day", "it": "Capodanno"},
    (1, 6): {"en": "Epiphany", "it": "l'Epifania"},
    (3, 19): {"en": "St Joseph's Day", "it": "San Giuseppe"},
    (5, 1): {"en": "Labour Day", "it": "la Festa del lavoro"},
    (6, 29): {"en": "the feast of St Peter and Paul", "it": "San Pietro e Paolo"},
    (8, 1): {"en": "the Swiss National Day", "it": "la Festa nazionale"},
    (8, 15): {"en": "the Assumption", "it": "l'Assunzione"},
    (11, 1): {"en": "All Saints' Day", "it": "Ognissanti"},
    (12, 8): {"en": "the Immaculate Conception", "it": "l'Immacolata"},
    (12, 25): {"en": "Christmas Day", "it": "Natale"},
    (12, 26): {"en": "St Stephen's Day", "it": "Santo Stefano"},
    1: {"en": "Easter Monday", "it": "il Lunedì dell'Angelo"},
    39: {"en": "Ascension Day", "it": "l'Ascensione"},
    50: {"en": "Whit Monday", "it": "il Lunedì di Pentecoste"},
    60: {"en": "Corpus Christi", "it": "il Corpus Domini"},
}
A_HOLIDAY = {"en": "a public holiday ({name})", "it": "un giorno festivo ({name})"}

GLOSSARY = [  # term -> explanation; every term in bold in the chapters is here
    ({"en": "Neuron", "it": "Neuron"},
     {"en": "the computer program of the insurance company, which is being replaced.",
      "it": "il programma per computer della compagnia di assicurazioni, che viene sostituito."}),
    ({"en": "CHF", "it": "CHF"},
     {"en": "Swiss francs.", "it": "franchi svizzeri."}),
    ({"en": "policy", "it": "polizza"},
     {"en": "the contract between the customer and the insurance company.",
      "it": "il contratto tra l'assicurato e la compagnia di assicurazioni."}),
    ({"en": "premium", "it": "premio"},
     {"en": "the amount the customer pays, here every month.", "it": "la somma che l'assicurato paga, qui ogni mese."}),
    ({"en": "savings", "it": "risparmi"},
     {"en": "the money of the premiums that the company invests for the customer.",
      "it": "i soldi dei premi che la compagnia investe per l'assicurato."}),
    ({"en": "life cover", "it": "copertura in caso di morte"},
     {"en": "the money the family receives if the customer dies before the end of the contract.",
      "it": "i soldi che riceve la famiglia se l'assicurato muore prima della fine del contratto."}),
    ({"en": "projection", "it": "proiezione"},
     {"en": "an estimate of what the savings could be worth later, not a guarantee.",
      "it": "una stima di quanto i risparmi potrebbero valere più avanti, non una garanzia."}),
    ({"en": "due date", "it": "scadenza"},
     {"en": "the day a premium must be paid.", "it": "il giorno in cui un premio va pagato."}),
    ({"en": "direct debit", "it": "addebito diretto"},
     {"en": "the customer has allowed the bank to take each premium from their account automatically.",
      "it": "l'assicurato ha autorizzato la banca a prelevare ogni premio dal suo conto automaticamente."}),
    ({"en": "bank working day", "it": "giorno lavorativo bancario"},
     {"en": "a day on which banks move money: not a Saturday, a Sunday or a public holiday.",
      "it": "un giorno in cui le banche muovono denaro: non un sabato, una domenica o un giorno festivo."}),
    ({"en": "entry charge", "it": "spesa d'entrata"},
     {"en": "the part of each premium that the company keeps before investing the rest.",
      "it": "la parte di ogni premio che la compagnia trattiene prima di investire il resto."}),
    ({"en": "broker", "it": "intermediario"},
     {"en": "the person who sold the policy to the customer.", "it": "la persona che ha venduto la polizza."}),
    ({"en": "commission", "it": "provvigione"},
     {"en": "what the company pays the broker for a premium.",
      "it": "quanto la compagnia paga all'intermediario per un premio."}),
    ({"en": "fund", "it": "fondo"},
     {"en": "a big basket of investments that many people own together.",
      "it": "un grande paniere di investimenti che molte persone possiedono insieme."}),
    ({"en": "units", "it": "quote"},
     {"en": "small, equal parts of a fund.", "it": "piccole parti uguali di un fondo."}),
    ({"en": "price", "it": "prezzo"},
     {"en": "what one unit of a fund costs on a given day.", "it": "quanto costa una quota di un fondo in un certo giorno."}),
    ({"en": "administration fee", "it": "spesa amministrativa"},
     {"en": "a fixed monthly charge for keeping the contract.", "it": "una spesa mensile fissa per gestire il contratto."}),
    ({"en": "management fee", "it": "spesa di gestione"},
     {"en": "a monthly charge for looking after the funds, a small share of the value.",
      "it": "una spesa mensile per occuparsi dei fondi, una piccola parte del valore."}),
    ({"en": "risk charge", "it": "costo del rischio"},
     {"en": "the monthly price of the life cover.", "it": "il prezzo mensile della copertura in caso di morte."}),
    ({"en": "annual statement", "it": "estratto annuale"},
     {"en": "the yearly letter that adds up what was paid in and what was charged.",
      "it": "la lettera annuale che riassume quanto è stato versato e quanto è stato prelevato."}),
    ({"en": "surrender value", "it": "valore di riscatto"},
     {"en": "what the customer gets if they stop the contract early.",
      "it": "quanto riceve l'assicurato se disdice il contratto in anticipo."}),
    ({"en": "penalty", "it": "penale"},
     {"en": "the part kept by the company when a contract is stopped early.",
      "it": "la parte che la compagnia trattiene quando un contratto viene disdetto in anticipo."}),
    ({"en": "results", "it": "risultati"},
     {"en": "the numbers Neuron worked out: commissions, days on which premiums are taken, projections, surrender values and annual "
            "statements.",
      "it": "i numeri calcolati da Neuron: provvigioni, giorni di addebito, proiezioni, valori di riscatto ed estratti "
            "annuali."}),
]

MONTHS = {
    "en": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
           "November", "December"],
    "it": ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre", "ottobre",
           "novembre", "dicembre"],
}
ORDINAL = {"en": lambda n: f"{n}{'th' if 11 <= n % 100 <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}",
           "it": lambda n: "primo" if n == 1 else str(n)}
