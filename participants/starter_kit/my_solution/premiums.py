"""t3: the premium bookings (PRM), made from the premium items as Neuron's nightly job made them.

From the story (tools/detective/llm/007-t3-story.md): every premium item received (and not reversed later)
buys units. The entry charge of the broker tier (or of an individual agreement while it is valid) stays with
NeuralWave Life; the rest is split between the funds of the allocation, and buys units at the issue price. Units
bought with the premiums of the first PD_INIMON months go to pot 1 (initial units), later ones to pot 2.

The choices stay parameters of `premium_bookings`:
- `day`: the date column whose broker, entry charge and allocation count
- `pot_day`: the date of a premium that decides its pot
- `trade`: the trade date: the first day after the money date with a price of the fund ("price_day"), or the
  first business day after it by a calendar of `calendars` ("TI", "CH", "weekend")
- `price`: the price column of NRFPRC that buys the units
- `entry`: how the entry charge is rounded to the cent: like the split ("split"), cut off ("down"), half
  down ("half_down", an exact half cent is cut off), or as the rest of the invested part, rounded like the split
  ("net"); or a pair (old system, Neuron NG)
- `split`: the amount of a fund as a share of the invested part, rounded ("net"), or the premium times (1 - entry
  rate) times the share with one rounding ("premium")
- `fx_day`: the date of the exchange rate (fund currency per policy currency, `market.rate_on`): a date column,
  or "EVE" the day before the trade date
- `conversion`: how the amount becomes units: "rate" with the rate rounded to millionths (BK_FXRAT), "exact"
  with the cross rate unrounded, or "cents" with the amount first converted to cents of the fund currency
- `rounding`: the cents of the split and the millionths of the units, "half_up" or "down", or a pair
  (old system, Neuron NG) by `era_day` (`eras`)
"""
import polars as pl

from calendars import business_days
from commission import received_items
from eras import by_era, half_up, new_system
from legacy import table, version_on
from market import price_day_after, price_on, rate_on
from money import RATE_UNIT, rounded

YEARS = range(1990, 2027)
ENTRY = "ENT"  # FEETP of an entry charge agreement
UNIT_CENTS = 10_000  # millionths of a unit per cent of a currency unit


def allocations(legacy_dir, rows: pl.DataFrame, day: str) -> pl.DataFrame:
    """One row per row of `rows` and fund of the allocation set valid on the date column `day` (the highest
    version among the valid sets), with AL_FNDID and AL_PCTG."""
    indexed = rows.with_row_index("ROW")
    sets = indexed.select("ROW", "PR_POLNR", day).join(table(legacy_dir, "NRALLO"), left_on="PR_POLNR",
                                                       right_on="AL_POLNR")
    valid = sets.filter(pl.col(day).is_between(pl.col("AL_VLDFR"), pl.col("AL_VLDTO")))
    chosen = valid.filter(pl.col("AL_VRSNR").eq(pl.col("AL_VRSNR").max().over("ROW")))
    return indexed.join(chosen.select("ROW", "AL_FNDID", "AL_PCTG"), on="ROW").drop("ROW")


def entry_rates(legacy_dir, rows: pl.DataFrame, day: str) -> pl.DataFrame:
    """`rows` with ENTRY_RATE: the rate of the broker tier on `day`, or of an entry agreement valid on `day`."""
    policies = version_on(rows, table(legacy_dir, "NRPOLH"), {"PR_POLNR": "PH_POLNR"}, day, "PH_VRSNR")
    brokers = policies.join(table(legacy_dir, "NRBROK"), left_on="PH_BRKNR", right_on="BR_BRKNR", how="left")
    tiers = version_on(brokers, table(legacy_dir, "NRENTC"), {"BR_TIER": "EC_TIER"}, day, "EC_VLDFR")
    agreements = table(legacy_dir, "NRAGRE").filter(pl.col("AG_FEETP").eq(ENTRY))
    agreed = version_on(tiers, agreements, {"PR_POLNR": "AG_POLNR"}, day, "AG_VLDFR")
    return agreed.with_columns(ENTRY_RATE=pl.coalesce("AG_RATE", "EC_RATE"))


def pots(legacy_dir, rows: pl.DataFrame, pot_day: str) -> pl.DataFrame:
    """`rows` with BK_POTCD: 1 when the date column `pot_day` is in the first PD_INIMON months after the start
    date, else 2."""
    products = rows.join(table(legacy_dir, "NRPROD").select("PD_PRDCD", "PD_INIMON"), left_on="PH_PRDCD",
                         right_on="PD_PRDCD")
    initial_end = pl.col("PH_BEGDT").dt.offset_by(pl.format("{}mo", pl.col("PD_INIMON")))
    return products.with_columns(BK_POTCD=pl.when(pl.col(pot_day).lt(initial_end)).then(pl.lit("1")).otherwise(
        pl.lit("2")))


def trade_dates(legacy_dir, rows: pl.DataFrame, trade: str) -> pl.DataFrame:
    """`rows` (one per fund AL_FNDID) with BK_TRDDT, by `trade` (see the module docstring)."""
    match trade:
        case "price_day":
            return price_day_after(legacy_dir, rows, "AL_FNDID", "PR_RCVDT", "BK_TRDDT")
    days = business_days(trade, YEARS).select(PR_RCVDT="DAY", BK_TRDDT="AFTER")
    return rows.join(days, on="PR_RCVDT", how="left")


