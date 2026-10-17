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
TRUNCATED = ["DE"]  # countries whose taxes Neuron truncates to the cent (example: 1407.04 x 5.5 % = 77.3872 -> 77.38)
TRUNCATED_CONVERSION = ["DE"]  # countries whose premiums are truncated to the cent when converted to the tax
# currency (example: only this gives 5628.16); IT rounds them half up like its taxes (assumption)
ROUNDED_BY_SYSTEM = False  # True: the system that processed a tax decides its rounding, as in t2 and t3: COBOL
# truncated, Neuron NG (TB_CHGTS from CONVERSION) rounds half up, the taxes and the conversions alike. The example
# (DE, 2006) was processed by COBOL, so it fits this rule as well as TRUNCATED; False rounds by country (assumption,
# to test on its own: it changes the annual table, which BASE_WITHOUT_TAX does not touch)
TAXED_ON_GROSS, TAXED_ON_GAIN = ["CH"], ["IT", "DE"]  # the taxable base of a payout; none elsewhere, LU (law)
BASE_WITHOUT_TAX = False  # a payout without withholding reports the base 0; True reports it as calculated
# (assumption, from the actuary: with the calculated base the payout table scored 1 of 20, while 56 % of the
# payouts are Swiss ones without withholding: reported (AD_TAXST M) or below the VST threshold)
REMITTANCE = {"DE": 9, "IT": 15, "CH": 29}  # days after the 1st of the next month. DE the 10th (example: 2006-07-17
# -> 2006-08-10, a Thursday); IT the 16th, F24 (law); CH 30 days after the month (law)
REMITTANCE_SHIFTED = []  # countries whose remittance day moves to the next business day of its calendar (assumption:
# none; the law moves a deadline that falls on a weekend or holiday, about 30 % of the days; the example, a
# Thursday, fits both)
REMITTANCE_CALENDARS = {"DE": {"country": "DE", "years": range(1994, 2100)},
                        "IT": {"country": "IT", "years": range(1994, 2100)}, "CH": CALENDAR}  # the tax offices; the
# other variant is Neuron's own calendar CALENDAR for every country, as for the direct debits
STAMP_DUTY_COUNTRY = "IT"  # a payout with stamp duty only pays it to Italy
STAMP_DUTY_REMITTED = True  # a payout with stamp duty alone has a remittance day; False: None, as the PDF says
# "None if nothing was withheld" if the stamp duty collected does not count as withheld (assumption)
CHURCH_REDUCED, CHURCH_TAX = "KST", "KIS"  # DE: with a KIS booking the KST is base x KST / (1 + KST x KIS),
# section 32d EStG (law); the KIS booking of the payout is the label, not the address
PREMIUM_STAMP = "STP"  # CH: the stamp duty on the premium of its event, the single premium
BOLLO_FIX = "TAXFIX"  # TB_USRID of the re-pricing of the Bollo after the rate restatement of July 2019 (NRTAXB)
BOLLO_ON_SURRENDER_VALUE = True  # IT: the Bollo is on the surrender value, the policy value less the penalty, as the
# Italian rules have it for insurance policies (law). The example cannot tell: its policy has no penalty. The share
# of annual rows the actuary found wrong is about the share of Bollo in years with a penalty (assumption, to test);
# False: on the policy value
PARTLY_TAXED = ["DE"]  # countries whose gain is taxed only in part: TFS, HEV and the old contracts
OLD_CONTRACT = dt.date(2005, 1, 1)  # DE: a contract started before is tax free once held HELD_YEARS (law), if it
# pays regular premiums: NRTAXB has KST on every payout with a gain of a single premium (PH_FREQ E) policy and on
# none of a regular premium one (labels); the old law asked for 5 years of premiums
HELD_YEARS = 12  # DE: years held for the old exemption and for HEV, section 20 (1) no. 6 EStG (law)
HALF_INCOME_AGE = {False: 60, True: 62}  # DE: age for HEV by "started on or after HALF_INCOME_2012" (law)
HALF_INCOME_2012 = dt.date(2012, 1, 1)  # DE: contracts from then need the higher age (law)
HALF_INCOME_WITHHELD = True  # DE: HEV halves the base of the withholding (assumption: NRTAXR has HEV rates, while
# the law, as far as we know, leaves HEV out of the KapESt)
