"""Totals by key: the yearly sums of an annual statement.

The amounts are added as they are, unrounded; whoever reports a total rounds it.
"""
import collections


def by_key(rows, key, amount):
    """Counter {key(row): sum of amount(row)} of `rows`."""
    sums = collections.Counter()
    for row in rows:
        sums[key(row)] += amount(row)
    return sums
