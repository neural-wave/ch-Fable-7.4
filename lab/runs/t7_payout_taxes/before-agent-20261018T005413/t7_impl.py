"""T7 tax module computation.

Derives tax calculations from Neuron legacy data tables.
Uses the existing fund accounting machinery (FundAccounting) for fund values
so that the German/Swiss/Italian tax rates can be applied correctly.
"""
import csv
import datetime as dt
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from os.path import join

# ── Helpers ──────────────────────────────────────────────────────────────────

def _parse_date(s):
    """Parse date string (YYMMDD/1YYMMDD/YYYYMMDD format) to datetime.date."""
    s = str(s).strip()
    if not s or s == '9999999' or s == '1111231':
        return None
    n = len(s)
    try:
        if n == 6:
            year = 1900 + int(s[:2]) if int(s[:2]) >= 50 else 2000 + int(s[:2])
            return dt.date(year, int(s[2:4]), int(s[4:6]))
        elif n == 7:
            century_prefix = 2000 if s[0] == '1' else 1900
            year = century_prefix + int(s[1:3])
            return dt.date(year, int(s[3:5]), int(s[5:7]))
        elif n == 8:
            return dt.date(int(s[:4]), int(s[4:6]), int(s[6:8]))
        else:
            return None
    except (ValueError, IndexError):
        return None


def _country_at_date(addresses, eff_date):
    """Find the country of residence at the given date."""
    for addr in addresses:
        ad_vl_df = _parse_date(addr.get('AD_VLDFR', ''))
        ad_vl_to = _parse_date(addr.get('AD_VLDTO', ''))
        if ad_vl_df and ad_vl_df <= eff_date:
            if ad_vl_to is None or ad_vl_to >= eff_date:
                return addr.get('AD_CNTRY')
    return None


def _remittance_date(eff_date):
    """Compute the remittance date as the 10th of the month after."""
    if eff_date is None:
        return None
    if eff_date.month == 12:
        return dt.date(eff_date.year + 1, 1, 10)
    return dt.date(eff_date.year, eff_date.month + 1, 10)


# ── Cached FundAccounting ────────────────────────────────────────────────────

_fund_accounting_cache = {}


def _get_fund_accounting(legacy_dir):
    """Return a cached FundAccounting instance for this legacy_dir."""
    if legacy_dir not in _fund_accounting_cache:
        from funds import FundAccounting
        _fund_accounting_cache[legacy_dir] = FundAccounting(legacy_dir)
    return _fund_accounting_cache[legacy_dir]


def _fund_value_at(policy_id, valuation_date, legacy_dir):
    """Compute the fund value of a policy on a given date using FundAccounting.

    Returns (fund_value_in_ccy_cents, total_premiums_paid_in_cents).

    The fund value is the redemption (bid) value of all holdings on the given date.
    The total_premiums is the sum of all paid premiums (PR_STATE=P) in raw cents.
    """
    accounting = _get_fund_accounting(legacy_dir)

    # Replay up to the given date (not including it). We capture units
    # *before* the last booking on that day. For surrender dates the
    # surrender zeroes the units, so we also capture units one day before.
    policy = accounting.replay(policy_id, [valuation_date])

    # If the day had a surrender (all units = 0), get the day-before snapshot
    units_map = policy.snapshots.get(valuation_date, {})
    if sum(units_map.values()) == 0:
        day_before = valuation_date - dt.timedelta(days=1)
        policy_before = accounting.replay(policy_id, [day_before])
        units_map = policy_before.snapshots.get(day_before, {})

    fund_value = Decimal(0)
    for (fund_id, _pot), unit_count in units_map.items():
        if unit_count and unit_count > 0:
            fx = policy.account.prices.fx(fund_id, valuation_date)
            value = unit_count * accounting.market.price(fund_id, valuation_date) * fx
            fund_value += value.quantize(Decimal("0.01")) if hasattr(value, 'quantize') else value

    total_premiums = sum(
        Decimal(str(p["PR_AMTRC"]))
        for p in accounting.premiums.get(policy_id, [])
        if p.get("PR_STATE") == "P" and p.get("PR_RCVDT") is not None
    )

    return fund_value * 100, total_premiums


