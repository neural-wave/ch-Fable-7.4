"""Lookups on the rows of a table, by a unique key or by group, and on sorted lists of days."""
import bisect
import operator


def keyed(rows, *key):
    """{key: row} of a table whose key columns are unique, e.g. brokers by BR_BRKNR.

    The key of one column is its value, the key of several columns the tuple of their values.
    """
    key_of = operator.itemgetter(*key)
    return {key_of(row): row for row in rows}


def grouped(rows, *key):
    """{key: [row, ...]} in the order of the table, e.g. all versions of each policy in NRPOLH."""
    key_of, groups = operator.itemgetter(*key), {}
    for row in rows:
        groups.setdefault(key_of(row), []).append(row)
    return groups


def differing_keys(computed, expected):
    """The keys of both dicts whose values differ, e.g. the targets a rule does not reproduce."""
    return {key for key in computed.keys() & expected.keys() if computed[key] != expected[key]}


def on_or_before(days, day_):
    """The last of the sorted `days` on or before `day_`.

    A day without a price or rate uses the last one published before it.
    """
    return days[bisect.bisect_right(days, day_) - 1]


def first_after(days, day_):
    """The first of the sorted `days` after `day_`.

    A premium is invested on the first price date after its money date.
    """
    return days[bisect.bisect_right(days, day_)]
