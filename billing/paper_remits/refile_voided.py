#!/usr/bin/env python3
# PLAIN ENGLISH (Re-file paper-remit money whose visit was voided and re-entered)
# Decides: Nothing new. For every register row HOLD "no live charges on the visit" it looks at the same chart for a LIVE charge with the same
#   date of service + CPT (the visit AMD re-created after the original was voided) and writes a second plan (plan_refile.json) whose claims carry the
#   live visit id (+ its sequence letter) so post_paper.py --plan plan_refile.json posts the same EOB lines there under the clean check number.
# Rules it uses: one candidate only - two live charges with the same DOS+CPT on the chart -> stays HOLD for William. Never touches paid lines.
# Usage: SCANS_DIR=/home/claude/scans python3 refile_voided.py [--write]
import os, sys, json, re, datetime
sys.path.insert(0, "/home/claude/unbilled")
import txh
D = os.environ.get("SCANS_DIR", "/home/claude/scans")
P = json.load(open(D + "/plan.json")); REG = json.load(open(D + "/post_register.json"))
def iso(d):
    d = (d or "")[:10]
    if "/" in d: m, dd, y = d.split("/"); return "%s-%s-%s" % (y, m, dd)
    return d
holds = [r for r in REG if r.get("status") == "HOLD" and "no live charges" in str(r.get("note", ""))]
groups = {}
for h in holds:
    g = next((g for g in P["groups"] if g["family"] == h["family"] and g["ref"] == h["ref"]), None)
    c = next((c for c in (g or {}).get("claims", []) if c["acct"] == h["acct"]), None)
    if not g or not c: print("no plan claim for", h["family"], h["ref"], h["acct"]); continue
    pid = str(h["pid"]); el = txh.fetch(pid)
    live = [x.attrib for x in el.iter("charge") if x.get("void") != "1" and float(x.get("fee") or x.get("totalfee") or 0) > 0]
    newlines = []; ok = True; newvid = None
    for l in c.get("lines") or []:
        cands = [x for x in live if iso(x.get("dos")) == iso(l.get("dos")) and (x.get("proccode") or x.get("chgcode")) == l.get("cpt")]
        if len(cands) != 1: print("  %s %s %s %s: %d live candidates - stays HOLD" % (h["acct"], l.get("dos"), l.get("cpt"), pid, len(cands))); ok = False; break
        v = cands[0].get("visit") or cands[0].get("visitid")
        if newvid and v != newvid: print("  %s: lines land on two visits - stays HOLD" % h["acct"]); ok = False; break
        newvid = v; newlines.append(l)
    if not ok or not newvid: continue
    # sequence letter: the live visit's current insorder position for this payer is unknown here - keep the EOB's letter (post_paper matches CLP01[:8] = visit id)
    acct2 = str(newvid) + h["acct"][8:]
    c2 = dict(c); c2["acct"] = acct2; c2["refiled_from"] = h["acct"]; c2["lines"] = newlines
    k = (g["family"], g["ref"])
    if k not in groups: groups[k] = dict(g, claims=[], trn_suffix=(g.get("trn_suffix") or "") + "R", _refile=True)
    groups[k]["claims"].append(c2); print("  %s -> %s (%s, $%.2f)" % (h["acct"], acct2, g["family"], c.get("paid") or 0))
out = {"groups": list(groups.values()), "holds": []}
for g in out["groups"]: g["claims_total"] = round(sum(c.get("paid") or 0 for c in g["claims"]), 2)
print("refile plan: %d groups, %d claims, $%.2f" % (len(out["groups"]), sum(len(g["claims"]) for g in out["groups"]), sum(g["claims_total"] for g in out["groups"])))
if "--write" in sys.argv: json.dump(out, open(D + "/plan_refile.json", "w"), indent=1); print("wrote", D + "/plan_refile.json")
