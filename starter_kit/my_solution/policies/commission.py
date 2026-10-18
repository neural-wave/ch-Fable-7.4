"""The commission of the brokers on the paid premium items: the NRCOMR rate by broker tier and pay type."""
from collections import defaultdict

from neuron import cents, grouped, keyed, table, valid
from neuron.versions import is_valid_on
from policies.codes import is_paid


class Commissions:
    """The policy versions, the risks, the brokers and the commission rates (NRCOMR) of the extract."""

    def __init__(self, legacy_dir):
        self.policies = grouped(table(legacy_dir, "NRPOLH"), "PH_POLNR")
        self.risks = keyed(table(legacy_dir, "NRRISK"), "RK_POLNR")
        self.brokers = keyed(table(legacy_dir, "NRBROK"), "BR_BRKNR")
        self.rates = defaultdict(list)  # (CR_TIER, CR_PAYTP): the NRCOMR rows of a tier and a pay type
        for row in table(legacy_dir, "NRCOMR"):
            self.rates[row["CR_TIER"], row["CR_PAYTP"].strip()].append(row)

    def amounts(self, premiums):
        """((policy_id, due_nr), commission) of the paid premium items with a received day and a valid rate.

        broker = NRBROK of the NRPOLH version valid on PR_RCVDT (highest version wins)
        rate   = NRCOMR.CR_RATE[CR_TIER = BR_TIER, CR_PAYTP = RK_TARKEY[6]] valid on PR_RCVDT
        amount = PR_AMTRC x rate, rounded half up to the cent
        """
        for premium in filter(is_received, premiums):
            policy_id, received = premium["PR_POLNR"].strip(), premium["PR_RCVDT"]
            broker = self.brokers[valid(self.policies.get(policy_id, []), "PH", received)["PH_BRKNR"]]
            rates = self.rates.get((broker["BR_TIER"], pay_type(self.risks[policy_id])), [])
            rate = commission_rate(rates, received)
            if rate is not None:
                yield (policy_id, premium["PR_DUENR"]), cents(premium["PR_AMTRC"] * rate)


def is_received(premium):
    """True for a paid premium item with the day the money was received."""
    return is_paid(premium) and premium["PR_RCVDT"] is not None


def commission_rate(rates, day_):
    """CR_RATE of the NRCOMR row of `rates` valid on `day_`, or None when no row is valid.

    A row needs a start day; when several rows are valid, the latest start wins (the most recent rate), the
    first in the table on a tie.
    """
    valid_rows = [row for row in rates if row["CR_VLDFR"] and is_valid_on(row, "CR", day_)]
    return max(valid_rows, key=lambda row: row["CR_VLDFR"])["CR_RATE"] if valid_rows else None


def pay_type(risk):
    """The pay type of an insured risk: the 6th character of its tariff key RK_TARKEY."""
    return risk["RK_TARKEY"][5]
