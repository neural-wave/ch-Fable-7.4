"""Neuron, the legacy system: its extract as typed tables, and the helpers the rules are written with.

The task functions and the code templates of the lab (`lab freeze`) import everything from here, so a
generated function needs one import line:
- `table` gives the typed rows of a legacy table, `read_targets` the target files (only t5 may read them);
- `keyed`, `grouped`, `latest` and `valid` look rows and versions up;
- `cents` and `era_rounding` round like Neuron, `add_months` and the other dates count like it.
"""
from .dates import add_months, age, calendar_years, months_between, policy_years
from .eras import SYSTEM_CHANGE, cents, era_rounding, is_cobol
from .extract import read_targets, table
from .days import OPEN_END, day
from .lookups import differing_keys, first_after, grouped, keyed, on_or_before
from .versions import first_valid, latest, valid

__all__ = ["OPEN_END", "SYSTEM_CHANGE", "add_months", "age", "calendar_years", "cents", "day", "differing_keys",
           "era_rounding",
           "first_after", "first_valid", "grouped", "is_cobol", "keyed", "latest", "months_between", "on_or_before",
           "policy_years", "read_targets", "table", "valid"]
