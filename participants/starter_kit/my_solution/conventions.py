"""The conventions of Neuron found in the data, written as data: the rules read them instead of branching on them.

Each value is a fact about the legacy system with the evidence for it in the comment, so a change of convention is
a change of one line.
"""
import datetime as dt

# Policies
IN_FORCE = 10  # PH_STATE: in force and paying premiums (20 paid-up, 30 premium holiday, 60 surrendered, 70 death)
SINGLE_PREMIUM = "E"  # PH_FREQ of single premium policies; the others pay regular premiums
MONTHS = {"M": 1, "Q": 3, "H": 6, "J": 12}  # PH_FREQ -> months between two due dates

# Events
EXTRACT_DATE = dt.date(2026, 6, 30)  # the day of the export (SCHEMA.md): what Neuron did up to then
REVERSAL = 900  # EV_EVTTP of an event that reverses the event EV_REVNR
CONVERSION = dt.date(2007, 8, 11)  # COBOL -> Java (Neuron NG): event 800 on all live policies that night

# Collection of premiums
DIRECT_DEBIT = ["LS"]  # PH_PAYMT that Neuron collects itself, on a business day; UB (bank transfer) keeps the due date
CALENDAR = {"country": "CH", "subdiv": "TI", "years": range(1994, 2100)}  # Ticino: Good Friday is a business day

# Tariff
SIGNED_VERSION = 1  # PH_VRSNR of the policy as signed: the offer ignores every later change
MAIN_RISK = 1  # RK_RSKNR of the main insured risk
TARIFF_KEY = {"TARFAM": (0, 2), "SEXB": (2, 1), "TARGEN": (3, 2), "OPTION": (6, 1)}  # RK_TARKEY: (offset, length)
SEX_BASIS = {"M": "1", "W": "2"}  # tariff sex basis -> MO_SEX; U (unisex) takes the sex PS_SEX of the person
SMOKER = "J"  # PS_SMOKE of a smoker (Ja): the death probability counts CG_SMKFAC times
DEATH_BENEFIT = {  # option -> millionths of (sum insured, value) of which the higher counts, plus of the sum insured
    "A": (0, 1_010_000, 0),  # 101 % of the value
    "B": (1_000_000, 1_000_000, 0),  # the higher of sum insured and value
    "C": (0, 1_000_000, 1_000_000),  # value plus sum insured
}

# Projection of the offer: COBOL projected the offers signed before the conversion, Neuron NG (Java) the later ones
COBOL_AGE = 365  # COBOL: entry age = days since birth / 365 rounded half up, as if there were no leap years
JAVA_AGE = 12  # Neuron NG: entry age = completed months since birth / 12 rounded half up

# Unit account (t3): NRBOOK has every booking, but those that the nightly job calculated have no amounts and units
PREMIUM_RECEIPT = 110  # EV_EVTTP that invests a received premium: bookings PRM, one per fund of the allocation
CHARGE_RUN = 300  # EV_EVTTP of the monthly charge run at 01:30: bookings ADM, AMC and RSK
MANUAL_CORRECTION = 990  # EV_EVTTP entered online with a manual correction of NREXCP: its units don't count
CALCULATED = ["PRM", "ADM", "AMC", "RSK"]  # BK_BKTYP of the nightly job; the others carry their units
CHARGES = ["ADM", "AMC", "RSK"]  # BK_BKTYP of a charge run, in the order the run takes them
INITIAL_POT = "1"  # BK_POTCD of the initial units: management charge CG_AMCP1; the base pot 2 pays CG_AMCP2
AGREED_ENTRY, AGREED_MANAGEMENT = "ENT", "AMC"  # AG_FEETP: individual rates (NRAGRE) that replace the tariff
COBOL_MONTH = 360  # COBOL: the management charge of a month is its days / 360 of the yearly rate
JAVA_MONTH = 12  # Neuron NG: a twelfth of the yearly rate, whatever the days of the month

