# PLAIN ENGLISH (Old-claims disposition - the approval cards and the name-free register copy)
# Decides: nothing. Turns old_claims_disposition_<stamp>.json into (1) items.json for approval_submit.py - one Mandatory Approvals
#   card per package letter (A..J and their -dec twins), each naming the exact apply command, the charts/visits/dollars at stake
#   (chart ids only - never a name, member id or date of birth) and the dry-run evidence - and (2) the repo copy of the disposition
#   with every patient name removed (practices/ehpa/registers/old_claims_disposition_<stamp>.json) so the 2-hourly run can apply an
#   approved card from its own container.
# Never touches: AMD, the approvals page, Gmail (approval_submit.py and the session make those calls).
"""Usage: python3 old_claims_cards.py [--stamp 1009] [--repo /home/user/effinger-billing-backend] [--letters A,B,...]"""
import json, sys, os, re, collections
a = sys.argv[1:]
def opt(n, d=None): return a[a.index(n) + 1] if n in a else d
STAMP = opt("--stamp", "1009"); REPO = opt("--repo", "/home/user/effinger-billing-backend")
D = json.load(open("old_claims_disposition_%s.json" % STAMP)); V = D["visits"]; PK = D["packages"]
ONLY = set(opt("--letters", "").split(",")) - {""}
dry = {}
if os.path.exists("old_claims_apply_%s.log" % STAMP):
    for l in open("old_claims_apply_%s.log" % STAMP):
        m = re.match(r"(DRY|DRY-FAIL|SKIP|DRY SEND) (\S+)", l)
        if m: dry[m.group(2)] = m.group(1)
UI = {"POST": "Payment Entry > patient > visit > New payment: carrier = the billed plan, check number + deposit date from the 277, amount = the payer's paid amount; write-off line (WOINS / WOCAID2ND) for the remainder; Save.",
      "WO": "Payment Entry > patient > visit > write-off only: code as on the card (WOINS / WOLATE / WOCAID2ND / WOSMBAL / WOPDEOB), note 'old-claims disposition 10/9/2026'; Save.",
      "SEND": "Claims > the visit > set claim frequency 1 (original), Rebill entire claim to the plan sequence shown; one send per visit."}
items = []; pkgs = collections.OrderedDict()
for r in V:
    if r["pkg"]: pkgs.setdefault(r["pkg"], []).append(r)
for L, rows in pkgs.items():
    if ONLY and L not in ONLY: continue
    base = L.split("-")[0]; kind = "SEND" if base in ("G", "H") else ("POST" if base in ("A", "B", "C") and any(x.get("pay") for r in rows for x in r["actions"]) else "WO")
    charts = sorted({r["pid"] for r in rows}); openv = sum(r["open"] for r in rows); pay = sum(r["pay_total"] for r in rows); wo = sum(r["wo_total"] for r in rows)
    cars = collections.Counter(r["carrier"] for r in rows)
    ndry = sum(1 for r in rows for x in r["actions"] if dry.get(re.sub(r"\D", "", str(x["cid"]))) in ("DRY", "DRY SEND")); nskip = sum(1 for r in rows for x in r["actions"] if dry.get(re.sub(r"\D", "", str(x["cid"]))) == "SKIP")
    what = ("%s%s - %d visits on %d charts (%s), open $%.2f%s%s. Visits: %s" % (PK[base], " - DECEASED-FLAG charts, confirm each DOS is before the date of death first" if L.endswith("-dec") else "",
            len(rows), len(charts), ", ".join("%s %d" % kv for kv in cars.most_common()), openv, (", post $%.2f from the payers' own 277 figures" % pay) if pay else "", (", write off $%.2f" % wo) if wo else "",
            ", ".join("%s/%s %s" % (r["pid"], r["vid"], r["dos"]) for r in rows)))[:3500]
    items.append({"letter": L, "command": "cd /home/claude/unbilled && python3 old_claims_apply.py --live --only %s --stamp %s" % (L, STAMP),
                  "reason": "chat session 10/9/2026 - William: 'do it now just as described' = list for approval first; nothing is posted until this card is approved (not a classifier refusal)",
                  "what": what, "dollars": "$%.2f" % (pay + wo if kind != "SEND" else openv), "ui": UI[kind],
                  "evidence": "dry run %s: %d charge actions verified live (%d skipped as settled/already posted); review page: Old Claims Disposition artifact; facts + 277 answers in old_claims_disposition_%s.json" % (STAMP, ndry, nskip, STAMP),
                  "evidence_file": "/home/claude/unbilled/old_claims_apply_%s.log" % STAMP})
json.dump(items, open("items_old_claims_%s.json" % STAMP, "w"), indent=1)
clean = json.loads(json.dumps(D))
for r in clean["visits"]: r["patient"] = "[name]"
os.makedirs(os.path.join(REPO, "practices", "ehpa", "registers"), exist_ok=True)
json.dump(clean, open(os.path.join(REPO, "practices", "ehpa", "registers", "old_claims_disposition_%s.json" % STAMP), "w"))
print("cards: %d -> items_old_claims_%s.json; register copy written (names removed)" % (len(items), STAMP))
for i in items: print("  %-6s %-9s %s" % (i["letter"], i["dollars"], i["what"][:110]))
