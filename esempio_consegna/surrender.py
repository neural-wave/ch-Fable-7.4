"""Surrender value: the policy value less the penalty, rounded the way of the day.

It is never negative: a policy whose units are worth less than nothing pays out nothing.
"""
import conventions as c
import money


def value(policy_value, penalty, day):
    """Surrender value of a `policy_value` with a `penalty` share on `day`."""
    return max(money.cents(policy_value * (1 - penalty), day), c.NOTHING)
