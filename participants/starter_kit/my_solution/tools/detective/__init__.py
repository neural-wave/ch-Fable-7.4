"""detective: an AI-driven method that finds the rules of a legacy system from its data and its targets.

The package knows nothing of the tasks. The legacy export enters through its data dictionary (`load`), a target
through a `spec.TaskSpec`, and the discovery loop (`discover`) turns the rows a rule gets wrong into findings.
"""