def _fund_value_at_year(policy_id, year, legacy_dir):
    """Fund value at the last day of a calendar year."""
    day = dt.date(year, 12, 31)
    return _fund_value_at(policy_id, day, legacy_dir)


def _total_premiums_up_to(policy_id, end_date, legacy_dir):
    """Total premiums received up to (and including) the given date."""
    total = Decimal(0)
    for p in _load_table(legacy_dir, 'PREM'):
        if p.get('PR_STATE') == 'P' and p.get('PR_RCVDT'):
            rd = _parse_date(p['PR_RCVDT'])
            if rd and rd <= end_date:
                total += Decimal(str(p['PR_AMTRC']))
    return total


def _tax_rate_for(taxr, tax_tp, eff_date_or_str):
    """Find the valid tax rate for a given type at a given date.

    `eff_date_or_str` may be a datetime.date or a raw CYYMMDD string.
    VLDFR/VLDTO are raw strings: parse them first.
    """
    if isinstance(eff_date_or_str, dt.date):
        eff_date = eff_date_or_str
    else:
        eff_date = _parse_date(eff_date_or_str)
        if eff_date is None:
            return None
    best = None
    best_vl = None  # best VLDFR as parsed date
    for r in taxr:
        if r['TX_TAXTP'] != tax_tp:
            continue
        vl_df = _parse_date(r['TX_VLDFR'])
        vl_to = _parse_date(r['TX_VLDTO'])
        if vl_df is None or vl_df > eff_date:
            continue
        if vl_to is not None and vl_to != dt.date.max and vl_to < eff_date:
            continue
        if vl_df <= eff_date and (vl_to is None or vl_to >= eff_date):
            if best is None or vl_df > best_vl:
                best = r
                best_vl = vl_df
    if best is None:
        return None
    rate = Decimal(best['TX_RATE'].strip()) / Decimal('10000')
    thrsh = None
    thrsh_str = best['TX_THRSH'].strip()
    if thrsh_str:
        thrsh = Decimal(thrsh_str) / Decimal('100')
    return rate, thrsh


def _load_table(legacy_dir, name):
    """Load an NR*.csv table."""
    path = join(legacy_dir, f'NR{name}.csv')
    with open(path, encoding='utf-8') as f:
        return list(csv.DictReader(f, delimiter=';'))


def cents(d):
    """Round a Decimal to the nearest cent (half up)."""
    return d.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


# ── Fund-based gain for taxable base ─────────────────────────────────────────

def _fund_gain(payout, fund_value, total_premiums):
    """Compute the taxable gain using a fund-based approach.

    When the fund has grown (fund_value > total_premiums):
        taxable_base = payout * (fund_value - total_premiums) / fund_value

    This is the Anwartschaftsverhältnis (claim ratio) formula used for German
    life insurance and other unit-linked policies.

    When there is no fund growth, fall back to the simple gain.
    """
    if fund_value > total_premiums and total_premiums > 0:
        penalty_rate = (fund_value - total_premiums) / fund_value
        return payout * penalty_rate
    return max(Decimal(0), payout - total_premiums)


# ── t7_tax_payout ────────────────────────────────────────────────────────────

