#!/usr/bin/env python3
import os
"""Turn remits.json into a POSTING PLAN at the claim level:
  * dedupe claims that appear in two mailings (the Zelis virtual-card mailing and the re-issued paper check carry the same EOB),
  * give every claim the best payment reference (physical check > payer check number > Zelis payment id),
  * group claims by (family, reference) -> one 835 per group,
  * hold anything that does not add up (no account number, $0 COB statements, Florida Blue EFTs already electronic, unknown reference).
Writes plan.json."""
import json, re
from collections import defaultdict, OrderedDict
R = json.load(open(os.environ.get("SCANS_DIR", "/home/claude/scans") + "/remits.json"))
def r2(x): return None if x is None else round(x + 1e-9, 2)
def eq(a, b, tol=0.006): return a is not None and b is not None and abs(a - b) < tol
POST_FAMILIES = {"UA", "WN", "AET12", "MUT01", "ECHO", "SIM01", "FLO99", "USAA", "CHAMPVA", "MER01", "BLUE", "TRI00"}   # MER01 + BLUE (paper check / card only - llm_merge maps EFT-paid Blue RAs to family BCBS, which stays held) added 10/5/2026
claims = []   # flattened
for rm in R:
    if rm.get("is_stub") or rm.get("is_physical_check"): continue
    for c in rm["claims"]:
        cc = dict(c); cc["remit"] = rm["id"]; cc["family"] = rm["family"]; cc["pages"] = rm["pages"]
        cc["ref"] = None; cc["ref_source"] = None; cc["ref_date"] = rm.get("date")
        pc = rm.get("physical_check")
        if pc and pc.get("number"): cc["ref"] = pc["number"]; cc["ref_source"] = "physical check"; cc["ref_date"] = pc.get("date") or rm.get("date")
        elif c.get("check_number"): cc["ref"] = c["check_number"]; cc["ref_source"] = "payer check number (EOB)"; cc["ref_date"] = c.get("check_date") or rm.get("date")
        elif rm.get("check_number") and rm["family"] != "UA": cc["ref"] = rm["check_number"]; cc["ref_source"] = "payer check/trace number"
        elif rm.get("check_number") and rm["family"] == "UA": cc["ref"] = rm["check_number"]; cc["ref_source"] = "EOP check number (cover page)"
        elif rm.get("payment_id"): cc["ref"] = rm["payment_id"]; cc["ref_source"] = "Zelis payment id"
        cc["method"] = rm.get("method"); cc["zero_statement"] = bool(rm.get("zero_payment"))
        claims.append(cc)

# ---------------------------------------------------------------- dedupe by (acct, paid, cpt set)
def sig(c):
    # two payers CAN both pay the same visit the same amount (crossover to a Medigap supplement AND a Medicaid plan) -> never merge across families
    return (c["family"], c.get("acct"), r2(c.get("paid")))
groups = OrderedDict()
for c in claims:
    k = sig(c)
    if k in groups:
        g = groups[k]; g["dups"].append({"remit": c["remit"], "pages": c["pages"], "ref": c["ref"], "ref_source": c["ref_source"]})
        # prefer a physical-check reference, then any reference
        rank = {"physical check": 3, "payer check number (EOB)": 2, "payer check/trace number": 2, "EOP check number (cover page)": 1, "Zelis payment id": 1, None: 0}
        if rank.get(c["ref_source"], 0) > rank.get(g["ref_source"], 0): g.update({"ref": c["ref"], "ref_source": c["ref_source"], "ref_date": c["ref_date"]})
        if len(c.get("lines") or []) > len(g.get("lines") or []): g["lines"] = c["lines"]
        for f in ("patient", "member", "icn", "payer_claim", "billed"):
            if not g.get(f) and c.get(f): g[f] = c[f]
    else:
        c["dups"] = []; groups[k] = c
claims = list(groups.values())

# ---------------------------------------------------------------- UA: attach reference-less claims to unlinked physical checks by subset sum
phys = [x for x in R if x.get("is_physical_check") and not x.get("linked_to")]
def subset_sum(items, target):
    """items: [(idx, amount)] -> a subset summing to target (first found, small n)"""
    from itertools import combinations
    for n in range(1, min(6, len(items)) + 1):
        for comb in combinations(items, n):
            if eq(sum(a for _, a in comb), target): return [i for i, _ in comb]
    return None