# Taxes (t7): NRTAXB names every tax booking of Neuron (type, event, dates); only the amounts are calculated.
# The evidence of each rule is in its comment: "example" = an example of the task PDF, "labels" = the bookings of
# NRTAXB, "law" = a prior from the law that no data confirms yet, "assumption" = a choice the data cannot settle
# (to be decided by the actuary).
PAYOUTS = [400, 410, 500]  # EV_EVTTP of a payout: partial withdrawal, full surrender, death claim (NRCODE)
TERMINATING = [410, 500]  # payouts that end the policy: they pay out all of it
PENALIZED = [400, 410]  # payouts that pay the units sold less the surrender penalty of the day; a death claim pays
# them whole. NRTAXB books no tax on the withdrawals and surrenders that the penalty takes to the limit or below,
# and taxes all the others (labels)
DEATH_CLAIM = 500  # EV_EVTTP of a death claim: it pays the death benefit of the tariff option on the units sold, the
# higher of the sum insured and the value, or 101 % of the value, or the value plus the sum insured
# (`charges.death_benefit_factors`; targets: BL10003217 and BL10004258, option A, pay 101 % of the units sold)
PAID_OUT = ["WDR", "SUR", "DTH"]  # BK_BKTYP of the money of a payout: its BK_AMTPC is negative
TAXES = {"STP": "CH", "VST": "CH", "SOS": "IT", "BOL": "IT", "BOC": "IT", "KST": "DE", "SOL": "DE", "KIS": "DE",
         "HEV": "DE", "TFS": "DE"}  # every TAXTP of NRCODE -> its country, TX_CNTRY of its rates in NRTAXR
ANNUAL_TAXES = ["STP", "VST", "SOS", "BOL", "KST", "SOL", "KIS"]  # the columns of t7_tax_annual; BOC is not reported
WITHHELD, SURCHARGES, STAMP_DUTY = ["VST", "SOS", "KST"], ["SOL", "KIS"], ["BOC"]  # the amounts of a payout
TAX_CURRENCY = {"CH": "CHF", "IT": "EUR", "DE": "EUR", "LU": "EUR"}  # country -> currency of its taxes
TRUNCATED = ["DE"]  # countries whose taxes Neuron truncates to the cent (example: 1407.04 x 5.5 % = 77.3872 -> 77.38)
TRUNCATED_CONVERSION = ["DE"]  # countries whose premiums are truncated to the cent when converted to the tax
# currency (example: only this gives 5628.16); IT rounds them half up like its taxes (assumption)
ROUNDED_BY_SYSTEM = True  # the system that processed an amount decides its rounding, as in every task with targets
# (t0, t2, t3): COBOL truncated, Neuron NG (TB_CHGTS from CONVERSION) rounds half up, the bases and the conversions
# alike (targets: CH STP 2006 985.95 and a CH base of 1998 truncated, a DE base of 2012 rounded half up). False:
# by country, TRUNCATED and TRUNCATED_CONVERSION
TRUNCATED_TAXES = ["DE"]  # countries whose tax amounts Neuron truncates to the cent whatever the system (targets:
# BL10001204 2012 SOL + KIS 1.57 + 2.58 = 4.15, BL10004408 2020 KIS 12.78; the example 77.38)
TAXED_ON_GROSS, TAXED_ON_GAIN = ["CH"], ["IT", "DE"]  # the taxable base of a payout; none elsewhere, LU (law)
PERIOD_RATES = ["SOS"]  # tax types that take the gain accrued in each period of their rates at the rate of the
# period (`periods`): the Italian SOS, 12.5 % to 2011, 20 % to June 2014, 26 % after (DL 138/2011, DL 66/2014), the
# gain of a period from the policy value at its end. Every payout takes its share of the gain of each period, which
# then shrinks by that share, as the premiums used do (targets: all 5 SOS payouts, BL10003541 with three payouts)
BASE_WITHOUT_TAX = True  # a payout without withholding reports the base as calculated: what Neuron calculated and,
# for the holders on the reporting procedure (AD_TAXST M), reported; False reports 0 (assumption: the payout table
# scored 1 of 20 with it and 0 of 40 with 0, on samples made mostly of payouts with tax)
REMITTANCE = {"DE": 9, "IT": 15, "CH": 29}  # days after the 1st of the next month: the days of the law, DE the
# 10th (section 44 EStG, and the example: 2006-07-17 -> 2006-08-10), IT the 16th (F24, art. 18 D.Lgs. 241/1997), CH
# 30 days after the month. They scored 0 of 40 twice, but never with the move to a business day and never alone
# (with the base 0 and the Bollo changed). The other variant is the 10th everywhere, the day of Neuron's tax batch
# (TAXBATCH runs every 10 January): {"DE": 9, "IT": 9, "CH": 9} (assumption, to test)
REMITTANCE_MONTH_END = []  # countries that remit on the last day of the month after instead of REMITTANCE (CH: the
# reading "by the end of the next month" of art. 16 VStG; assumption, to test)
REMITTED_FROM_PAYMENT = False  # the remittance month follows the effective date of the payout, the day its tax
# is booked; True: the day the money was paid, the effective date + the payout business days PD_PAYDAY of the
# product (NRPROD, read by no other rule; the law of all three countries counts from the payment). The example fits
# both: paid 2006-07-24, still in July (assumption, to test: it moves the month of about a fifth of the payouts with
# tax)
REMITTANCE_SHIFTED = ["DE", "IT", "CH"]  # countries whose remittance day moves to the next business day of its
# calendar: the law moves a deadline that falls on a weekend or holiday, about 30 % of the days (law; the example, a
# Thursday, fits both). [] keeps the day as it is, as Neuron's own batches that run on weekends (assumption, to test)
REMITTANCE_CALENDARS = {"DE": {"country": "DE", "years": range(1994, 2100)},
                        "IT": {"country": "IT", "years": range(1994, 2100)},
                        "CH": {"country": "CH", "subdiv": "BE", "years": range(1994, 2100)}}  # the tax offices;
