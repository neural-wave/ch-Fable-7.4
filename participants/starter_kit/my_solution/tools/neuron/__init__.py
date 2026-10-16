"""Tools built to explore the Neuron export and to find its rules; the submission does not use them.

- `load`, `codes`, `policy`: the tables decoded into readable types, the code texts, the history of a policy.
- `targets`: the train targets and the official scoring, to compare a rule with the expected values.
- `schema`: keys and relations between the tables, found in the data with Desbordante, and their diagram.
- `solver`: Z3 proofs and rate recovery for rounded amounts.
"""