def t7_tax_payout(legacy_dir) -> dict[tuple[str, int], tuple]:
    """{(policy_id, event_nr): (country, taxable_base, withholding, surcharges, stamp_duty, remittance_date)}

    For each entry in NRTAXB:
    1. Country = policyholder's residence at TB_EFFDT
    2. Taxable base = fund-based gain (for DE/IT) or payout (for CH)
    3. Withholding + surcharges using applicable tax rates
    4. remittance_date = 10th of month after TB_EFFDT

    Tax rules:
      CH + STP: stamp_duty = payout × rate (2.5%)
      CH + VST: withholding = rate × max(0, payout - threshold)
      DE + KST: withholding = rate × taxable_base (25%)
      DE + SOL: surcharges = rate × KST_withholding (5.5%)
      DE + KIS: withholding = rate × taxable_gain (9%) — on full gain
      IT + SOS: withholding = rate × taxable_base (26%)
      IT + BOL: surcharge = rate × fund_value (per mille ~0.0002, annual)
      LU: KIS on taxable_base (9%)
    """
    taxa = _load_table(legacy_dir, 'TAXB')
    hold_map = {h['HD_POLNR'].strip(): h['HD_PERNR'].strip()
                for h in _load_table(legacy_dir, 'HOLD')}
    addr_by_person = defaultdict(list)
    for a in _load_table(legacy_dir, 'ADDR'):
        addr_by_person[a['AD_PERNR'].strip()].append(a)
    taxr = _load_table(legacy_dir, 'TAXR')

    # Pre-index NRBOOK payout by (policy, event) — O(1) lookup
    payouts = defaultdict(Decimal)
    book_path = join(legacy_dir, 'NRBOOK.csv')
    with open(book_path, encoding='utf-8') as f:
        for row in csv.DictReader(f, delimiter=';'):
            pol = row['BK_POLNR'].strip()
            evt = row['BK_EVTNR']
            amt = row['BK_AMTPC']
            if amt and amt.strip():
                payouts[(pol, evt)] += abs(Decimal(amt.strip()) / Decimal('100'))

    # Group NRTAXB by (policy, event)
    entries = defaultdict(list)
    for t in taxa:
        entries[(t['TB_POLNR'].strip(), t['TB_EVTNR'])].append(t)

    result = {}

    for (pol, evt_str), ta_entries in entries.items():
        eff_dt_str = ta_entries[0]['TB_EFFDT']
        eff_dt = _parse_date(eff_dt_str)
        if eff_dt is None:
            continue

        # 1. Get residence country
        per_nr = hold_map.get(pol)
        if per_nr is None:
            continue
        addresses = addr_by_person.get(per_nr, [])
        country = _country_at_date(addresses, eff_dt)
        if country is None:
            continue

        # 2. Get payout (O(1))
        payout = payouts.get((pol, evt_str), Decimal('0'))

        # 3. Taxable base — fund-based for DE/IT/SI, simple for CH
        if country == 'CH':
            # Swiss: tax is on the payout (stamp duty) and on the excess over threshold (VST)
            taxable_base = payout
        else:
            fund_value_raw, total_prem_raw = _fund_value_at(pol, eff_dt, legacy_dir)
            # Convert back to currency units (divide by 100)
            fund_value = fund_value_raw / 100
            total_prem = total_prem_raw / 100
            gain = _fund_gain(payout, fund_value, total_prem)
            taxable_base = gain

        # 4. Tax type flags
        tax_types = {e['TB_TAXTP'] for e in ta_entries}
        has_sos = 'SOS' in tax_types
        has_bol = 'BOL' in tax_types

        # 5. Calculate withholdings & surcharges
        withholding = Decimal('0')
        surcharges = Decimal('0')
        stamp_duty = Decimal('0')

        if country == 'DE':
            for ta in ta_entries:
                ta_eff = _parse_date(ta['TB_EFFDT'])
                if ta_eff is None:
                    continue
                if ta['TB_TAXTP'] == 'KST':
                    info = _tax_rate_for(taxr, 'KST', ta_eff)
                    if info:
                        withholding = info[0] * taxable_base
                elif ta['TB_TAXTP'] == 'SOL':
                    info = _tax_rate_for(taxr, 'SOL', ta_eff)
                    if info:
                        surcharges = info[0] * withholding
            # KIS on gain (for German policies with foreign fund)
            if 'KIS' in tax_types:
                fund_value_raw, total_prem_raw = _fund_value_at(pol, eff_dt, legacy_dir)
                gain = max(Decimal(0), payout - total_prem_raw / 100)
                info = _tax_rate_for(taxr, 'KIS', eff_dt)
                if info:
                    withholding = info[0] * gain

        elif country == 'CH':
            for ta in ta_entries:
                if ta['TB_TAXTP'] == 'VST':
                    ta_eff = _parse_date(ta['TB_EFFDT'])
                    if ta_eff is None:
                        continue
                    info = _tax_rate_for(taxr, 'VST', ta_eff)
                    if info:
                        rate, thrsh = info
                        base = max(Decimal('0'), payout - (thrsh if thrsh else Decimal('5000')))
                        withholding = rate * base
            for ta in ta_entries:
                if ta['TB_TAXTP'] == 'STP':
                    ta_eff = _parse_date(ta['TB_EFFDT'])
                    if ta_eff is None:
                        continue
                    info = _tax_rate_for(taxr, 'STP', ta_eff)
                    if info:
                        stamp_duty = info[0] * payout

        elif country == 'IT':
            if has_sos:
                for ta in ta_entries:
                    ta_eff = _parse_date(ta['TB_EFFDT'])
                    if ta_eff is None:
                        continue
                    if ta['TB_TAXTP'] == 'SOS':
                        info = _tax_rate_for(taxr, 'SOS', ta_eff)
                        if info:
                            withholding = info[0] * taxable_base
            elif has_bol:
                # BOL is an annual tax: rate × fund_value (per mille = divide by 1000)
                fund_value_raw, _ = _fund_value_at(pol, eff_dt, legacy_dir)
                fund_value = fund_value_raw / 100
                bol_rate, _ = _tax_rate_for(taxr, 'BOL', eff_dt)
                if bol_rate is not None:
                    surcharges = bol_rate * fund_value

        elif country == 'LU':
            for ta in ta_entries:
                if ta['TB_TAXTP'] == 'KIS':
                    ta_eff = _parse_date(ta['TB_EFFDT'])
                    if ta_eff is None:
                        continue
                    info = _tax_rate_for(taxr, 'KIS', ta_eff)
                    if info:
                        withholding = info[0] * taxable_base

        rem_dt = _remittance_date(eff_dt)

        result[(pol, int(evt_str))] = (
            country,
            cents(taxable_base),
            cents(withholding),
            cents(surcharges),
            cents(stamp_duty),
            rem_dt,
        )

    return result


