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
