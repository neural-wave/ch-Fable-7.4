"""What each position is worth after the ADM and the AMC of a run: the base of the risk charge.

The risk charge is computed on the total of it and shared in proportion to it.
"""


def left(values, admin, management):
    """{position: value} left after the ADM and then the AMC of the month."""
    return {position: value - admin.get(position, 0) - management.get(position, 0) for position, value in values.items()}
