"""The tariff of a policy: its charges and rates as valid on the application date, and its insured person.

Prices change over time, so every parameter table has validity periods, and a policy keeps the parameters that
were valid on the day the customer applied (PH_APPDT), not today's. The tariff key RK_TARKEY of the insured risk
names the tariff family and generation, the sex basis and the death benefit option (`conventions.TARIFF_KEY`).
"""
import polars as pl

from conventions import MAIN_RISK, SIGNED_VERSION, TARIFF_KEY
from legacy import table, valid_on


def signed_policies(legacy_dir) -> pl.DataFrame:
    """Every policy as the customer signed it: its first version, with its main risk and the insured person.

    The parts of the tariff key become the columns TARFAM, SEXB, TARGEN and OPTION.
    """
    policies = table(legacy_dir, "NRPOLH").filter(pl.col("PH_VRSNR").eq(SIGNED_VERSION))
    risks = policies.join(table(legacy_dir, "NRRISK").filter(pl.col("RK_RSKNR").eq(MAIN_RISK)),
                          left_on="PH_POLNR", right_on="RK_POLNR")
    insured = risks.join(table(legacy_dir, "NRPERS"), left_on="RK_PERNR", right_on="PS_PERNR")
    return insured.with_columns(pl.col("RK_TARKEY").str.slice(*span).alias(part) for part, span in TARIFF_KEY.items())


def tariffs(legacy_dir, policies: pl.DataFrame) -> pl.DataFrame:
    """`policies` with the parameters that are valid on their application date PH_APPDT.

    - CG_*: the charges of the tariff family and generation (NRCHRG)
    - EC_RATE: the entry charge of the broker tier (NRENTC)
    - IL_RATE: the yearly growth rate of the offers (NRILLU)

    These tables have no version numbers, so the newest start date wins.
    """
    brokers = policies.join(table(legacy_dir, "NRBROK"), left_on="PH_BRKNR", right_on="BR_BRKNR")
    charges = valid_on(brokers, table(legacy_dir, "NRCHRG"), {"TARFAM": "CG_TARFAM", "TARGEN": "CG_TARGEN"},
                       "PH_APPDT", "CG", newest="VLDFR")
    entry = valid_on(charges, table(legacy_dir, "NRENTC"), {"BR_TIER": "EC_TIER"}, "PH_APPDT", "EC", newest="VLDFR")
    growth = entry.join(table(legacy_dir, "NRILLU"), how="cross")
    return growth.filter(pl.col("PH_APPDT").is_between(pl.col("IL_VLDFR"), pl.col("IL_VLDTO")))
