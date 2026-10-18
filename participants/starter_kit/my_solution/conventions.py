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
PAID_OUT = ["WDR", "SUR", "DTH"]  # BK_BKTYP of the money of a payout: its BK_AMTPC is negative
TAXES = {"STP": "CH", "VST": "CH", "SOS": "IT", "BOL": "IT", "BOC": "IT", "KST": "DE", "SOL": "DE", "KIS": "DE",
         "HEV": "DE", "TFS": "DE"}  # every TAXTP of NRCODE -> its country, TX_CNTRY of its rates in NRTAXR
ANNUAL_TAXES = ["STP", "VST", "SOS", "BOL", "KST", "SOL", "KIS"]  # the columns of t7_tax_annual; BOC is not reported
WITHHELD, SURCHARGES, STAMP_DUTY = ["VST", "SOS", "KST"], ["SOL", "KIS"], ["BOC"]  # the amounts of a payout
TAX_CURRENCY = {"CH": "CHF", "IT": "EUR", "DE": "EUR", "LU": "EUR"}  # country -> currency of its taxes
ROUNDING = {"CH": "system", "IT": "system", "DE": "system"}  # country -> how Neuron rounds its taxes to the cent.
# "system": the system that processed the booking (TB_CHGTS) decides, as in every task with targets (t0, t2, t3):
# COBOL truncated, Neuron NG (from CONVERSION) rounds half up. "truncate": always truncated. "half_up": always half
# up. The example (DE, 2006, 1407.04 x 5.5 % = 77.3872 -> 77.38) was processed by COBOL and fits "system" and
# "truncate" (assumption, to test)
PREMIUM_ROUNDING = {"CH": "system", "IT": "system", "DE": "system"}  # the same for the premiums converted to the tax
# currency, decided by the system that processed the payout (example: only truncation gives 5628.16, 28 premiums
# of a payout of 2006)
PREMIUMS_ROUNDED_AT_RECEIPT = False  # True: a converted premium is rounded by the system of its own money date
# PR_RCVDT, whatever PREMIUM_ROUNDING says, as if Neuron had converted it when received (assumption, to test: 160
# of the 241 taxed Italian and German payouts are of Neuron NG with premiums received under COBOL)
TAXED_ON_GROSS, TAXED_ON_GAIN = ["CH"], ["IT", "DE"]  # the taxable base of a payout; none elsewhere, LU (law)
BLENDED_RATES = []  # tax types whose rate is averaged by days over the life of the policy (`taxpayer.blended_rates`):
# ["SOS"] takes the gain of each period at its rate, 12.5 % to 2011, 20 % to June 2014, 26 % after (law, DL 138/2011
# and DL 66/2014); [] the rate valid on the payout day, as read 11 and 10 of 30 by the actuary (assumption, to test
# once the payout table reads above 0: it changes 97 payouts and 95 annual rows)
BASE_WITHOUT_TAX = True  # a payout without withholding reports the base as calculated: what Neuron calculated and,
# for the holders on the reporting procedure (AD_TAXST M), reported; False reports 0 (assumption: the payout table
# scored 1 of 20 with it and 0 of 40 with 0, on samples made mostly of payouts with tax)
REMITTANCE = {"DE": ("month", 10), "IT": ("month_end", 0), "CH": ("day", 30)}  # country -> (anchor, days): the
# day Neuron paid the taxes of a payout is the anchor plus the days. "month": the last day of the month of the payout
# day (so 10 = the 10th of the month after: DE, section 44 EStG and the example 2006-07-17 -> 2006-08-10; 16 = the
# 16th, the F24 of Italy; 30 = the law's 30 days after the month for CH, art. 16 VStG). "month_end": the last day of
# the month after (CH: the reading "by the end of the next month" of the same article). "day": the payout day itself
# ("30 days after the benefit"). "quarter": the last day of the quarter (CH: 30 days after the quarter, the rule of
# the bank interests). Read 0 of 40 by the actuary: ("month", 10) everywhere and CH ("month", 30) (assumption, to test)
REMITTED_FROM_PAYMENT = True  # the remittance month follows the day the money was paid, the effective date + the
# payout business days PD_PAYDAY of the product (NRPROD, read by no other rule; the law of all three countries
# counts from the payment); False: from the effective date. The example fits both: paid 2006-07-24, still in July
# (assumption, to test: it moves the month of about a fifth of the payouts with tax)
REMITTANCE_SHIFTED = ["DE", "IT", "CH"]  # countries whose remittance day moves to the next business day of its
# calendar: the law moves a deadline that falls on a weekend or holiday, about 30 % of the days (law; the example, a
# Thursday, fits both). [] keeps the day as it is, as Neuron's own batches that run on weekends (assumption, to test)
REMITTANCE_CALENDARS = {"DE": {"country": "DE", "years": range(1994, 2100)},
                        "IT": {"country": "IT", "years": range(1994, 2100)}, "CH": CALENDAR}  # the tax offices; the
# other variant is Neuron's own calendar CALENDAR for every country, as for the direct debits
STAMP_DUTY_COUNTRY = "IT"  # a payout with stamp duty only pays it to Italy
STAMP_DUTY_REMITTED = False  # a payout with stamp duty alone has no remittance day (None), as the PDF says "None if
# nothing was withheld" when the stamp duty collected does not count as withheld; True: the day of Italy
# (assumption, to test: 182 payouts)
CHURCH_REDUCED, CHURCH_TAX = "KST", "KIS"  # DE: with a KIS booking the KST is base x KST / (1 + KST x KIS),
# section 32d EStG (law); the KIS booking of the payout is the label, not the address
CHURCH_REDUCES_KST = True  # DE: the KIS booking reduces the KST as above (law, from 2009); False: base x KST and the
# church tax on top (assumption, to test)
COLLECTED_IN_ANNUAL = False  # IT: it_bol of the annual table adds up the Bollo accrued (BOL); True also the Bollo
# collected at the payouts of the year (BOC), which pays the accrued one (assumption, to test)
PREMIUM_STAMP = "STP"  # CH: the stamp duty on the premium of its event, the single premium
BOLLO_FIX = "TAXFIX"  # TB_USRID of the re-pricing of the Bollo after the rate restatement of July 2019 (NRTAXB)
BOLLO_FIX_PER_YEAR = True  # the fix books, for every earlier BOL, the Bollo at the restated rate less the amount
# booked, both in cents: a fix job works on booked amounts. False: the difference of the rates over all the earlier
# BOL, rounded once. The example fits both (BL10000044, 2019) (assumption)
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
HALF_INCOME_WITHHELD = True  # DE: HEV halves the base of the withholding (assumption: NRTAXR has HEV rates, while
# the law, as far as we know, leaves HEV out of the KapESt)
