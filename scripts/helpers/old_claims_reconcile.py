# PLAIN ENGLISH (Old-claims disposition - fold the reviewers' verdicts into the list)
# Decides: nothing new. Reads the verification workflows' results (old_claims_workflow_results_<stamp>/*.json: per batch the
#   verifier's and refuter's verdicts and, for every disputed visit, the judge's decision) and applies them to the disposition:
#   a judge's 'pull' or 'change' removes the visit from its package tonight (tier REVIEW, the reason kept on the row); a 'keep'
#   is recorded on the row; a visit flagged by a reviewer but never judged (the judge did not answer) is pulled too - nothing a
#   reviewer doubted is posted or written off without a ruling. Rows that left a package through the classifier fixes keep their
#   new tier. Writes the disposition back, a review-notes file, and prints what was pulled.
# Never touches: AMD.
"""Usage: python3 old_claims_reconcile.py [--stamp 1009]"""
import json, sys, os, glob, collections
a = sys.argv[1:]; STAMP = a[a.index("--stamp") + 1] if "--stamp" in a else "1009"
D = json.load(open("old_claims_disposition_%s.json" % STAMP)); V = {r["vid"]: r for r in D["visits"]}
judged = {}; flagged = collections.defaultdict(list); notes = collections.defaultdict(list); concerns = []; money = []; lists = []
for f in sorted(glob.glob("old_claims_workflow_results_%s/*.json" % STAMP)):
    R = json.load(open(f))
    if isinstance(R, dict) and "lists" in R:        # the audit workflow
        for item in R.get("lists") or []:
            res = item.get("result") or {}
            for e in (res.get("visits") or []):
                if e.get("verdict") != "agree": lists.append(dict(e, file=item.get("file")))
        concerns += ((R.get("rules") or {}).get("concerns") or []); money += ((R.get("money") or {}).get("findings") or [])
        continue
    for batch in (R if isinstance(R, list) else []):
        if not batch: continue
        for fl in batch.get("flagged") or []:
            flagged[fl["vid"]] += fl.get("opinions") or []
        for j in batch.get("judged") or []:
            if j and j.get("vid"): judged[j["vid"]] = j
        if batch.get("verify_notes"): notes[batch["file"]].append("verifier: " + batch["verify_notes"])
        if batch.get("refute_notes"): notes[batch["file"]].append("refuter: " + batch["refute_notes"])
pulled = []; kept = 0; unjudged = []
for vid, r in V.items():
    if not r["pkg"]: continue
    j = judged.get(vid)
    if j and j["decision"] == "keep":
        kept += 1; r["review"] = {"decision": "keep", "reason": j.get("reason", "")[:400]}; continue
    if j and j["decision"] in ("pull", "change"):
        r["review"] = {"decision": j["decision"], "tier": j.get("tier_if_pull", ""), "reason": j.get("reason", "")[:600]}
        pulled.append((vid, r["pkg"], j["decision"], (j.get("tier_if_pull") or "")[:40], (j.get("reason") or "")[:140]))
        r["tier_before_review"] = r["tier"]; r["pkg_before_review"] = r["pkg"]; r["tier"] = "REVIEW"; r["pkg"] = None; r["actions"] = []; r["pay_total"] = 0.0; r["wo_total"] = 0.0
        r["notes"].append("REVIEWER (%s): %s" % (j["decision"], (j.get("reason") or "")[:300])); continue
    if vid in flagged:
        ops = flagged[vid]; r["review"] = {"decision": "flagged-unjudged", "reason": "; ".join("%s %s: %s" % (o.get("who"), o.get("verdict"), (o.get("reason") or "")[:160]) for o in ops)[:600]}
        unjudged.append(vid); pulled.append((vid, r["pkg"], "flagged", "", r["review"]["reason"][:140]))
        r["tier_before_review"] = r["tier"]; r["pkg_before_review"] = r["pkg"]; r["tier"] = "REVIEW"; r["pkg"] = None; r["actions"] = []; r["pay_total"] = 0.0; r["wo_total"] = 0.0
        r["notes"].append("REVIEWER flagged, no ruling: " + r["review"]["reason"][:300])
# money-audit findings: a high-severity finding on a package row pulls it too
for m in money:
    r = V.get(str(m.get("vid")))
    if r and r["pkg"] and m.get("severity") == "high":
        pulled.append((r["vid"], r["pkg"], "money-audit", "", (m.get("issue") or "")[:140]))
        r["tier_before_review"] = r["tier"]; r["pkg_before_review"] = r["pkg"]; r["tier"] = "REVIEW"; r["pkg"] = None; r["actions"] = []; r["pay_total"] = 0.0; r["wo_total"] = 0.0
        r["notes"].append("MONEY AUDIT: " + (m.get("issue") or "")[:300])
def money_(x): return round(float(x or 0) + 1e-9, 2)
pkgs = collections.OrderedDict()
for r in D["visits"]:
    k = r["pkg"] or ("list:" + r["tier"] + (("/" + r["sub"]) if r.get("sub") else "")); s = pkgs.setdefault(k, {"visits": 0, "charges": 0, "open": 0.0, "paid277": 0.0, "pay": 0.0, "wo": 0.0, "carriers": collections.Counter()})
    s["visits"] += 1; s["charges"] += len(r["actions"]); s["open"] = money_(s["open"] + r["open"]); s["paid277"] = money_(s["paid277"] + ((r.get("exact") or {}).get("paid", 0) if r["tier"] == "POST-277" else 0)); s["pay"] = money_(s["pay"] + r["pay_total"]); s["wo"] = money_(s["wo"] + r["wo_total"]); s["carriers"][r["carrier"]] += 1
for s in pkgs.values(): s["carriers"] = dict(s["carriers"].most_common())
D["summary"] = pkgs; D["review"] = {"judged": len(judged), "kept": kept, "pulled": len(pulled), "flagged_unjudged": len(unjudged), "list_findings": len(lists), "rule_concerns": len(concerns), "money_findings": len(money)}
json.dump(D, open("old_claims_disposition_%s.json" % STAMP, "w"), indent=1)
json.dump({"pulled": pulled, "lists": lists, "concerns": concerns, "money": money, "batch_notes": notes, "judged": judged}, open("old_claims_review_notes_%s.json" % STAMP, "w"), indent=1)
print("judged %d (kept %d, pulled %d incl. %d flagged-unjudged); list findings %d; rule concerns %d; money findings %d" % (len(judged), kept, len(pulled), len(unjudged), len(lists), len(concerns), len(money)))
for k, s in sorted(pkgs.items(), key=lambda x: (x[0].startswith("list"), x[0])):
    if not k.startswith("list"): print("  %-6s %4d visits  open $%9.2f  post $%8.2f  wo $%9.2f  %s" % (k, s["visits"], s["open"], s["pay"], s["wo"], s["carriers"]))
for p in pulled[:60]: print("  PULLED v%s %s %s -> %s | %s" % p)
