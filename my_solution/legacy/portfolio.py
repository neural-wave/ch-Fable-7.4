"""The policies of the portfolio and their history.

Every change to a policy creates a new version in NRPOLH, valid from one day to another.
Each task asks for the version valid on its own day: the money date of a premium (t0),
the extract date (t1), a valuation date (t3).
"""
import functools

import conventions as c
from core import lookup
from legacy import tables


@functools.cache
def versions(legacy_dir):
    """{policy_id: all versions of the policy}, in the order of the export."""
    return lookup.group(tables.table(legacy_dir, "NRPOLH"), "PH_POLNR")


def version_on(history, when):
    """The version of one policy valid on `when`, or None if the policy did not exist yet.

    If two versions overlap, the higher version number wins.
    """
    return lookup.valid_on(history, when, "PH_VLDFR", "PH_VLDTO", "PH_VRSNR")


def policies_on(legacy_dir, when):
    """The version valid on `when` of every policy that existed on that day."""
    current = (version_on(history, when) for history in versions(legacy_dir).values())
    return [policy for policy in current if policy]


def pays_premiums(policy):
    """In force (state 10) and paying regular premiums: the policy has a premium schedule.

    Paid-up (20), premium holiday (30), surrendered (60) and death (70) policies have none.
    """
    return policy["PH_STATE"] == c.IN_FORCE and policy["PH_FREQ"] != c.SINGLE_PREMIUM
