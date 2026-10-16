# Neuron data schema

This is the extract of Neuron, the policy administration system of NeuralWave Life, taken on 2026-06-30. The column descriptions come from the old data
dictionary `NRDICT`, and how Neuron calculates its values is not documented anywhere.

## Conventions

- One file per table, `<TABLE>.csv`, separated by `;`, UTF-8, with a header row. An empty field means no value.
- Table names are `NR` plus four letters. A column name is the two-letter alias of its table, `_` and a abbreviation.
  The same abbreviation means the same business key, so `RK_POLNR` refers to `PH_POLNR`.
- `C` columns have a fixed length and are padded with blanks on the right (`'BL10000001  '`). Trim them before you
  join tables.
- `N(s)` columns are integers with `s` implied decimals: in `N(2)` the value `123456` is 1234.56, in `N(6)` the
  value `12500` is 0.0125.
- `D` columns are dates stored as `CYYMMDD`, where C is 0 for 19xx and 1 for 20xx. `1250131` is 2025-01-31 and
  `970630` is 1997-06-30 (the leading 0 of the 19xx dates is lost). `0` means no date and `9999999` open end.
- `T` columns are timestamps `YYYYMMDDHHMMSS`.
- Validity periods `..._VLDFR` to `..._VLDTO` include both days.
- In tables with a `..._VRSNR` the row valid on a date d is the one with `VLDFR <= d <= VLDTO`. If several rows are
  valid, the highest version number wins.
- Amounts are in the policy currency `PH_CCY` unless a column says otherwise.
- `NRCODE` explains every code. Its domain is the abbreviation of the column, e.g. `STATE`, `EVTTP` or `BKTYP`.

## Contract data

### NRPOLH: policy header, versioned (key PH_POLNR, PH_VRSNR)
| Column | Type | Description |
|---|---|---|
| PH_POLNR | C12 | policy number |
| PH_VRSNR | N(0) | version number |
| PH_VRSST | C1 | version status (C=current, S=superseded) |
| PH_VLDFR | D | valid from (inclusive) |
| PH_VLDTO | D | valid to (inclusive) |
| PH_EVTNR | N(0) | creating event |
| PH_CHGTS | T | processing timestamp |
| PH_PRDCD | C4 | product code |
| PH_STATE | N(0) | policy state |
| PH_CCY | C3 | policy currency |
| PH_APPDT | D | application date |
| PH_BEGDT | D | start date |
| PH_ENDDT | D | maturity date |
| PH_FREQ | C1 | premium frequency |
| PH_PAYMT | C2 | payment method |
| PH_PREMI | N(2) | instalment premium |
| PH_BRKNR | C6 | broker |
| PH_MKTCD | C6 | campaign |
| PH_USRID | C8 | clerk |

### NRRISK: insured risk (key RK_POLNR)
| Column | Type | Description |
|---|---|---|
| RK_POLNR | C12 | policy number |
| RK_RSKNR | N(0) | risk number (1 = main risk) |
| RK_TARKEY | C7 | tariff key |
| RK_PERNR | C8 | insured person |
| RK_SUMIN | N(2) | sum insured |
| RK_BEGDT | D | risk start |
| RK_ENDDT | D | risk end |
| RK_LOAD | N(6) | medical extra loading |
| RK_UWCLS | C2 | underwriting class |

The tariff key `RK_TARKEY` looks like `FXU03LB`:

