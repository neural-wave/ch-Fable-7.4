"""Conventions of Neuron, found in the data and kept as values instead of branches in the code.

Every hidden rule of the legacy system that the migration team discovered lives in this table,
next to the evidence that fixed it (exact rows on the train targets). An auditor reads one page;
a developer changes one value and the engines follow.
"""
import datetime as dt
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal

# System eras. Event 800 (user CONV2007) moved every policy from COBOL Neuron to Java Neuron NG.
ERA_SWITCH = dt.date(2007, 8, 11)
# COBOL truncated, Neuron NG rounds half up: premium allocations match 100 % in both eras.
ROUNDING_COBOL = ROUND_DOWN
ROUNDING_JAVA = ROUND_HALF_UP
CENT = Decimal("0.01")
NOTHING = Decimal("0.00")  # a value of nothing: surrender values are never below it

# Legacy formats (SCHEMA.md). CYYMMDD 0 means no date, 9999999 an open end.
SPECIAL_DATES = {0: None, 9999999: dt.date.max}
CENTURY_OFFSET = 19_000_000  # CYYMMDD + 19000000 = YYYYMMDD: 1250131 -> 20250131
SEPARATOR = ";"

# Policy data and code lists (NRCODE).
IN_FORCE = 10  # PH_STATE 10: in force and paying premiums
SINGLE_PREMIUM = "E"  # PH_FREQ of single-premium policies
MONTHS_PER_PERIOD = {"M": 1, "Q": 3, "H": 6, "J": 12}
PREMIUM_TYPE_POSITION = 5  # RK_TARKEY[5]: L regular, E single premium
PAID = "P"  # PR_STATE: only paid items count; R returned, O open, W written off
DIRECT_DEBIT = "LS"  # PH_PAYMT Lastschrift: collected on a business day

# Calendar: Ticino public holidays. Good Friday is a working day there; 19 Mar and 29 Jun are not.
HOLIDAY_COUNTRY = "CH"
HOLIDAY_REGION = "TI"
SATURDAY = 5  # date.weekday() of the first day of the weekend

# Unit accounting (t3, t4): with these values every PRM, ADM, AMC and RSK booking of the
# 3,019 train policies is exact, and so are all their surrender values and statements.
PRECISION = 50  # Decimal digits of intermediate results, far more than any rounding needs
UNIT = Decimal("0.000001")  # fund units have 6 decimals
EXTRACT_DATE = dt.date(2026, 6, 30)  # day of the export
RUNS_END = dt.date(2026, 7, 1)  # first day after the export: no charge run from this day on
LAST_STATEMENT_YEAR = 2025  # the last full calendar year before the export
CENTURIES = {"0": "19", "1": "20"}  # first digit C of a CYYMMDD date
HALF_YEAR = 6  # months: Neuron NG rounds an age of x years and 6 months up
PREMIUM, ADMIN, MANAGEMENT, RISK = "PRM", "ADM", "AMC", "RSK"  # booking types (BK_BKTYP)
ORDERS = ("SWO", "SWI", "WDR", "SUR", "DTH")  # customer orders: NRBOOK holds them with their units
EXITS = ("SUR", "DTH")  # surrender and death end the charge runs and the statements
REVERSAL = "900"  # EV_EVTTP as written; a reversal names the event it cancels in EV_REVNR
TECHNICAL_CORRECTION = "990"  # EV_EVTTP of a technical correction: its bookings never happened
CLOSED = (60, 70)  # PH_STATE surrendered and death, also without an exit booking
ENTRY_AGREEMENT, AMC_AGREEMENT = "ENT", "AMC"  # NRAGRE fee types that replace the tariff rate
FIRST_POT, LATER_POT = "1", "2"  # pot 1 holds the premiums received in the first PD_INIMON months
AMC_RATES = {"1": "CG_AMCP1", "2": "CG_AMCP2"}  # tariff column of the yearly AMC rate of a pot
AMC_DAY_BASIS = 360  # COBOL charged the AMC by the day, ACT/360 since the previous run
MONTHS_PER_YEAR = 12  # Neuron NG charges a twelfth of the yearly rate every month
DAYS_PER_YEAR = 365  # COBOL insurance age: days lived / 365, the 29 Februaries do not count
SEX = {"M": "1", "W": "2"}  # RK_TARKEY[2]; U (unisex tariff) takes the sex of the person
SEX_POSITION, OPTION_POSITION = 2, 6  # in RK_TARKEY: FKW02LB is sex W and sum-at-risk option B
VALUE_AT_RISK = Decimal("0.01")  # option A: 1 % of the policy value is at risk
SMOKER = "J"  # PS_SMOKE is J/N (Ja/Nein) in the export, not Y/N as SCHEMA.md says
