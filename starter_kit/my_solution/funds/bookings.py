"""The bookings of a policy, from its events (NREVNT) and its paid premiums (NRPREM, NRALLO), in processing order."""
import datetime as dt
import functools
from collections.abc import Callable
from operator import attrgetter
from typing import NamedTuple

from neuron import grouped, valid
from policies.codes import CHARGE_RUN, SALES, SWITCH, active_events, is_paid

FIRST, AFTER_CHARGE_RUN = 0, 1  # rank of the bookings of a day


class Booking(NamedTuple):
    """A premium, charge run or customer order, to be booked on its trade date.

    Neuron processed the bookings by trade date; on the same day the charge run comes before the premiums and
    orders, which are processed in the order of their event numbers (EV_EVTNR, PR_EVTNR).
    """

    day: dt.date
    rank: int
    event: int
    apply: Callable  # apply(day) books it on the FundAccount


PROCESSING_ORDER = attrgetter("day", "rank", "event")
RANKS = {CHARGE_RUN: FIRST, SWITCH: AFTER_CHARGE_RUN, **dict.fromkeys(SALES, AFTER_CHARGE_RUN)}


def event_bookings(events, handlers):
    """The charge runs and customer orders, booked with the handler of their event type, `handler(event, day)`.

    Reversed events are left out, and so are the event types without a handler: the reversals themselves and
    the technical corrections (990), which move no units.
    """
    return [Booking(event["EV_EFFDT"], RANKS[event["EV_EVTTP"]], event["EV_EVTNR"], functools.partial(handler, event))
            for event in active_events(events) if (handler := handlers.get(event["EV_EVTTP"]))]


def premium_bookings(premiums, allocations, market, invest):
    """The investments of the paid premiums, booked with `invest(premium, share, day)`.

    Each premium buys units of every fund of the allocation valid on its money date, on the first price date
    of the fund after the money date.
    """
    shares = grouped(allocations, "AL_VRSNR")
    return [Booking(market.price_day(share["AL_FNDID"], premium["PR_RCVDT"], after=True), AFTER_CHARGE_RUN,
                    premium["PR_EVTNR"], functools.partial(invest, premium, share))
            for premium in filter(is_paid, premiums)
            for share in shares[valid(allocations, "AL", premium["PR_RCVDT"])["AL_VRSNR"]]]
