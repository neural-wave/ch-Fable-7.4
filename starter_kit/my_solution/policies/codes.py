"""The codes of NRCODE that the rules depend on, and the tests the rules make on them."""
MONTHS_PER_DUE = {"M": 1, "Q": 3, "H": 6, "J": 12}  # FREQ; E (single premium) has no due dates
PREMIUM_PAYING = 10  # STATE: in force, premiums due
CLOSED = {60, 70}  # STATE: surrendered, death claim
PAID = "P"  # PR_STATE of a paid premium item; the states O, R and W are not in NRCODE
SMOKER = {"Y", "J"}  # NRPERS.PS_SMOKE: J (German ja) also means yes
CHARGE_RUN, SWITCH, REVERSAL = 300, 200, 900  # EVTTP
SALES = {400, 410, 500}  # EVTTP withdrawal, surrender, death claim: EV_PCTG of the units of every holding are sold


def is_paid(premium):
    """True for a paid premium item.

    Only the money received is invested and reported; open or reversed items move no units.
    """
    return premium["PR_STATE"] == PAID


def is_closed(version):
    """True for a policy version that is surrendered or closed by a death claim."""
    return version["PH_STATE"] in CLOSED


def has_due_dates(version):
    """True for a policy version in force with regular premiums.

    Single premium policies (FREQ E) and policies without premiums due have no due dates.
    """
    return version["PH_STATE"] == PREMIUM_PAYING and version["PH_FREQ"] in MONTHS_PER_DUE


def active_events(events):
    """The events that are not reversed: a reversal (900) points at the event it reverses with EV_REVNR."""
    reversed_events = {event["EV_REVNR"] for event in events if event["EV_EVTTP"] == REVERSAL}
    return [event for event in events if event["EV_EVTNR"] not in reversed_events]


def is_smoker(person):
    """True for an insured person who smokes."""
    return person["PS_SMOKE"] in SMOKER
