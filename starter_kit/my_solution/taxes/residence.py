"""The country the holder of a policy lives in: NRHOLD gives the holder, NRADDR the addresses."""
from collections import defaultdict

from .days import is_valid_on
from .raw import raw_table


class Residence:
    """The holder of every policy and the addresses of every person."""

    def __init__(self, legacy_dir):
        self.holders = {row["HD_POLNR"].strip(): row["HD_PERNR"].strip() for row in raw_table(legacy_dir, "HOLD")}
        self.addresses = defaultdict(list)
        for row in raw_table(legacy_dir, "ADDR"):
            self.addresses[row["AD_PERNR"].strip()].append(row)

    def country(self, policy_id, day_):
        """AD_CNTRY of the first address of the holder valid on `day_`; None without a holder or an address."""
        addresses = self.addresses.get(self.holders.get(policy_id), [])
        return next((row.get("AD_CNTRY") for row in addresses if is_valid_on(row, "AD", day_)), None)
