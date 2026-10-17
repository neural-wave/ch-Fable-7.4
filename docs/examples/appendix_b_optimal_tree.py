"""Optimal sparse tree (GOSDT objective: errors, then leaves) by exact DP vs greedy CART, on the t0 cluster labels."""
import collections, csv, itertools, functools
from decimal import Decimal, ROUND_HALF_UP
def rows(path, sep=";"):
    with open(path, newline="", encoding="utf-8") as f:
        r = csv.reader(f, delimiter=sep); h = next(r)
        for x in r: yield dict(zip(h, (v.strip() for v in x)))
versions = collections.defaultdict(list)
for r in rows("legacy/NRPOLH.csv"): versions[r["PH_POLNR"]].append(r)
for vs in versions.values(): vs.sort(key=lambda r: int(r["PH_VRSNR"]))
tiers = {r["BR_BRKNR"]: r["BR_TIER"] for r in rows("legacy/NRBROK.csv")}
paytypes = {r["RK_POLNR"]: r["RK_TARKEY"][5] for r in rows("legacy/NRRISK.csv")}
items = {(r["PR_POLNR"], int(r["PR_DUENR"])): r for r in rows("legacy/NRPREM.csv")}
target = {(r["policy_id"], int(r["due_nr"])): Decimal(r["amount"]) for r in rows("targets/t0_commission.csv", ",")}
def tier_on(p, d):
    ok = [v for v in versions[p] if int(v["PH_VLDFR"]) <= d <= int(v["PH_VLDTO"])]
    return tiers[(ok or versions[p])[-1]["PH_BRKNR"]]
CENTERS = [Decimal(c) for c in ("0.005", "0.01", "0.015", "0.02", "0.03", "0.04")]
FEATS = ["premium type", "product", "freq", "currency", "payment", "era", "tier now", "tier@DUEDT", "tier@RCVDT"]
data = collections.defaultdict(collections.Counter)          # unique feature vector -> label counts
for k, t in target.items():
    it, cur = items[k], versions[k[0]][-1]
    a = Decimal(it["PR_AMTRC"]).scaleb(-2)
    fits = [c for c in CENTERS if (a * c).quantize(Decimal("0.01"), ROUND_HALF_UP) == t]
    if len(fits) != 1: continue                                  # noise rows are left out, as in the pipeline
    vec = (paytypes[k[0]], cur["PH_PRDCD"], cur["PH_FREQ"], cur["PH_CCY"], cur["PH_PAYMT"],
           "COBOL" if int(cur["PH_APPDT"]) < 1070811 else "NG", tiers[cur["PH_BRKNR"]],
           tier_on(k[0], int(it["PR_DUEDT"])), tier_on(k[0], int(it["PR_RCVDT"])))
    data[vec][fits[0]] += 1
U = list(data)
print(f"rows {sum(sum(c.values()) for c in data.values())} -> {len(U)} unique feature vectors (GOSDT works on binarized, deduplicated data)")
print("unique vectors with more than one label (would need a new feature):", sum(1 for v in U if len(data[v]) > 1))
literals = [(i, v) for i, f in enumerate(FEATS) for v in sorted({u[i] for u in U})]
lit_mask = {l: sum(1 << j for j, u in enumerate(U) if u[l[0]] == l[1]) for l in literals}
FULL = (1 << len(U)) - 1
@functools.lru_cache(maxsize=None)
def leaf(mask):
    cnt = collections.Counter()
    m = mask
    while m:
        b = m & -m; cnt.update(data[U[b.bit_length() - 1]]); m ^= b
    return sum(cnt.values()) - max(cnt.values())                 # misclassified rows if this subset is one leaf
def solve(mask, depth, lits):
    """Lexicographic optimum (errors, leaves) and number of optimal trees, over splits on the allowed literals."""
    best = (leaf(mask), 1); count = 1
    if depth == 0 or best[0] == 0:
        return best, count
    for l in lits:
        left = mask & lit_mask[l]; right = mask & ~lit_mask[l]
        if not left or not right: continue
        (el, ll), cl = solve_c(left, depth - 1, lits); (er, lr), cr = solve_c(right, depth - 1, lits)
        cand = (el + er, ll + lr)
        if cand < best: best, count = cand, cl * cr
        elif cand == best: count += cl * cr
    return best, count
memo = {}
def solve_c(mask, depth, lits):
    key = (mask, depth, lits)
    if key not in memo: memo[key] = solve(mask, depth, lits)
    return memo[key]
all_lits = tuple(literals)
(err, nleaves), n_opt = solve_c(FULL, 3, all_lits)
print(f"\noptimal sparse tree, depth <= 3, all {len(FEATS)} features: errors {err}, leaves {nleaves}, "
      f"number of optimal trees (split orderings included) {n_opt}")
print("\nsmallest feature sets that reach the same optimum (errors, leaves):")
for size in (1, 2, 3):
    found = []
    for fs in itertools.combinations(range(len(FEATS)), size):
        lits = tuple(l for l in literals if l[0] in fs)
        res, _ = solve_c(FULL, 3, lits)
        if res == (err, nleaves): found.append([FEATS[i] for i in fs])
    print(f"  size {size}: {found if found else 'none'}")
    if found: break
for fs in (["tier now", "premium type"], ["tier@DUEDT", "premium type"], ["tier@RCVDT", "premium type"]):
    lits = tuple(l for l in literals if FEATS[l[0]] in fs)
    (e, n), _ = solve_c(FULL, 3, lits)
    print(f"  only {fs}: errors {e}, leaves {n}")
