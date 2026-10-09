# PLAIN ENGLISH (Old-claims disposition - review batches for the verification workflow)
# Decides: nothing. Splits old_claims_disposition_<stamp>.json into small JSON batches (package rows grouped by patient, about
#   10 visits each; plus sampled batches of the no-package lists) so independent reviewers can check every proposed posting and
#   write-off against the chart facts and William's rules. Writes old_claims_batches/<stamp>/pkg_NN.json and list_NN.json.
# Never touches: AMD.
"""Usage: python3 old_claims_batches.py [--stamp 1009] [--per 10] [--list-sample 160]"""
import json, sys, os, random, collections, shutil
a = sys.argv[1:]
def opt(n, d=None): return a[a.index(n) + 1] if n in a else d
STAMP = opt("--stamp", "1009"); PER = int(opt("--per", 10)); LS = int(opt("--list-sample", 160)); SUB = opt("--subdir", "")
D = json.load(open("old_claims_disposition_%s.json" % STAMP)); V = D["visits"]
if "--only-vids" in a:   # a second pass over rows that entered a package after the first review (file = JSON list of vids)
    keep = set(json.load(open(opt("--only-vids")))); V = [r for r in V if r["vid"] in keep]
F = {v["vid"]: v for v in json.load(open("old_claims_facts_%s.json" % STAMP))["visits"]}
out = "old_claims_batches/%s%s" % (STAMP, SUB); shutil.rmtree(out, ignore_errors=True); os.makedirs(out)
def slim(r):
    x = {k: r[k] for k in ("vid", "pid", "patient", "carrier", "dos", "age", "open", "patbal", "cpts", "provider", "tier", "sub", "pkg", "wocode", "position", "order", "other_plans", "deceased", "notes", "actions", "pay_total", "wo_total", "facts")}
    x["answer"] = {k: r["answer"][k] for k in ("src", "kind", "action", "paid", "checks", "dates", "detail")}; x["exact"] = r.get("exact"); return x
byp = collections.OrderedDict()
for r in V:
    if r["pkg"]: byp.setdefault(r["pid"], []).append(r)
batches = []; cur = []; n = 0
for pid, rs in byp.items():
    cur.extend(rs)
    if len(cur) >= PER: batches.append(cur); cur = []
if cur: batches.append(cur)
for i, b in enumerate(batches):
    pids = sorted({r["pid"] for r in b})
    json.dump({"batch": "pkg_%02d" % i, "stamp": STAMP, "packages": D["packages"], "charts": {p: (F.get(next(r["vid"] for r in b if r["pid"] == p)) or {}).get("chart") for p in pids},
               "visits": [slim(r) for r in b]}, open("%s/pkg_%02d.json" % (out, i), "w"), indent=1)
rest = [r for r in V if not r["pkg"]]
random.seed(1009); sample = random.sample(rest, min(LS, len(rest)))
# make sure every list tier is represented
for t in sorted({r["tier"] for r in rest}):
    if not any(r["tier"] == t for r in sample): sample += [r for r in rest if r["tier"] == t][:3]
lists = [sample[i:i + 20] for i in range(0, len(sample), 20)]
for i, b in enumerate(lists):
    pids = sorted({r["pid"] for r in b})
    json.dump({"batch": "list_%02d" % i, "stamp": STAMP, "packages": D["packages"], "charts": {p: (F.get(next(r["vid"] for r in b if r["pid"] == p)) or {}).get("chart") for p in pids},
               "visits": [slim(r) for r in b]}, open("%s/list_%02d.json" % (out, i), "w"), indent=1)
json.dump({"pkg": ["%s/pkg_%02d.json" % (out, i) for i in range(len(batches))], "list": ["%s/list_%02d.json" % (out, i) for i in range(len(lists))],
           "summary": D["summary"], "packages": D["packages"]}, open("%s/index.json" % out, "w"), indent=1)
print("package batches: %d (%d visits); list batches: %d (%d sampled of %d)" % (len(batches), sum(len(b) for b in batches), len(lists), len(sample), len(rest)))
