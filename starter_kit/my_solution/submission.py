"""Neuron migration challenge: the functions the checker runs, one per task.

Each function gets the folder `legacy_dir` with the NR*.csv files and returns the calculated values.
Dates are `datetime.date`, amounts are `decimal.Decimal`. Every value is calculated from `legacy_dir`; only
t5 reads target files. The functions wire the tables to the rules of `policies`, `funds` and `taxes`, written
with the helpers of `neuron`. `lab freeze` may rewrite t0 and the first `from neuron import` line.
"""
from funds import FundAccounting
from neuron import add_months, cents, grouped, table, valid
from neuron import differing_keys, policy_years  # kept apart: `lab freeze` rewrites the line above
from policies.codes import has_due_dates
from policies.commission import Commissions
from policies.portfolio import Portfolio
from policies.projection import Projection
from policies.schedule import collection_date, due_dates
from policies.statement import CHARGES, premiums_by_year, statement_years
from policies.surrender import Penalties, surrender_value
from taxes import annual_taxes, payout_taxes

__all__ = ["t0_commission", "t1_next_due_dates", "t2_projected_maturity_value", "t3_surrender_value",
           "t4_annual_statement", "t5_outlier_detection", "t7_tax_payout", "t7_tax_annual"]


def t0_commission(legacy_dir):
    """{(policy_id, due_nr): commission} of the paid premium items of NRPREM (see `Commissions.amounts`).

    amount = PR_AMTRC x NRCOMR.CR_RATE[CR_TIER = BR_TIER@PR_RCVDT, CR_PAYTP = RK_TARKEY[6]], ROUND_HALF_UP.
    """
    return dict(Commissions(legacy_dir).amounts(table(legacy_dir, "NRPREM")))


def t1_next_due_dates(legacy_dir, extract_date):
    """{(policy_id, n): (due_date, collection_date)} for the due dates in the year after `extract_date`, n = 1, 2, ...

    Policies in force and premium paying on the extract date. Direct debits are collected on the next bank
    working day, bank transfers on the due date.
    """
    year_end = add_months(extract_date, 12)
    result = {}
    for policy_id, versions in grouped(table(legacy_dir, "NRPOLH"), "PH_POLNR").items():
        policy = valid(versions, "PH", extract_date)
        if has_due_dates(policy):
            for n, due_date in enumerate(due_dates(policy, extract_date, year_end), start=1):
                result[policy_id, n] = (due_date, collection_date(due_date, policy["PH_PAYMT"]))
    return result


def t2_projected_maturity_value(legacy_dir):
    """{policy_id: maturity_value} of every insured risk, projected with the parameters of the offer."""
    portfolio = Portfolio(legacy_dir)
    illustration_rates = table(legacy_dir, "NRILLU")
    return {policy_id: Projection(portfolio, policy_id, illustration_rates).maturity_value()
            for policy_id in portfolio.risks}


def t3_surrender_value(legacy_dir, valuation_dates):
    """{(policy_id, valuation_date): surrender_value} of the policies started on or before the valuation date.

    policy value = sum of units x bid price x FX per fund and pot, each rounded to the cent;
    surrender value = policy value x (1 - NRSURR penalty of the product scale and the completed policy years).
    """
    accounting, penalties = FundAccounting(legacy_dir), Penalties(legacy_dir)
    result = {}
    for policy_id, versions in accounting.policies.items():
        policy = accounting.replay(policy_id, valuation_dates)
        for valuation_date, units in policy.snapshots.items():
            version = valid(versions, "PH", valuation_date)
            policy_value = sum(policy.account.prices.worth(fund, unit_count, valuation_date)
                               for (fund, _), unit_count in units.items())
            scale = accounting.products[version["PH_PRDCD"]]["PD_SRPSCL"]
            penalty = penalties.rate(scale, policy_years(policy.offer["PH_BEGDT"], valuation_date), valuation_date)
            result[policy_id, valuation_date] = surrender_value(version, policy_value, penalty, valuation_date)
    return result


def t4_annual_statement(legacy_dir):
    """{(policy_id, year): (premiums, entry_charges, admin_fees, management_fees, risk_charges, total_charges)}

    Premiums: the paid NRPREM items by PR_RCVDT; charges: the bookings of the fund accounting (t3) by year.
    """
    accounting = FundAccounting(legacy_dir)
    result = {}
    for policy_id, versions in accounting.policies.items():
        premiums = premiums_by_year(accounting.premiums.get(policy_id, []))
        charges = accounting.replay(policy_id, []).charges
        for year in statement_years(versions):
            amounts = [cents(sum(charges.get((year, charge), []))) for charge in CHARGES]
            result[policy_id, year] = (cents(sum(premiums.get(year, []))), *amounts, sum(amounts))
    return result


def t5_outlier_detection(legacy_dir, targets_dir):
    """{(task, key)} of the values that were changed by hand: the t0 targets that differ from t0_commission.

    `targets_dir` holds the target files of the policies to check, in the format of `targets/`. This is the
    only function that may read target files. Only the keys that t0_commission calculates are compared.
    """
    import scoring  # the official reader of the target files: the checker puts it on the path
    targets = scoring.read_targets(targets_dir, "t0_commission")
    computed = t0_commission(legacy_dir)
    return {("t0_commission", key) for key in differing_keys(computed, targets)}


def t7_tax_payout(legacy_dir):
    """{(policy_id, event_nr): (country, taxable_base, withholding, surcharges, stamp_duty, remittance_date)}"""
    return payout_taxes(legacy_dir)


def t7_tax_annual(legacy_dir):
    """{(policy_id, year): (ch_stp, ch_vst, it_sos, it_bol, de_kst, de_sol, de_kis)}"""
    return annual_taxes(legacy_dir)
