#!/usr/bin/env python3
import os
# PLAIN ENGLISH (CHAMPVA paper EOBs -> plan groups for post_paper.py)
# Decides: Which CHAMPVA EOB payments (EFT, "information only") are NOT in AMD, and builds one plan group per EOB (ref = the EFT
#          trace on the EOB) with per-line amounts taken from the live chart: line paid = the open Medicare coinsurance on that
#          line (capped at the claim's paid), OA-23 = what Medicare paid, CO-45 = the rest (so the engine's WOINS rule adjusts a
#          contractual Medicare never wrote off).  Patient-balance lines are listed for move_to_ins first.
# Never touches: AMD (writes plan.json only).  Usage: build(member_by_pid) from a runtime script; member ids are never written here.
import json, os, collections
D = os.environ.get("SCANS_DIR", "/home/claude/scans") + ""
TRACE = {tuple(k.split("|")): tuple(v) for k, v in json.load(open(D + "/champva_traces.json")).items()}   # {"LAST,FIRST|m/d/yy": [trace, "YYYY-MM-DD"]} - PHI, beside the scans
def batch_dir(page): return next(b for b in os.listdir(D + "/ocr") if b.endswith(page.split(" p")[0]))
def build(member_by_pid=None):
    member_by_pid = member_by_pid or {}
    C = json.load(open(D + "/champva_claims.json")); L = json.load(open(D + "/fb_live.json")); P = json.load(open(D + "/plan.json"))
    groups = collections.OrderedDict(); moves = []
    for c in C:
        if not c.get("paid"): continue
        acct = c.get("acct_norm") or c.get("acct")
        tr = TRACE.get((c["patient"], c["eob_date"]))
        if not tr: print("no trace for", c["patient"], c["eob_date"], acct); continue
        live = L.get(acct) or {}
        if live.get("charges") is None: print("no live data", acct); continue
        ch = [x for x in live["charges"] if x["fee"] > 0]
        lines = []; left = round(c["paid"], 2)
        for x in sorted(ch, key=lambda x: -x["fee"]):
            medicare = round(sum(p["amount"] for p in x["pays"] if p["void"] != "1" and p["carrier"] == "FLO02"), 2)
            openbal = round(x["insbalance"] + x["patbalance"], 2)
            wo_taken = round(sum(w["amount"] for w in x["wos"] if w["void"] != "1"), 2)
            coins = round(x["fee"] - medicare - wo_taken, 2) if wo_taken else None
            want = min(left, openbal) if openbal > 0 else left
            if coins is not None and abs(coins - want) > 0.011 and 0 < coins <= left: want = coins
            pay = round(want, 2); left = round(left - pay, 2)
            co45 = round(x["fee"] - pay - medicare, 2)
            dos = x["dos"][:10]; dos = "%s-%s-%s" % (dos[6:10], dos[0:2], dos[3:5]) if "/" in dos else dos
            cas = ([{"group": "OA", "code": "23", "amount": medicare}] if medicare > 0 else []) + ([{"group": "CO", "code": "45", "amount": co45}] if co45 > 0.004 else [])
            lines.append({"dos": dos, "cpt": x["cpt"], "mod": "", "billed": x["fee"], "allowed": round(x["fee"] - co45, 2), "paid": pay, "cas": cas})
            if x["patbalance"] > 0.004: moves.append((live["pid"], x["cid"], acct, x["patbalance"]))
        if abs(left) > 0.011: print("WARNING allocation left %.2f on %s" % (left, acct))
        g = groups.setdefault(tr[0], {"family": "CHAMPVA", "ref": tr[0], "ref_source": "EFT trace on the CHAMPVA EOB", "date": tr[1], "expected_total": 0.0, "claims": [], "claims_total": 0.0, "complete": True,
                                      "note": "CHAMPVA EOB %s (%s): EFT payments never posted in AMD (no 835 reached the ERA Center); posted from the paper EOB" % (c["eob_date"], c["patient"])})
        g["claims"].append({"acct": acct, "patient": c["patient"], "member": member_by_pid.get(live.get("pid"), ""), "payer_claim": c.get("control"), "plan": None,
                            "billed": round(sum(l["billed"] for l in lines), 2), "paid": round(c["paid"], 2), "lines": lines, "claim_cas": [], "remit": "CHAMPVA-%s" % c["eob_date"], "family": "CHAMPVA",
                            "pages": [[batch_dir(c["page"]), int(c["page"].split(" p")[1])]], "ref": tr[0], "ref_source": "EFT trace", "ref_date": tr[1], "method": "eft", "zero_statement": False, "dups": []})
        g["expected_total"] = round(g["expected_total"] + c["paid"], 2); g["claims_total"] = round(g["claims_total"] + c["paid"], 2)
    existing = {(g["family"], g["ref"]) for g in P["groups"]}; added = 0
    for ref, g in groups.items():
        if ("CHAMPVA", ref) in existing: print("group exists", ref); continue
        P["groups"].append(g); added += 1
    json.dump(P, open(D + "/plan.json", "w"), indent=1); json.dump(moves, open(D + "/champva_moves.json", "w"), indent=1)
    print("added", added, "CHAMPVA groups:", [(g["ref"], g["date"], len(g["claims"]), g["claims_total"]) for g in groups.values()])
    print("patient-balance charges to move first:", moves)
    for g in groups.values():
        for c in g["claims"]: print("  ", g["ref"], c["acct"], c["patient"], c["paid"], [(l["dos"], l["cpt"], l["paid"], [(a["code"], a["amount"]) for a in l["cas"]]) for l in c["lines"]])
    return groups, moves
if __name__ == "__main__": build()
