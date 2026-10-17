"""Step 1 without names or LLM: unary/n-ary inclusion dependencies (what Desbordante's IND mining computes), naive stdlib version."""
import csv, collections as C, glob, os
def rows(path, sep=";"):
    with open(path, newline="", encoding="utf-8") as f:
        r = csv.reader(f, delimiter=sep); h = next(r)
        for x in r: yield dict(zip(h, (v.strip() for v in x)))
dic = {(d["DC_TABLE"], d["DC_COLUMN"]): d for d in rows("legacy/NRDICT.csv")}
cols = {}                                     # "TABLE.COLUMN" -> set of values (key-like columns: C and N(0))
for path in sorted(glob.glob("legacy/NR*.csv")):
    t = os.path.basename(path)[:-4]
    if t in ("NRBOOK", "NRDICT"): continue
    data = list(rows(path))
    for c in data[0]:
        d = dic.get((t, c))
        if d and (d["DC_TYPE"] == "C" or (d["DC_TYPE"] == "N" and d["DC_SCALE"] in ("0", ""))):
            cols[f"{t}.{c}"] = {r[c] for r in data if r.get(c)}
    if t == "NRRISK":                         # generic decomposition of fixed-width codes into character positions
        for i in range(7):
            cols[f"NRRISK.RK_TARKEY[{i + 1}]"] = {r["RK_TARKEY"][i] for r in data}
tgt = list(rows("targets/t0_commission.csv", ","))
cols["t0.policy_id"] = {r["policy_id"] for r in tgt}
cols["t0.due_nr"] = {r["due_nr"] for r in tgt}
def inds(a, min_size=1):
    return sorted(b for b in cols if b != a and len(cols[a]) >= min_size and cols[a] <= cols[b])
print("unary INDs of the target keys:")
print("  t0.policy_id ⊆", inds("t0.policy_id"))
print("  t0.due_nr    ⊆", len(inds("t0.due_nr")), "columns, e.g.", inds("t0.due_nr")[:6])
pairs = {(r["policy_id"], r["due_nr"]) for r in tgt}
prem = {(r["PR_POLNR"], r["PR_DUENR"]) for r in rows("legacy/NRPREM.csv")}
evnt = {(r["EV_POLNR"], r["EV_EVTNR"]) for r in rows("legacy/NREVNT.csv")}
print(f"n-ary IND (policy_id, due_nr) ⊆ (PR_POLNR, PR_DUENR): {pairs <= prem}  | ⊆ (EV_POLNR, EV_EVTNR): {pairs <= evnt} ({len(pairs - evnt)} violations)")
train = {p for p, _ in pairs}
prem_train = {k for k in prem if k[0] in train}; evnt_train = {k for k in evnt if k[0] in train}
print(f"reverse coverage: NRPREM {len(pairs) / len(prem_train):.1%} of {len(prem_train)}, NREVNT {len(pairs) / len(evnt_train):.1%} of {len(evnt_train)}")
print("\njoin path of t0, found by INDs into key columns:")
for a in ("NRPREM.PR_POLNR", "NRPOLH.PH_BRKNR", "NRBROK.BR_TIER", "NRRISK.RK_TARKEY[6]"):
    print(f"  {a:20s} ⊆", [b for b in inds(a, 2) if not b.startswith("t0.")])
print("\nwhich of the equivalent tree features is a key of the parameter table holding the 6 rates (NRCOMR)?")
dom = {"premium type": {"E", "L"}, "product": {"FLKL", "FLFX", "FLSP"}, "freq": {"M", "Q", "H", "J", "E"}, "tier": {"A", "B", "C"}}
for name, values in dom.items():
    print(f"  {name:12s} values ⊆", [b for b in ("NRCOMR.CR_TIER", "NRCOMR.CR_PAYTP") if values <= cols[b]] or "no NRCOMR key column")
