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
