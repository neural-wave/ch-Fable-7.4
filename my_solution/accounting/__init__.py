"""Accounting: the unit account of a policy, the engine behind t3 and t4.

account holds positions and bookings, conversion and trades turn amounts into units.
investment books the premiums, orders the customer orders, charges the monthly ADM, AMC
and RSK runs (with fees, purchase and sharing), runs the calendar of a policy, and
ledger puts all bookings of a policy together.
"""
