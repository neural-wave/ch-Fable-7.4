# Neuron migration: rules as code

`submission.py` computes everything from the export in `legacy_dir` and nothing else. It does not read any
target file and has no values written into it. The rules were found in the data with the tools in `tools/`, handed
in too.

| | |
|---|---|
| t0 commission | 225'848 / 225'858 train rows exact (99.9956 %). The 10 other rows are manual corrections, proven below |
| t1 next due dates | 15'028 / 15'028 train rows exact (100 %); backtest on 18 past years: no wrong due date |
| t2 projected maturity value | 3'011 / 3'019 train rows exact (99.735 %), and all 79'040 yearly values of the diagnostic. The 8 other rows are manual corrections |
| t3 surrender value | 6'137 / 6'153 train rows exact (99.74 %), and every link of the diagnostics: all 5'024'847 calculated bookings (amount and units), all 23'052 holdings, all 6'153 policy values. The 16 other rows are manual corrections |
| t4 annual statement | 34'125 / 34'145 train rows exact (99.94 %): every column of every row, except 20 admin fees. Those 20 are manual corrections |
| t5 outlier detection | 54 outliers on the train targets: exactly the 54 rows that t0 – t4 miss, among them all 38 corrections that NREXCP lists for train policies. Without them every task scores 100 % (`scoring.accuracy` with `excluded`) |
| t7 tax audit | No targets. Both PDF examples exact on the real tables (BL10000086 #121 and BL10000044 2019, 616.11), also with the official `scoring_t7.py`. The labels of NRTAXB (which tax was booked) agree with the taxable base on 277 / 285 German and 384 / 393 Italian payouts (`t7lab/t7_labels.py`, next to the hand-in). Before every upload `t7lab/t7_check.py` runs both examples and the labels of NRTAXB on the real tables, with an open-weights model |
| Maintainability index | 100 for the whole folder (radon, weighted by lines) and for every file in it. The t7 lab, which keeps the operators of plain Python, is next to the folder (`../t7lab/`), not in the hand-in |

```
python check.py   # from starter_kit/: all tasks and the maintainability index
```

## Layout

```
my_solution/
├── submission.py      entry point: thin task functions that compose the modules below
├── conventions.py     the conventions of Neuron as data (states, frequencies, conversion, tariff key, ...)
├── legacy.py          reading the export by the types of NRDICT, the version valid on a date
├── dates.py           calendar: schedules of whole months, business days of canton Ticino, policy years
├── money.py           exact money arithmetic: cents x millionths, units x prices, splits over positions
├── market.py          unit prices and exchange rates as known on a date
├── tariff.py          the policy as signed and its parameters valid on the application date
├── charges.py         the charges: entry charge, risk charge, death benefit, ages and mortality
├── projection.py      t2: the offer month by month, its steps in Neuron's order
├── bookings.py        t3: the counted bookings, the premiums bought in units, the units moved by events
├── charge_run.py      t3: the monthly charge runs (admin fee, management and risk charge) one after another
├── valuation.py       t3: holdings, policy value and surrender value on a date
├── statement.py       t4: premiums and charges of the unit account per calendar year
├── outliers.py        t5: the target files as tables, and the values that differ from their rule
├── taxpayer.py        t7: residence of the holder and tax rates as Neuron knew them at a booking, tax currency
├── payouts.py         t7: the payouts, the premiums they use one after another, the taxable base by country
├── bollo.py           t7: the Italian Bollo, accrued every year, re-priced in 2019, collected at the payouts
├── taxes.py           t7: the amount of every tax booking of NRTAXB, the payout and annual tables
├── requirements.txt   polars 2.0.0 and holidays 0.106, pinned: the versions tested (128-bit integers need polars 1.31+)
└── tools/neuron/      the tools that found the rules (not used by the submission)
    ├── load.py, codes.py, policy.py   tables decoded for exploring, code texts, history of one policy
    ├── targets.py                     train targets and official scoring, for exploring only
    ├── schema/                        keys and relations found with Desbordante, and their diagram
    ├── solver/                        Z3 with SMT-LIB constraints: proofs (UNSAT), intervals, rate recovery (MaxSMT)
    ├── backtest.py                    t1 on past extract dates against the real due dates PR_DUEDT
    ├── bisection.py                   the first step where a calculation leaves a diagnostic target (t2)
    └── account_check.py               the unit account link by link against the diagnostics (t3, t4)
```

Next to the folder, `../t7lab/` holds the tools that read the real tax tables for t7 (`t7_check`, `t7_labels`,
`t7_variants`); they run from here with `PYTHONPATH="$PWD:$PWD/tools:$PWD/.."`.

## Approach

1. **Formats from the data dictionary.** Every column is converted by its NRDICT type. Amounts stay integers in
   cents and rates integers in millionths, so the arithmetic is exact. `CYYMMDD` dates stay integers too, since
   they sort like dates (`970630` < `1070326` < `9999999`, the open end).
2. **Relations found by a tool, not by hand.** Desbordante finds the candidate keys (HyUCC) and the inclusion
   dependencies between all tables (Faida exact, also over two columns; Spider approximate). Every IND is
   checked exactly; it counts as a relation when it can be a foreign key (`schema/relations.py`).
3. **Rules checked against the targets.** A candidate rule is scored with the official scoring. Every row it
   misses is examined.
4. **Proofs with Z3.** MaxSMT recovers a parameter from the targets alone. An UNSAT answer proves that no rule of
   a whole space (bases x rates x rounding modes) gives a target value, so the value was corrected by hand.
5. **Search over conventions, then bisection.** For t2 a grid of conventions (monthly rate, order of the steps,
   rounding, age, management charge: 768 combinations) was scored on the first policy year; the diagnostic of the
   yearly values then shows the first year in which a policy leaves the target (`bisection.py`), and the
   policies that share it point at the missing condition.
6. **One link at a time.** t3 is a chain: calculated bookings, holdings, policy value, surrender value. Each link
   was matched with its diagnostic (`t3_booking`, `t3_holding`, `policy_value`) before the next one was built
   (`account_check.py`), so every miss pointed at one rule.

## Rules found

**t0 commission.** One commission per premium item whose money was received:

- received: money date `PR_RCVDT` > 0, and the receipt event `PR_EVTNR` not reversed by an event 900
  (`EV_REVNR`);
- rate from NRCOMR, by the broker tier and the premium type, valid on the money date `PR_RCVDT`;
- broker tier: `NRBROK.BR_TIER` of the broker `PH_BRKNR` of the policy version valid on `PR_RCVDT`. If several
  versions are valid, the highest `PH_VRSNR` wins, so a broker change counts from its validity date even when it
  was entered later;
- premium type: `E` for single premium policies (`PH_FREQ` = E), `L` for regular premiums;
- commission = `PR_AMTRC` x rate, rounded half up to the cent.

Z3 recovers the six rates from the targets alone, and they equal NRCOMR: A/L 4 %, A/E 1.5 %, B/L 3 %, B/E 1 %,
C/L 2 %, C/E 0.5 %. Each interval of feasible rates closes on a single value.

**t1 next due dates.** For every policy that pays regular premiums on the extract date, the due dates of the
following year with their collection dates:

- policies: state 10 and frequency other than `E` in the policy version **valid on the extract date** (not the
  version marked current: BL10001854 has a current version that ended in 2021);
- schedule: COBOL computed every due date from the previous one, so a day 29 to 31 sank in a short month and
  stayed there (31 -> 28 -> 28). Since the conversion to Neuron NG on 11.8.2007 the schedule is its first due date
  plus whole periods of the frequency (M 1, Q 3, H 6, J 12 months), so a day 31 comes back after a short month.
  The anchor is the first past due date `PR_DUEDT` on or after the conversion. No due date on or after maturity;
- collection: direct debit (`LS`) on the due date if it is a business day, else on the next one; bank transfer
  (`UB`) on the due date. Business days are the weekdays without a public holiday of canton Ticino (library
  `holidays`, `CH`/`TI`): Good Friday is a business day there, 26.3.2027 is collected on the day.

The target window has dues on all 365 days; the moved weekdays are exactly the Ticino holidays. The export keeps
no past collection dates (`PR_RCVDT` is when the money arrived), but it keeps the past due dates: computing t1
for 30 June of every year from 2008 to 2025 reproduces the real due dates of 28'366 of 28'386 unchanged policies.
In the other 20 the real list is the start of the predicted one: the policy stopped paying without a new version.

**t2 projected maturity value.** The offer simulates the policy month by month from the start date to the
maturity date, as one amount (no fund prices, currencies or individual agreements):

- the policy as signed: its first version (`PH_VRSNR` 1), later changes do not count; the insured person of the
  main risk;
- the parameters valid on the application date `PH_APPDT`: charges NRCHRG by tariff family and generation (from
  the tariff key `RK_TARKEY`), entry charge NRENTC by broker tier, growth rate NRILLU;
- every month, in this order: the premium due (every 1, 3, 6 or 12 months from the start; a single premium once)
  less the entry charge; the admin fee `CG_ADMFEE`; the management charge at the pot 2 rate `CG_AMCP2` / 12 (one
  amount has no initial units); the risk charge; the growth at `IL_RATE` / 12 (not the compound monthly rate);
- risk charge = sum at risk x qx x smoker factor (`CG_SMKFAC` if `PS_SMOKE` = J) x (1 + `RK_LOAD`) / 12. The sum
  at risk is the death benefit less the value: option A 101 % of the value, B the higher of sum insured and value,
  C value plus sum insured. qx comes from the table `CG_MORTTB`, for the sex of the tariff key (U: the sex of the
  person) and the entry age plus the policy year;
- COBOL made the offers signed before the conversion (11.8.2007), Neuron NG the later ones. Neuron NG rounds the
  charges and the growth half up to the cent, and its entry age is the completed months since birth / 12, rounded
  half up. COBOL truncates them, and its entry age is the days since birth / 365, rounded half up: with the leap
  days its age goes up a little earlier. With the Java rules the first policy year matched 0 to 11 % of the offers
  per month of application up to July 2007, 80 % in August 2007 and nearly all after it;
- the growth multiplies by 1 + rate / 12 in decimal arithmetic of 28 significant digits. For 4 % the factor
  1.00333...3 is a bit less than 1 + 1/300, so a value that would end on exactly half a cent (or a whole cent, for
  COBOL) may end just below it; the 28 digits round it back only when the error is small enough. The exact
  fraction misses a cent in 22 % of the policies, an 18-digit rate in 7 %, the 28 digits in none;
- birth dates that do not exist (31 November, 8 policies) run on into the next month, like a lenient calendar.
  Taking the last day of the month gives the same values for all 8, so the train data cannot tell them apart.

**t3 surrender value.** NRBOOK has a row for every booking with its fund, pot and dates. Switches, withdrawals,
surrenders and death claims carry their units; the premiums (`PRM`) and the charges (`ADM`, `AMC`, `RSK`) are
blank, since the nightly job that calculated them is not in the extract. The submission recalculates them:

- counted: the bookings of events not reversed by an event 900 and not entered as a manual correction (event
  990, online, at the timestamps of NREXCP);
- prices: the bid or ask price of the last price date of the fund on or before the trade date (that is always
  `BK_PRCDT`), and of that day the last publication `FP_CHGTS`. Exchange rates `NRFXRT` in francs per unit, the
  lower case currencies included; units = amount x rate of the policy currency / rate of the fund currency /
  price, rounded to the millionth;
- premium (event 110): one booking per fund of the allocation. Amount = `PR_AMTRC` x (1 - entry charge rate) x
  `AL_PCTG`, rounded once; the entry charge is an individual agreement (`NRAGRE` ENT) or the rate of the broker
  tier of the policy version, the allocation and both rates valid on the money date `BK_RCVDT`. Units at the ask
  price, with the exchange rates of the day **before** the trade date;
- charge run (event 300, at 01:30): it values every position with the units traded **before** its trade date, at
  the bid price and the exchange rates of the day, rounded to the cent position by position. Then:
  - ADM: `CG_ADMFEE` valid on the trade date (not the application date), at most the value; split over the
    positions by value, the cents of the rounding to the largest position (the first fund and pot on a tie).
    Positions too small for a cent of fee count in the split too;
  - AMC per position: the rate of its pot (`CG_AMCP1` initial, `CG_AMCP2` base) or of an agreement (`NRAGRE`
    AMC), on its value. Neuron NG takes a twelfth; COBOL took the days of the month (from the previous monthly
    date of the start date) / 360;
  - RSK: the risk charge of t2 on the value left after ADM and AMC, at most that value, split by that value.
    The age is the entry age as the system that issued the policy counted it (COBOL days / 365 before the
    conversion, months / 12 after) plus the policy years completed on the trade date. A start on 29 February
    has its anniversary on 28 February;
- Neuron NG rounds half up, COBOL truncated, by the trade date of the booking. The runs of a policy depend on each
  other through the units, so they run one after another: the first run of every policy at once, then the
  second, and so on (6 seconds for 533'660 runs);
- policy value on a valuation date: the units traded on or before it, at the bid price of the last price date
  and the exchange rates of the day, rounded position by position;
- surrender value = policy value x (1 - penalty), rounded once, never below 0. The penalty `NRSURR` comes from
  the scale of the product for the policy years completed on the valuation date; there is none after the last
  year of the scale and in the waiver periods `NRWAIV`. BL10001005 shows the floor: its value no longer covered
  the run of October 2021, the admin fee took all of it and the management charge 2 cents more, so its policy
  value at the end of 2025 is -0.03 and its surrender value 0.

**t4 annual statement.** Per policy and calendar year, from the same unit account as t3:

- premiums: the received premiums `PR_AMTRC` not reversed (as in t0), in the year of the money date `PR_RCVDT`;
- entry charges: per premium booking, the fund's share of the premium (`PR_AMTRC` x `AL_PCTG`) less the amount
  invested in it, in the year of the booking's trade date. The funds of one premium can trade on different days:
  BL10000851 received 715.00 on 29.12.2018, its CHF fund N0001 traded on 31.12.2018 and N0016 on 2.1.2019, so
  21.45 of its entry charge is in 2018 and 14.30 in 2019. Taking the whole premium on one date misses 36 rows;
- admin fees, management fees, risk charges: the `ADM`, `AMC` and `RSK` bookings, in the year of their trade
  date; total charges = entry charges + the three charges;
- a statement for every year from the year of the start date on, with zeros in the years without bookings
  (extra years after the end of a policy are not scored).

**t5 outlier detection.** The rules reproduce every value that Neuron calculated, so a target value that differs
from its rule was set by hand. Every task with amounts builds a table in the format of its target file, amounts in
cents (`commissions`, `maturity_values`, `surrender_table`, `statement_table`); t5 reads the target files the
same way (amounts as text, converted exactly) and returns the keys whose amounts differ (`outliers.py`). The
surrender values are calculated for the valuation dates of the target file. t1 has no corrections: its values are
the dates of the schedule, and NREXCP has none for it. On the train targets t5 returns 54 keys: the misses of
t0 – t4, one by one, and among them all 38 entries of NREXCP for train policies. The other 16 are listed below.

**Manual corrections (input for t5).** The 10 rows of t0 that the rule misses are UNSAT for every base
(`PR_AMTDU`, `PR_AMTRC`), every NRCOMR rate and every rounding mode. Each differs from the rule by whole francs.
Six of them are listed in NREXCP. Four are not: BL10001299 #103, BL10001328 #1, BL10002438 #11, BL10004554 #35.

The 8 maturity values of t2 that the rule misses have a projection that is right in every year; only the final
value differs, by whole francs with the cents of the projection (`bisection.corrected_maturities`). Five are
listed in NREXCP (BL10000128, BL10001762, BL10003323, BL10003583, BL10003808). Three are not: BL10002196
(+1'726.00), BL10002973 (+1'498.00), BL10004278 (+3'294.00).

The 16 surrender values of t3 that the rule misses have the right policy value and holdings; only the surrender
value is higher, by whole francs (`account_check.surrender_mismatches`). Eleven are listed in NREXCP. Five are
not: BL10000321 2025 (+175.00), BL10000768 2020 (+117.00), BL10001080 2020 (+158.00), BL10002328 2020 (+499.00),
BL10004896 2025 (+474.00).

The 20 statements of t4 that the rule misses differ in `admin_fees` alone (so also in `total_charges`), by whole
francs from 7.00 to 147.00; the other four amounts are exact (`account_check.statement_mismatches`). Sixteen are
listed in NREXCP, each with an event 990 at the same timestamp and no amount. Four are not: BL10003910 2024
(+21.00), BL10004031 2013 (+96.00), BL10004844 2018 (+46.00), BL10004909 2017 (+53.00). The export has no
trace of the corrected amounts, so no rule can reproduce them.

**t7 tax audit.** NRTAXB names every tax booking of Neuron (type, event, effective date, processing timestamp,
job user); only the amounts are missing. So the rules do not decide again whether a tax was due: they calculate
the amount of every booking (`taxes.py`) and add them up per payout and per policy and year.

- country: the country of the taxes withheld from the payout (VST, SOS, KST), a label of NRTAXB; without them
  the residence: the holder (NRHOLD) and the address (NRADDR) valid on the effective date, among the versions
  entered up to the processing timestamp (`legacy.valid_on` with `known_at`). The rates NRTAXR are looked up the
  same way, for the country of their tax type (`TX_CNTRY`), so the Bollo batches of 2017 – 2019 used rate
  version 1 and the fix of July 2019 version 2;
- payouts: the events 400, 410 and 500 with a tax booking or not reversed. Units sold = the WDR, SUR, DTH
  bookings; gross = the units sold less the surrender penalty of the day for a withdrawal or a surrender
  (`PENALIZED`, rounded as in t3), so NRTAXB books no tax where the penalty takes the gain or the gross to the
  limit or below; value before = units sold + the value left that day (`valuation.values_on`);
- premiums used: every premium received (not reversed) up to the payout, converted to the tax currency at the
  rates of its own money date and rounded to the cent, truncated in DE. The payouts of a policy use them one
  after another: a partial withdrawal uses its share units sold / value before. A holder who moved (CH -> DE) has the
  chain counted in the currency of each payout;
- taxable base, in the tax currency, rounded once: CH the gross converted on the payout day, IT and DE the gain
  = that gross less the premiums used (at least 0); DE x (1 - TFS), half under HEV, 0 for contracts with regular
  premiums started before 2005 and held 12 years (NRTAXB books KST on every single premium one with a gain, as
  the old law asked for 5 years of premiums); LU none. A payout without withholding reports the base 0;
- amounts: VST, SOS = base x rate; KST = base x rate, divided by (1 + rate x KIS) when the payout has a KIS
  booking (the label, not the address); SOL, KIS = KST x rate; STP = the premium of event 2 in francs x rate.
  Rounded half up, German taxes truncated (or COBOL truncates and Neuron NG rounds half up, with
  `ROUNDED_BY_SYSTEM`);
- Bollo: BOL = surrender value (the value less the penalty, as Italian rules have it for insurance policies;
  `BOLLO_ON_SURRENDER_VALUE`) x rate x days run / days of the year; the TAXFIX19 re-pricing is the difference of the
  earlier BOL at the restated rate, **rounded once on the total**: BL10000044 2019 = 421.57 + 194.54 = 616.11, as
  in the example (rounding every year gives 194.53). BOC collects the outstanding BOL, all of it at a payout that
  ends the policy, its share at a partial withdrawal. A negative amount rounds like its positive twin;
- remittance: DE the 10th of the next month (example), IT the 16th and CH 30 days after the month end (law),
  no business-day shift.

Example 1 (BL10000086 #121: a USD policy, surrendered on 17.7.2006, gross 12'107.36 USD, 28 premiums of 420.00
USD) decides the base. Every premium converted on its money date and truncated gives 5'628.16, as in the PDF;
rounded half up 5'628.01, unrounded 5'628.02, and the whole gain converted on the payout day 539.30. The rate of
the day before, the due dates and the reversed premium all miss. Then KST 25 % = 1'407.04 and SOL 5.5 %, truncated,
= 77.38.

The labels settle the discrete choices: VST is booked only for holders who objected to the reporting (AD_TAXST
E) with a gross above TX_THRSH (257 of 259; never for the 1'275 payouts of reported holders), SOS and KST when
the gain is above 0, no SOS on Italian death claims, and the country of every payout with tax is its residence.

Open, with no labels: each choice is one line in `conventions.py`, to be changed one per upload as the actuary
answers: the base of a payout without tax (`BASE_WITHOUT_TAX`: 0 since the upload after the 5 % of 19:30), the
base of the Bollo (`BOLLO_ON_SURRENDER_VALUE`: the surrender value, against the 70 % of the annual table), the
rounding by system instead of by country (`ROUNDED_BY_SYSTEM`), the remittance day of a payout with stamp duty
alone (`STAMP_DUTY_REMITTED`), the remittance days of IT and CH (`REMITTANCE`) and their move to a business day
(`REMITTANCE_SHIFTED`), the rounding of the IT conversion (`TRUNCATED_CONVERSION`) and HEV on the withholding
(`HALF_INCOME_WITHHELD`). Also
assumed: the first EUR rate for the days before 31.12.1998, and the pro-rata share of a partial withdrawal (no
example). `t7lab/t7_check.py` checks the rest on the real tables before an upload.

## Code quality

As the strategy suggests: thin task functions, small modules with one job each, the conventions as data instead
of branches, and docstrings that state the rule in business terms. The polars expressions use its methods
(`.add`, `.mul`, `.floordiv`, `.eq`, ...); the Z3 tools write their constraints in SMT-LIB, the input language of
Z3, and let Z3 parse them (`(<= low (* base rate) high)`); plain Python keeps its operators where they read
better, as in the t7 lab next to the folder. The maintainability index (radon, weighted by lines of code) is 100
for the whole folder and for every module of the submission: a signal, not a target.

## Memory

The evaluation allows 5 GB and 2 CPUs. All tasks in one process peak at 3.3 GB working set with 2 polars
threads (5.8 GB before):

- the export is read with the streaming engine (`legacy.scan`), in batches instead of 6.8 million rows of text;
- the unit account reads only the rows of NRBOOK that are no charges (`bookings.uncharged_bookings`): the
  charges are 6.2 million rows, and the charge runs calculate them anew;
- `legacy.valid_on` chooses the version on the keys and dates alone and joins the wide rows once;
- `valuation.values_on` adds the units up per position and trade date once and looks up every day with an as-of
  join, instead of copying the account for every day (the Bollo of t7 values 5'500 policy-days);
- t0 – t4 and t7 in one process, on synthetic tax tables of that size (10'716 bookings, 7'018 of them Bollo):
  10 s and a peak of 3.4 GB on 2 polars threads.

## Running the tools

```
pip install -r requirements.txt -r tools/requirements.txt
PYTHONPATH="$PWD:$PWD/tools" python -c "from neuron.backtest import backtests; print(backtests())"
PYTHONPATH="$PWD:$PWD/tools" python -c "from neuron.bisection import corrected_maturities; print(corrected_maturities())"
PYTHONPATH="$PWD:$PWD/tools" python -c "from neuron.account_check import surrender_mismatches; print(surrender_mismatches())"
PYTHONPATH="$PWD:$PWD/tools" python -c "from neuron.account_check import statement_mismatches; print(statement_mismatches())"
POLARS_MAX_THREADS=2 PYTHONPATH="$PWD:$PWD/tools:$PWD/.." python -B -m t7lab.t7_check   # tax tables: open-weights model only
POLARS_MAX_THREADS=2 PYTHONPATH="$PWD:$PWD/tools:$PWD/.." python -B -m t7lab.t7_labels  # tax tables: open-weights model only
```

The tools look for the data in `$NEURON_DATA`, by default the `participants` folder that contains this
hand-in. They cache decoded tables as parquet in `cache/` next to it. Only the tools read the train targets,
for exploring and checking.
