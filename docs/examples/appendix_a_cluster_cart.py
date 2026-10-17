"""t0 with clustering and a decision tree: regimes, conditions, candidate pool, exact score (stdlib only, read-only)."""
import collections
import csv
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


def rows(path, sep=";"):
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=sep)
        header = next(reader)
        for values in reader:
            yield dict(zip(header, (v.strip() for v in values)))


versions = collections.defaultdict(list)
for r in rows("legacy/NRPOLH.csv"):
    versions[r["PH_POLNR"]].append(r)
for vs in versions.values():
    vs.sort(key=lambda r: int(r["PH_VRSNR"]))
tiers = {r["BR_BRKNR"]: r["BR_TIER"] for r in rows("legacy/NRBROK.csv")}
paytypes = {r["RK_POLNR"]: r["RK_TARKEY"][5] for r in rows("legacy/NRRISK.csv")}
items = {(r["PR_POLNR"], int(r["PR_DUENR"])): r for r in rows("legacy/NRPREM.csv")}
target = {(r["policy_id"], int(r["due_nr"])): Decimal(r["amount"]) for r in rows("targets/t0_commission.csv", ",")}


def tier_on(policy, day):
    """Broker tier of the policy version valid on `day` (highest version wins, fallback: current version)."""
    valid = [v for v in versions[policy] if int(v["PH_VLDFR"]) <= day <= int(v["PH_VLDTO"])]
    return tiers[(valid or versions[policy])[-1]["PH_BRKNR"]]


# Step 1: generic features of each target row, and the relation feature target / PR_AMTRC
features, amount = {}, {}
for key in target:
    item, current = items[key], versions[key[0]][-1]
    amount[key] = Decimal(item["PR_AMTRC"]).scaleb(-2)
    features[key] = {
        "premium type": paytypes[key[0]], "product": current["PH_PRDCD"], "freq": current["PH_FREQ"],
        "currency": current["PH_CCY"], "payment": current["PH_PAYMT"],
        "era": "COBOL" if int(current["PH_APPDT"]) < 1070811 else "NG",
        "tier now": tiers[current["PH_BRKNR"]],
        "tier@DUEDT": tier_on(key[0], int(item["PR_DUEDT"])),
        "tier@RCVDT": tier_on(key[0], int(item["PR_RCVDT"])),
    }

# Step 2: 1-D density clustering of the ratio on large amounts (little rounding noise), then exact assignment
ratios = sorted(float(target[k] / amount[k]) for k in target if amount[k] >= 100)
groups = [[ratios[0]]]
for previous, value in zip(ratios, ratios[1:]):
    if value - previous > 1e-4:
        groups.append([])
    groups[-1].append(value)
dense = [g for g in groups if len(g) >= 20]
centers = [Decimal(str(round(sum(g) / len(g), 4))) for g in dense]
print("step 2  clusters of target/PR_AMTRC:", [(str(c), len(g)) for c, g in zip(centers, dense)],
      "| sparse groups (noise):", len(groups) - len(dense))
label = {}
for key in target:
    fits = [c for c in centers if (amount[key] * c).quantize(CENT, ROUND_HALF_UP) == target[key]]
    label[key] = fits[0] if len(fits) == 1 else "ambiguous" if fits else "noise"
print("        every row assigned to the center that reproduces it exactly:",
      sorted(collections.Counter(str(v) for v in label.values()).items()))


# Step 3: CART decision tree (Gini, binary splits "feature == value") predicting the cluster of each row
def gini(counts):
    n = sum(counts.values())
    return 1 - sum((c / n) ** 2 for c in counts.values()) if n else 0.0


def best_splits(keys, names):
    """All splits with the lowest weighted Gini: several can be exactly equivalent."""
    total = collections.Counter(label[k] for k in keys)
    left = collections.defaultdict(collections.Counter)
    for k in keys:
        for name in names:
            left[name, features[k][name]][label[k]] += 1
    cost = {s: sum(c.values()) * gini(c) + (len(keys) - sum(c.values())) * gini(total - c) for s, c in left.items()}
    low = min(cost.values())
    return [s for s, c in cost.items() if c == low]


def grow(keys, names, path=(), depth=0, leaves=None, verbose=False):
    leaves = [] if leaves is None else leaves
    counts = collections.Counter(label[k] for k in keys)
    if depth == 3 or len(counts) == 1:
        value, n = counts.most_common(1)[0]
        leaves.append((path, value, len(keys), n / len(keys)))
        return leaves
    ties = best_splits(keys, names)
    name, value = ties[0]
    if verbose and len(ties) > 1:
        print(f"        equivalent splits at {' AND '.join(path) or 'the root'}: {ties}")
    grow([k for k in keys if features[k][name] == value], names, path + (f"{name} = {value}",), depth + 1, leaves, verbose)
    grow([k for k in keys if features[k][name] != value], names, path + (f"{name} != {value}",), depth + 1, leaves, verbose)
    return leaves


def matches(key, condition):
    if " != " in condition:
        name, value = condition.split(" != ")
        return features[key][name] != value
    name, value = condition.split(" = ")
    return features[key][name] == value


def predict(leaves, key):
    rate = next(v for path, v, n, p in leaves if all(matches(key, c) for c in path))
    return (amount[key] * rate).quantize(CENT, ROUND_HALF_UP)


def score(leaves):
    return sum(predict(leaves, k) == target[k] for k in target)


known = [k for k in target if label[k] not in ("ambiguous", "noise")]
all_names = list(features[known[0]])
print(f"\nstep 3  decision tree on the cluster label ({len(known)} rows with a unique cluster)")
tree = grow(known, all_names, verbose=True)
for path, value, n, purity in tree:
    print(f"        {' AND '.join(path):70s} -> {value}  ({n} rows, purity {purity:.2%})")

# Step 4/6: the pool of partial candidates (tree paths) translated as is, scored exactly
print(f"\nstep 6  tree translated as is: {score(tree)} / {len(target)}")
print("        residuals:", [(k, str(label[k])) for k in target if predict(tree, k) != target[k]])

# Step 5: one consistent anchor date instead of the mix, each variant scored exactly
print("\nstep 5  variants with a single tier feature:")
for anchor in ("tier now", "tier@DUEDT", "tier@RCVDT"):
    names = [n for n in all_names if not n.startswith("tier") or n == anchor]
    print(f"        only {anchor:10s}: {score(grow(known, names))} / {len(target)}")