def entry_charge(entry: str) -> pl.Expr:
    """The entry charge in cents on PR_AMTRC at ENTRY_RATE, rounded by `entry` (see the module docstring)."""
    exact = pl.col("PR_AMTRC").mul(pl.col("ENTRY_RATE"))
    invested = pl.col("PR_AMTRC").mul(pl.lit(RATE_UNIT).sub(pl.col("ENTRY_RATE")))
    modes = {"split": rounded(exact, RATE_UNIT, pl.col("HALF_UP")), "down": exact.floordiv(RATE_UNIT),
             "half_down": rounded(exact.sub(1), RATE_UNIT, True),
             "net": pl.col("PR_AMTRC").sub(rounded(invested, RATE_UNIT, pl.col("HALF_UP")))}
    return by_era(entry, modes.get)


def fund_amount(split: str) -> pl.Expr:
    """The cents of a fund's share AL_PCTG of the premium (see `split` in the module docstring)."""
    invested = pl.col("PR_AMTRC").cast(pl.Int128).mul(pl.lit(RATE_UNIT).sub(pl.col("ENTRY_RATE")))
    shares = {"net": (pl.col("NET").mul(pl.col("AL_PCTG")), RATE_UNIT),
              "premium": (invested.mul(pl.col("AL_PCTG")), pl.lit(pow(RATE_UNIT, 2), pl.Int128))}
    numerator, denominator = shares[split]
    return rounded(numerator, denominator, pl.col("HALF_UP")).cast(pl.Int64)


def units_of(conversion: str) -> pl.Expr:
    """The millionths of units that BK_AMTPC buys at BK_PRICE (see `conversion` in the module docstring)."""
    amount = pl.col("BK_AMTPC").cast(pl.Int128)
    cents = rounded(amount.mul(pl.col("POLICY_FX")), pl.col("FUND_FX"), pl.col("HALF_UP"))
    numerators = {"rate": (amount.mul(pl.col("BK_FXRAT")).mul(UNIT_CENTS), pl.col("BK_PRICE")),
                  "exact": (amount.mul(pl.col("POLICY_FX")).mul(UNIT_CENTS).mul(RATE_UNIT),
                            pl.col("BK_PRICE").mul(pl.col("FUND_FX"))),
                  "cents": (cents.mul(UNIT_CENTS).mul(RATE_UNIT), pl.col("BK_PRICE"))}
    numerator, denominator = numerators[conversion]
    return rounded(numerator, denominator.cast(pl.Int128), pl.col("HALF_UP")).cast(pl.Int64)


def premium_bookings(legacy_dir, day: str = "PR_RCVDT", trade: str = "price_day", price: str = "FP_ASKPR",
                     rounding=("down", "half_up"), era_day: str = "BK_TRDDT", fx_day: str = "EVE",
                     conversion: str = "exact", entry: str = "down", pot_day: str = "PR_RCVDT",
                     split: str = "premium") -> pl.DataFrame:
    """BK_POLNR, BK_EVTNR, BK_FNDID, BK_POTCD, BK_BKTYP, BK_RCVDT, BK_TRDDT, BK_PRCDT, BK_AMTPC (cents), BK_FXRAT,
    BK_PRICE and BK_UNITS (millionths) of every premium booking."""
    charged = pots(legacy_dir, entry_rates(legacy_dir, received_items(legacy_dir), day), pot_day)
    traded = trade_dates(legacy_dir, allocations(legacy_dir, charged, day), trade)
    systems = traded.with_columns(NEW_SYSTEM=new_system(legacy_dir, era_day)).with_columns(
        HALF_UP=by_era(rounding, half_up))
    amounts = systems.with_columns(NET=pl.col("PR_AMTRC").sub(entry_charge(entry))).with_columns(
        BK_AMTPC=fund_amount(split))
    funds = amounts.join(table(legacy_dir, "NRFUND").select("FD_FNDID", "FD_CCY"), left_on="AL_FNDID",
                         right_on="FD_FNDID")
    priced = price_on(legacy_dir, funds, "AL_FNDID", "BK_TRDDT").with_columns(EVE=pl.col("BK_TRDDT").dt.offset_by("-1d"))
    exchanged = rate_on(legacy_dir, rate_on(legacy_dir, priced, "PH_CCY", fx_day, "POLICY_FX"), "FD_CCY", fx_day,
                        "FUND_FX")
    fx = rounded(pl.col("POLICY_FX").mul(RATE_UNIT), pl.col("FUND_FX"), True)
    booked = exchanged.with_columns(BK_FXRAT=fx, BK_PRICE=pl.col(price))
    return booked.select(BK_POLNR="PR_POLNR", BK_EVTNR="PR_EVTNR", BK_FNDID="AL_FNDID", BK_POTCD="BK_POTCD",
                         BK_BKTYP=pl.lit("PRM"), BK_RCVDT="PR_RCVDT", BK_TRDDT="BK_TRDDT", BK_PRCDT="FP_PRCDT",
                         BK_AMTPC="BK_AMTPC", BK_FXRAT="BK_FXRAT", BK_PRICE="BK_PRICE", BK_UNITS=units_of(conversion))