for pcheck in phys:
    fam = pcheck["family"]; amt = pcheck.get("amount")
    if amt is None: continue
    cand = [(i, c["paid"]) for i, c in enumerate(claims) if c["family"] == fam and c.get("paid") and c["ref_source"] in (None, "Zelis payment id", "EOP check number (cover page)") and not c.get("_taken")]
    hit = subset_sum(cand, amt)
    # a check that prints a Medicare ICN we never saw on an EOB page belongs to claims that are NOT in the pile -> no amount guessing
    if pcheck.get("icn") and not any(c.get("icn") == pcheck["icn"] for c in claims): hit = None
    if hit:
        for i in hit:
            claims[i]["ref"] = pcheck.get("check_number"); claims[i]["ref_source"] = "physical check (matched by amount)"; claims[i]["ref_date"] = pcheck.get("date"); claims[i]["_taken"] = True
        pcheck["linked_by_amount"] = [claims[i]["acct"] for i in hit]

# ---------------------------------------------------------------- decide per claim
plan_groups = OrderedDict(); holds = []
def hold(c, why): holds.append({"acct": c.get("acct"), "patient": c.get("patient"), "family": c["family"], "paid": c.get("paid"), "why": why, "remit": c["remit"], "pages": c["pages"]})
for c in claims:
    fam = c["family"]
    if fam not in POST_FAMILIES: hold(c, "family not posted from paper (%s: electronic ERA already feeds AMD)" % fam); continue
    if c.get("zero_statement") or not c.get("paid"): hold(c, "$0 / COB statement - no money to post (denial handling, not payment posting)"); continue
    if not c.get("acct") or "?" in c["acct"]: hold(c, "AMD account number unreadable on the scan"); continue
    if not c.get("ref"): hold(c, "no check / payment reference found for this claim"); continue
    key = (fam, c["ref"])
    g = plan_groups.setdefault(key, {"family": fam, "ref": c["ref"], "ref_source": c["ref_source"], "date": c.get("ref_date"), "claims": [], "expected_total": None})
    g["claims"].append(c)
# expected totals from the remits / physical checks
for (fam, ref), g in plan_groups.items():
    for x in R:
        if x.get("is_physical_check") and x.get("check_number") == ref: g["expected_total"] = x.get("amount"); g["date"] = x.get("date") or g["date"]
    if g["expected_total"] is None:
        for x in R:
            if not x.get("is_stub") and not x.get("is_physical_check") and (x.get("check_number") == ref or x.get("payment_id") == ref) and x.get("amount"): g["expected_total"] = x["amount"]
    g["claims_total"] = r2(sum(c["paid"] for c in g["claims"]))
    g["complete"] = eq(g["expected_total"], g["claims_total"]) if g["expected_total"] is not None else None
out = {"groups": list(plan_groups.values()), "holds": holds}
json.dump(out, open(os.environ.get("SCANS_DIR", "/home/claude/scans") + "/plan.json", "w"), indent=1, default=str)
if __name__ == "__main__":
    tot = 0.0
    for g in out["groups"]:
        tot += g["claims_total"]
        print("%-8s ref=%-18s %-32s date=%s claims=%d $%.2f expected=%s %s" % (g["family"], g["ref"], g["ref_source"], g["date"], len(g["claims"]), g["claims_total"], g["expected_total"], "OK" if g["complete"] else ("PARTIAL" if g["complete"] is False else "?")))
        for c in g["claims"]:
            print("      %s %-24s $%6.2f  %s  dups=%d" % (c["acct"], (c.get("patient") or "")[:24], c["paid"], [(l.get("dos"), l.get("cpt"), l.get("billed")) for l in c.get("lines", [])], len(c["dups"])))
    print("PLAN: %d groups, %d claims, $%.2f" % (len(out["groups"]), sum(len(g["claims"]) for g in out["groups"]), tot))
    from collections import Counter
    print("HOLDS:", Counter(h["why"] for h in holds))
