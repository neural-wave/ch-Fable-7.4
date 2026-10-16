"""Insurance age and policy years: how old the insured is for the mortality table.

The age is fixed on the start date and grows by one on every policy anniversary. A policy
keeps the age rule of the system that issued it (see age_rules.py). Birth dates are taken
as written, also the impossible ones of the export (30 Feb 1971).
"""
from dateutil.relativedelta import relativedelta

import age_rules
import conventions as c
import formats
import legacy


def births(legacy_dir):
    """{person: (year, month, day)} of the birth dates as written."""
    return {row["PS_PERNR"].strip(): formats.parts(row["PS_BIRTH"]) for row in legacy.read(legacy_dir, "NRPERS")}


def policy_years(start, day):
    """Completed policy years on `day`; an anniversary on 29 Feb falls on 28 Feb."""
    return relativedelta(day, start).years


def insurance_age(birth, start, day):
    """Insurance age on `day`: the age at the start plus the completed policy years.

    COBOL fixed the age at the start of its policies, Neuron NG at the start of the others.
    """
    rule = age_rules.cobol if start < c.ERA_SWITCH else age_rules.neuron_ng
    return rule(birth, start) + policy_years(start, day)


def insured_age(export, contract, day):
    """Insurance age on `day` of the person insured by a policy."""
    return insurance_age(export.births[export.risks[contract.policy_id]["RK_PERNR"]], contract.start, day)