# the Swiss one is in Bern, where 2 January is a holiday (targets: BL10000094, 30.12.2017 -> 3.1.2018)
STAMP_DUTY_COUNTRY = "IT"  # a payout with stamp duty only pays it to Italy
STAMP_DUTY_REMITTED = False  # a payout with stamp duty alone has no remittance day: the PDF's "None if nothing was
# withheld", the Bollo collected is not withheld (targets: 6 IT payouts with Bollo alone, none has a day)
CHURCH_REDUCED, CHURCH_TAX = "KST", "KIS"  # DE: with a KIS booking the KST is base x KST / (1 + KST x KIS),
# section 32d EStG (law); the KIS booking of the payout is the label, not the address
CHURCH_REDUCES_KST = True  # DE: the KIS booking reduces the KST as above (law, from 2009); False: base x KST and the
# church tax on top (assumption, to test)
REPORTED_WHEN_REMITTED = [*WITHHELD, *SURCHARGES]  # the taxes withheld from a payout count in the annual table in
# the year of their remittance, not of the payout (targets: BL10003349 paid out 3.12.2025, remitted 16.1.2026, it_sos
# in 2026; four more of the kind). STP and the Bollo count in the year of their effective date (the example)
COLLECTED_IN_ANNUAL = False  # IT: it_bol of the annual table adds up the Bollo accrued (BOL); True also the Bollo
# collected at the payouts of the year (BOC), which pays the accrued one (assumption, to test)
PREMIUM_STAMP = "STP"  # CH: the stamp duty on the premium of its event, the single premium
BOLLO_FIX = "TAXFIX"  # TB_USRID of the re-pricing of the Bollo after the rate restatement of July 2019 (NRTAXB)
BOLLO_FIX_PER_YEAR = False  # the fix books the difference of the rates over all the earlier BOL, rounded once;
# True: for every earlier BOL the Bollo at the restated rate less the amount booked. The example fits both
# (BL10000044, 2019); the targets want it once (BL10003273 2019 142.48, BL10002967 2019 347.13)
BOLLO_ON_SURRENDER_VALUE = False  # IT: the Bollo is on the policy value. True: on the surrender value, the value less
# the penalty, as the Italian rules have it for insurance policies (law); the example cannot tell, its policy has no
# penalty. The actuary scored the annual table 14 of 20 twice without it and 8 of 30 with it (leaderboard)
PARTLY_TAXED = ["DE"]  # countries whose gain is taxed only in part: TFS, HEV and the old contracts
OLD_CONTRACT = dt.date(2005, 1, 1)  # DE: a contract started before is tax free once held HELD_YEARS (law), if it
# pays regular premiums: NRTAXB has KST on every payout with a gain of a single premium (PH_FREQ E) policy and on
# none of a regular premium one (labels); the old law asked for 5 years of premiums
HELD_YEARS = 12  # DE: years held for the old exemption and for HEV, section 20 (1) no. 6 EStG (law)
HALF_INCOME_AGE = {False: 60, True: 62}  # DE: age for HEV by "started on or after HALF_INCOME_2012" (law)
HALF_INCOME_2012 = dt.date(2012, 1, 1)  # DE: contracts from then need the higher age (law)
HALF_INCOME_WITHHELD = False  # DE: HEV does not halve the base of the withholding; True: it does. The law leaves HEV
# to the assessment, and the targets leave the other taxable share of NRTAXR, TFS, out of the withholding too
PARTIAL_EXEMPTION_WITHHELD = False  # DE: the partial exemption TFS (15 % from 2018) does not reduce the base of the
# withholding; True: it does (targets: BL10004408 2020 and BL10000301 2024, KST on the whole gain)
PAYOUT_SCOPE = "all"  # the payouts that t7_tax_payout reports: "all"; or, for a leaderboard probe, "unflagged" (only
# those without a flag of `gaps.FLAGS`, decided by verified rules alone) or "flagged" (only those with one). A probe
# scores only the rows it reports, so it tells in which of the two groups the rows of a sample are right