# ── t7_tax_annual ────────────────────────────────────────────────────────────

def t7_tax_annual(legacy_dir) -> dict[tuple[str, int], tuple[Decimal, ...]]:
    """{(policy_id, year): (ch_stp, ch_vst, it_sos, it_bol, de_kst, de_sol, de_kis)}

    For each calendar year, aggregates the annuity tax amounts.
    CH: stamp duty on fund_value at year-end; withholding on payout excess over threshold
    IT: annual insurance tax ( BOL per mille on fund_value at year-end)
    DE: withholding on gain (KST + SOL surcharge); also KIS for foreign policies
    LU: KIS on gain
    """
    taxa = _load_table(legacy_dir, 'TAXB')
    hold_map = {h['HD_POLNR'].strip(): h['HD_PERNR'].strip()
                for h in _load_table(legacy_dir, 'HOLD')}
    addr_by_person = defaultdict(list)
    for a in _load_table(legacy_dir, 'ADDR'):
        addr_by_person[a['AD_PERNR'].strip()].append(a)
    taxr = _load_table(legacy_dir, 'TAXR')

    # Group entries by (policy, year)
    entries_by_pol_year = defaultdict(dict)
    for ta in taxa:
        pol = ta['TB_POLNR'].strip()
        eff_dt = _parse_date(ta['TB_EFFDT'])
        if eff_dt is None:
            continue
        year = eff_dt.year
        tax_tp = ta['TB_TAXTP']
        if tax_tp not in entries_by_pol_year[(pol, year)]:
            entries_by_pol_year[(pol, year)][tax_tp] = []
        entries_by_pol_year[(pol, year)][tax_tp].append(ta)

    result = {}

    for (pol, year), type_entries in entries_by_pol_year.items():
        check_date = dt.date(year, 1, 1)
        per_nr = hold_map.get(pol)
        if per_nr is None:
            continue
        addresses = addr_by_person.get(per_nr, [])
        country = _country_at_date(addresses, check_date)
        if country is None:
            continue

        # Tax types present this year
        tax_types = set(type_entries.keys())
        tax_types_by_sub = defaultdict(list, type_entries)  # the bookings are already grouped by tax type

        # Annual (fund_value × rate) taxes
        ch_stp = Decimal('0')
        ch_vst = Decimal('0')
        it_bol = Decimal('0')
        it_sos = Decimal('0')

        if 'STP' in tax_types and country == 'CH':
            fv_raw = _fund_value_at_year(pol, year, legacy_dir)[0]
            fv = fv_raw / 100
            info = _tax_rate_for(taxr, 'STP', dt.date(year, 12, 31))
            if info:
                ch_stp = cents(info[0] * fv)

        if 'SOS' in tax_types and country == 'IT':
            # SOS: surcharge based on fund value
            fv_raw = _fund_value_at_year(pol, year, legacy_dir)[0]
            fv = fv_raw / 100
            for ta in tax_types_by_sub['SOS']:
                ta_eff = _parse_date(ta['TB_EFFDT'])
                if ta_eff is None:
                    continue
                info = _tax_rate_for(taxr, 'SOS', ta_eff)
                if info:
                    it_sos = cents(info[0] * fv)

        if 'BOL' in tax_types and country == 'IT':
            fv_raw = _fund_value_at_year(pol, year, legacy_dir)[0]
            fv = fv_raw / 100
            for ta in tax_types_by_sub['BOL']:
                ta_eff = _parse_date(ta['TB_EFFDT'])
                if ta_eff is None:
                    continue
                info = _tax_rate_for(taxr, 'BOL', ta_eff)
                if info:
                    it_bol = cents(info[0] * fv)

        # Withholding / gain-based taxes
        # KST (German income tax on insurance gains)
        de_kst = de_sol = de_kis = Decimal('0')
        if 'KST' in tax_types and country == 'DE':
            # KST = 25% of taxable gain (from annuity savings = premiums - fund_value)
            premiums_to_date = _total_premiums_up_to(pol, dt.date(year, 12, 31), legacy_dir)
            fv_raw = _fund_value_at_year(pol, year, legacy_dir)[0]
            fv = fv_raw / 100
            gain = _fund_gain(premiums_to_date, fv, premiums_to_date)
            for ta in tax_types_by_sub['KST']:
                ta_eff = _parse_date(ta['TB_EFFDT'])
                if ta_eff is None:
                    continue
                info = _tax_rate_for(taxr, 'KST', ta_eff)
                if info:
                    de_kst = cents(info[0] * gain)

        if 'SOL' in tax_types and country == 'DE':
            for ta in tax_types_by_sub['SOL']:
                ta_eff = _parse_date(ta['TB_EFFDT'])
                if ta_eff is None:
                    continue
                info = _tax_rate_for(taxr, 'SOL', ta_eff)
                if info and de_kst:
                    de_sol = cents(info[0] * de_kst)

        if 'KIS' in tax_types and country == 'DE':
            for ta in tax_types_by_sub['KIS']:
                ta_eff = _parse_date(ta['TB_EFFDT'])
                if ta_eff is None:
                    continue
                info = _tax_rate_for(taxr, 'KIS', ta_eff)
                if info:
                    pre_fund_v_raw, total_prem_raw = _fund_value_at(pol, _parse_date(ta['TB_EFFDT']), legacy_dir)
                    pre_fund_v = pre_fund_v_raw / 100
                    total_prem = total_prem_raw / 100
                    gain = max(Decimal(0), pre_fund_v - total_prem)
                    de_kis = cents(info[0] * gain)

        if country == 'LU' and 'KIS' in tax_types:
            for ta in tax_types_by_sub['KIS']:
                ta_eff = _parse_date(ta['TB_EFFDT'])
                if ta_eff is None:
                    continue
                info = _tax_rate_for(taxr, 'KIS', ta_eff)
                if info:
                    # KIS is typically on gain
                    pre_fund_v_raw, total_prem_raw = _fund_value_at(pol, ta_eff, legacy_dir)
                    gain = max(Decimal(0), pre_fund_v_raw / 100 - total_prem_raw / 100)
                    de_kis = cents(info[0] * gain)

        if any(v != Decimal('0') for v in (ch_stp, ch_vst, de_kst, de_sol, de_kis, it_sos, it_bol)):
            result[(pol, year)] = (
                cents(ch_stp), cents(ch_vst), cents(it_sos), cents(it_bol),
                cents(de_kst), cents(de_sol), cents(de_kis),
            )

    return result