| Position | Meaning | Values |
|---|---|---|
| 1-2 | tariff family | `FK`, `FX`, `FS` (see `NRPROD.PD_TARFAM`) |
| 3 | sex basis | `M` male, `W` female, `U` unisex (then the person's sex applies) |
| 4-5 | tariff generation | `01` to `04` |
| 6 | premium type | `L` regular, `E` single |
| 7 | death benefit option | `A` 101 % of the fund value, `B` the higher of sum insured and fund value, `C` fund value plus sum insured |

### NRPERS: persons (key PS_PERNR)
| Column | Type | Description |
|---|---|---|
| PS_PERNR | C8 | person number |
| PS_BIRTH | D | birth date |
| PS_SEX | C1 | sex |
| PS_SMOKE | C1 | smoker (Y/N) |
| PS_CNTRY | C2 | country |
| PS_LANG | C2 | language |
| PS_ZIP | C8 | postal code |
| PS_NAMEH | C16 | masked name |

### NRBROK: brokers (key BR_BRKNR)
| Column | Type | Description |
|---|---|---|
| BR_BRKNR | C6 | broker number |
| BR_TIER | C1 | broker tier |
| BR_CHNL | C2 | channel |
| BR_REGIO | C3 | region |
| BR_SINCE | D | broker since |

### NRAGRE: individual fee agreements (key AG_POLNR, AG_FEETP, AG_VLDFR)
While an agreement is valid, its rate replaces the tariff rate.

| Column | Type | Description |
|---|---|---|
| AG_POLNR | C12 | policy number |
| AG_FEETP | C3 | fee type (ENT/AMC) |
| AG_VLDFR | D | valid from |
| AG_VLDTO | D | valid to |
| AG_RATE | N(6) | agreed rate |
| AG_REASON | C30 | reason |

### NRALLO: fund allocation of the premiums, versioned (key AL_POLNR, AL_FNDID, AL_VRSNR)
Each allocation set has its own `AL_VRSNR`, and the shares of a set add up to 1.

| Column | Type | Description |
|---|---|---|
| AL_POLNR | C12 | policy number |
| AL_FNDID | C5 | fund |
| AL_VRSNR | N(0) | allocation version number |
| AL_VRSST | C1 | version status |
| AL_VLDFR | D | valid from |
| AL_VLDTO | D | valid to |
| AL_EVTNR | N(0) | creating event |
| AL_CHGTS | T | processing timestamp |
| AL_PCTG | N(6) | share of premium |

### NRPREM: premium items (key PR_POLNR, PR_DUENR)
| Column | Type | Description |
|---|---|---|
| PR_POLNR | C12 | policy number |
| PR_DUENR | N(0) | instalment number |
| PR_DUEDT | D | due date |
| PR_AMTDU | N(2) | amount due |
| PR_RCVDT | D | money received date |
| PR_AMTRC | N(2) | amount received |
| PR_STATE | C1 | item state |
| PR_EVTNR | N(0) | booking event |

### NREVNT: business events (key EV_POLNR, EV_EVTNR)
The event numbers go up in the order in which Neuron processed the events. For a reversal (type `900`),
`EV_REVNR` is the event it cancels, otherwise it is `0`. Customer orders (switch, withdrawal, surrender, death)
keep what the customer ordered in `EV_FNDID`, `EV_TOFND` and `EV_PCTG`.

| Column | Type | Description |
|---|---|---|
| EV_POLNR | C12 | policy number |
| EV_EVTNR | N(0) | event number |
| EV_EVTTP | N(0) | event type |
| EV_EFFDT | D | effective date |
| EV_REVNR | N(0) | reversed event |
| EV_CHGTS | T | processing timestamp |
| EV_SRC | C1 | source |
| EV_USRID | C8 | job user |
| EV_FNDID | C5 | fund of the order |
| EV_TOFND | C5 | target fund of a switch |
| EV_PCTG | N(6) | share of units sold |

### NRBOOK: unit bookings (key BK_BOOKID)
For the booking types `PRM`, `ADM`, `AMC` and `RSK` the columns `BK_AMTPC`, `BK_FXRAT`, `BK_PRICE` and `BK_UNITS`
are empty. A nightly job calculated them, and that job is not part of the extract.

| Column | Type | Description |
|---|---|---|
| BK_BOOKID | N(0) | booking ID |
| BK_POLNR | C12 | policy number |
| BK_EVTNR | N(0) | event |
| BK_FNDID | C5 | fund |
| BK_POTCD | C1 | unit pot |
| BK_BKTYP | C3 | booking type |
| BK_RCVDT | D | money date |
| BK_TRDDT | D | trade date |
| BK_PRCDT | D | price date |
| BK_AMTPC | N(2) | amount policy currency |
| BK_FXRAT | N(6) | fund currency per policy currency |
| BK_PRICE | N(6) | unit price |
| BK_UNITS | N(6) | units |

## Tax module

Neuron also withheld and reported the taxes of the policyholders. These tables come from its tax module.

### NRHOLD: policyholder, versioned (key HD_POLNR, HD_VRSNR)
The policyholder is usually, but not always, the insured person `RK_PERNR`.

| Column | Type | Description |
|---|---|---|
| HD_POLNR | C12 | policy number |
| HD_VRSNR | N(0) | version number |
| HD_VLDFR | D | valid from |
| HD_VLDTO | D | valid to |
| HD_PERNR | C8 | policyholder |
| HD_CHGTS | T | processing timestamp |

### NRADDR: residence of a person, versioned (key AD_PERNR, AD_VRSNR)
`PS_CNTRY` in `NRPERS` is the country of the person when the first policy was applied for.

| Column | Type | Description |
|---|---|---|
| AD_PERNR | C8 | person number |
| AD_VRSNR | N(0) | version number |
| AD_VLDFR | D | valid from |
| AD_VLDTO | D | valid to |
| AD_CHGTS | T | processing timestamp |
| AD_CNTRY | C2 | country of residence |
| AD_REGIO | C3 | region |
| AD_ZIP | C8 | postal code |
| AD_TAXST | C1 | tax reporting status |
| AD_CHURCH | C1 | church member |

### NRTAXR: tax rates, versioned (key TX_CNTRY, TX_TAXTP, TX_REGIO, TX_VLDFR, TX_VRSNR)
| Column | Type | Description |
|---|---|---|
| TX_CNTRY | C2 | country |
| TX_TAXTP | C3 | tax type |
| TX_REGIO | C3 | region (blank = all) |
| TX_VLDFR | D | valid from |
| TX_VLDTO | D | valid to |
| TX_VRSNR | N(0) | version number |
| TX_RATE | N(6) | rate |
| TX_THRSH | N(2) | threshold |
| TX_CHGTS | T | entered at |

### NRTAXB: tax bookings (key TB_BOOKID)
`TB_AMOUNT` and `TB_REMDT` are empty, like the calculated columns of `NRBOOK`.

| Column | Type | Description |
|---|---|---|
| TB_BOOKID | N(0) | tax booking ID |
| TB_POLNR | C12 | policy number |
| TB_EVTNR | N(0) | event |
| TB_TAXTP | C3 | tax type |
| TB_EFFDT | D | effective date |
| TB_CHGTS | T | processing timestamp |
| TB_USRID | C8 | job user |
| TB_AMOUNT | N(2) | amount in tax currency |
| TB_REMDT | D | remitted to the tax office |

## Market data

### NRFUND: funds (key FD_FNDID)
| Column | Type | Description |
|---|---|---|
| FD_FNDID | C5 | fund |
| FD_CCY | C3 | fund currency |
| FD_ASSCL | C2 | asset class |
| FD_ISIN | C12 | ISIN |
| FD_LNCDT | D | launch date |

### NRFPRC: unit prices (key FP_FNDID, FP_PRCDT, FP_CHGTS)
Prices are sometimes restated. The latest publication counts.

| Column | Type | Description |
|---|---|---|
| FP_FNDID | C5 | fund |
| FP_PRCDT | D | price date |
| FP_BIDPR | N(6) | bid |
| FP_ASKPR | N(6) | ask |
| FP_MIDPR | N(6) | mid |
| FP_CHGTS | T | publication time |

### NRFXRT: exchange rates (key FX_CCY, FX_RATDT)
Cross rates go via CHF. EUR exists from 1998-12-31.

| Column | Type | Description |
|---|---|---|
| FX_CCY | C3 | currency |
| FX_RATDT | D | rate date |
| FX_RATE | N(6) | CHF per unit |

### NRMORT: mortality tables (key MO_TABID, MO_SEX, MO_AGE)
| Column | Type | Description |
|---|---|---|
| MO_TABID | C4 | mortality table |
| MO_SEX | C1 | sex |
| MO_AGE | N(0) | age |
| MO_QX | N(6) | death probability |

## Product and tariff parameters

### NRPROD: products (key PD_PRDCD)
| Column | Type | Description |
|---|---|---|
| PD_PRDCD | C4 | product code |
| PD_NAME | C30 | product name |
| PD_TARFAM | C2 | tariff family |
| PD_INIMON | N(0) | months of initial pot |
| PD_SRPSCL | N(0) | surrender scale |
| PD_PAYDAY | N(0) | payout business days |

### NRCHRG: charges (key CG_TARFAM, CG_TARGEN, CG_VLDFR)
| Column | Type | Description |
|---|---|---|
| CG_TARFAM | C2 | tariff family |
| CG_TARGEN | C2 | tariff generation |
| CG_VLDFR | D | valid from |
| CG_VLDTO | D | valid to |
| CG_ADMFEE | N(2) | admin fee per month |
| CG_AMCP1 | N(6) | management charge pot 1 p.a. |
| CG_AMCP2 | N(6) | management charge pot 2 p.a. |
| CG_SMKFAC | N(6) | smoker factor |
| CG_MORTTB | C4 | mortality table |

### NRENTC: entry charges (key EC_TIER, EC_VLDFR)
| Column | Type | Description |
|---|---|---|
| EC_TIER | C1 | broker tier |
| EC_VLDFR | D | valid from |
| EC_VLDTO | D | valid to |
| EC_RATE | N(6) | entry charge rate |

### NRCOMR: commission rates (key CR_TIER, CR_PAYTP, CR_VLDFR)
| Column | Type | Description |
|---|---|---|
| CR_TIER | C1 | broker tier |
| CR_PAYTP | C1 | premium type |
| CR_VLDFR | D | valid from |
| CR_VLDTO | D | valid to |
| CR_RATE | N(6) | commission rate |

### NRSURR: surrender scales (key SR_SCALE, SR_YEAR)
If there is no row, there is no penalty.

| Column | Type | Description |
|---|---|---|
| SR_SCALE | N(0) | surrender scale |
| SR_YEAR | N(0) | completed policy years |
| SR_RATE | N(6) | surrender penalty |

### NRWAIV: periods without surrender penalty (key WV_VLDFR)
| Column | Type | Description |
|---|---|---|
| WV_VLDFR | D | waiver from |
| WV_VLDTO | D | waiver to |
| WV_REASON | C30 | reason |

### NRILLU: growth rates for offers (key IL_VLDFR)
| Column | Type | Description |
|---|---|---|
| IL_VLDFR | D | valid from |
| IL_VLDTO | D | valid to |
| IL_RATE | N(6) | illustration growth rate p.a. |

## Metadata

### NRCODE: code lists (key CD_DOMAIN, CD_CODE)
| Column | Type | Description |
|---|---|---|
| CD_DOMAIN | C6 | domain |
| CD_CODE | C4 | code |
| CD_TXTDE | C40 | German text |
| CD_TXTEN | C40 | English text |

### NRDICT: data dictionary (key DC_TABLE, DC_COLUMN)
| Column | Type | Description |
|---|---|---|
| DC_TABLE | C6 | table |
| DC_COLUMN | C9 | column |
| DC_TYPE | C1 | type |
| DC_LEN | N(0) | length |
| DC_SCALE | N(0) | scale |
| DC_DESC | C60 | description |

### NREXCP: known manual corrections (incomplete)
| Column | Type | Description |
|---|---|---|
| EX_POLNR | C12 | policy number |
| EX_TARGET | C40 | affected value |
| EX_REASON | C60 | reason |
| EX_TSTMP | T | recorded at |

## Target files

The folder `targets/` has the values for the train policies in the format of the new system: separated by `,`,
ISO dates and decimal numbers. Key columns are in bold, and `policy_id` is `PH_POLNR` without the blanks. Files
marked as diagnostic are not scored, they are only there to help you debug. The train targets of
`t3_surrender_value` use the valuation dates 2006-12-31, 2020-04-30, 2025-12-31.

| File | Columns | Content |
|---|---|---|
| `t0_commission.csv` | **policy_id**, **due_nr**, amount | commission of every counted premium item |
| `t1_next_due_dates.csv` | **policy_id**, **n**, due_date, collection_date | due dates after the extract date, n = 1, 2, ... |
| `t2_projected_maturity_value.csv` | **policy_id**, maturity_value | projected value at maturity |
| `t2_projection_year.csv` *(diagnostic)* | **policy_id**, **policy_year**, value | projected value at the end of each policy year |
| `t3_surrender_value.csv` | **policy_id**, **valuation_date**, surrender_value, policy_value | surrender value; policy_value (diagnostic) is the value before the penalty |
| `t3_holding.csv` *(diagnostic)* | **policy_id**, **fund_id**, **pot**, **valuation_date**, units | units per fund and pot on the valuation date |
| `t3_booking.csv` *(diagnostic)* | **booking_id**, policy_id, booking_type, amount_pc, price, units | amount, price and units of the counted PRM/ADM/AMC/RSK bookings that are blank in NRBOOK |
| `t4_annual_statement.csv` | **policy_id**, **year**, premiums, entry_charges, admin_fees, management_fees, risk_charges, total_charges | annual statement per calendar year |
