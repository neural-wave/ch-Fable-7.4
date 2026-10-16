"""Finding the rows valid on a given day, and grouping rows.

Policy versions, tariffs, allocations, agreements and waivers all carry a validity period
in Neuron, with both ends included.
"""
import operator


def group_by(rows, key):
    """Rows grouped by `key(row)`, in the order of the export."""
    groups = {}
    for row in rows:
        groups.setdefault(key(row), []).append(row)
    return groups


def group(rows, *columns):
    """Rows grouped by one column, or by a tuple of columns."""
    return group_by(rows, operator.itemgetter(*columns))


def valid_rows(rows, when, valid_from, valid_to):
    """The rows valid on `when`."""
    return [row for row in rows if row[valid_from] <= when <= row[valid_to]]


def valid_on(rows, when, valid_from, valid_to, version=None):
    """The row valid on `when`, or None.

    If several rows are valid, the highest `version` wins (SCHEMA.md).
    """
    valid = valid_rows(rows, when, valid_from, valid_to)
    return max(valid, key=operator.itemgetter(version), default=None) if version else next(iter(valid), None)
