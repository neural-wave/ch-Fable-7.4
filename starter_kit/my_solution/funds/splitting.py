"""How the charges of a charge run are spread over the holdings of a policy."""
from neuron import cents


def split(total, weights, rounding):
    """`total` in proportion to the weights, each part rounded to the cent.

    The largest weight takes the rounding difference, so the parts always add up to `total`.
    """
    total_weight = sum(weights.values()) or 1
    parts = {key: cents(total * weight / total_weight, rounding) for key, weight in weights.items()}
    parts[max(weights, key=weights.get)] += total - sum(parts.values())
    return parts


def net_values(values, admin, management):
    """{holding: value} after the admin fee and the management charge.

    The risk charge is computed on this value, and split over the holdings in proportion to it.
    """
    return {key: value - admin[key] - management[key] for key, value in values.items()}
