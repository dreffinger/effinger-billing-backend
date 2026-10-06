#!/usr/bin/env python3
import os
"""Assemble the extracted pages into PAYMENT events (money) with their CLAIM lines, validate the arithmetic, and
write remits.json (one entry per payer remittance) + review.json (anything that did not add up).
Linking rules:
  * Zelis mailings share a document code (jcode + [seq]); pages of one mailing = one remittance whatever batch they landed in.
  * United American: EOP cover (check number, total) + detail pages that follow it in scan order until the next cover;
    the physical check matches by amount + Medicare ICN (the check prints 'Claim#: <ICN>').
  * Aetna SSI / Simply / WN / MoO / ECHO: the remit pages carry their own payment id / check number / trace.
  * FCC: check number + date + amount on every remit page; zero-payment statements carry a statement date.
  * Florida Blue: Check/EFT number on the cover, claims on the following pages.
"""
import json, re, sys
from collections import defaultdict, OrderedDict
EX = json.load(open(os.environ.get("SCANS_DIR", "/home/claude/scans") + "/extracted.json"))
PG = {(p["batch"], p["page"]): p for p in json.load(open(os.environ.get("SCANS_DIR", "/home/claude/scans") + "/pages.json"))}
def key(r): return (r["batch"], r["page"])
def r2(x): return None if x is None else round(x + 1e-9, 2)
def eq(a, b, tol=0.011): return a is not None and b is not None and abs(a - b) < tol
BATCH_ORDER = sorted({r["batch"] for r in EX})

remits = []      # {id, family, payer, method, check_number, payment_id, date, amount, claims:[...], pages:[...], notes:[...], valid}
review = []
def new_remit(**kw):
    r = {"id": None, "family": None, "payer": None, "method": None, "check_number": None, "payment_id": None, "date": None, "amount": None,
         "claims": [], "pages": [], "notes": [], "valid": None}
    r.update(kw); remits.append(r); return r

# ---------------------------------------------------------------- 1. Zelis document codes: group pages by (jcode, seq)
bycode = defaultdict(list)
for r in EX:
    dc = r.get("doccode")
    if dc and dc.get("seq"):
        bycode[(dc.get("jcode") or "?", dc["seq"])].append(r)

# ---------------------------------------------------------------- 2. walk each batch in scan order and build remits
def ua_claim_norm(c):
    lines = []
    for l in c.get("lines", []):
        lines.append({"dos": l["dos"], "cpt": l["cpt"], "mod": l.get("mod") or "", "billed": l["billed"], "allowed": l["allowed"], "paid": None,
                      "cas": [{"group": "CO", "code": "45", "amount": l["adj"]}] if l.get("adj") else []})
    tot = c.get("totals") or {}
    return {"acct": c.get("acct"), "patient": c.get("patient"), "icn": c.get("icn"), "member": c.get("policy"), "mbi": c.get("mbi"),
            "billed": tot.get("billed"), "allowed": tot.get("allowed"), "paid": tot.get("paid"), "ptresp": tot.get("ptresp"),
            "claim_cas": [{"group": a["code"][:2], "code": a["code"][2:], "amount": a["amount"]} for a in c.get("claim_adj", [])], "lines": lines}

cur_ua = None
for b in BATCH_ORDER:
    recs = sorted([r for r in EX if r["batch"] == b], key=lambda r: r["page"])
    for r in recs:
        ty = r["type"]
        if ty == "ua_eop_cover":
            p = r["payment"]
            cur_ua = new_remit(family="UA", payer="UNITED AMERICAN INSURANCE CO", method="check", check_number=p.get("check_number"), date=p.get("date") or p.get("date_text"),
                               amount=p.get("amount"), pages=[key(r)], cover=p, doccode=r.get("doccode"))
            cur_ua["claims"] += [ua_claim_norm(c) for c in r.get("claims", [])]
        elif ty == "ua_eob_detail":
            cl = [ua_claim_norm(c) for c in r.get("claims", [])]
            dc = r.get("doccode")
            target = None
            if cur_ua is not None and cur_ua.get("batch_hint") == b: target = cur_ua   # 10/5/2026: the old conditional-expression precedence raised TypeError when a detail page came before any cover
            if cur_ua is not None and cur_ua["pages"] and cur_ua["pages"][-1][0] == b: target = cur_ua
            if target is None:
                target = new_remit(family="UA", payer="UNITED AMERICAN INSURANCE CO", method="check", pages=[], doccode=dc, notes=["detail page without a cover in this batch"])
                cur_ua = target
            target["claims"] += cl; target["pages"].append(key(r))
        elif ty == "aetna_ssi_remit":
            p = r["payment"]
            rm = new_remit(family="AET12", payer=p["payer"], method=("vcard" if "Virtual" in (p.get("modality") or "") else "check"), payment_id=p.get("payment_id"), date=p.get("date"),
                           amount=p.get("amount"), pages=[key(r)], doccode=r.get("doccode"))
            for c in p.get("claims", []):
                lines = [{"dos": l["dos"], "cpt": l["cpt"], "mod": "", "billed": l["billed"], "allowed": None, "paid": l["paid"],
                          "cas": ([{"group": "OA", "code": "23", "amount": l["other_payer"]}] if l.get("other_payer") else []) + ([{"group": "CO", "code": "45", "amount": l["contractual"]}] if l.get("contractual") else [])
                                 + ([{"group": "PR", "code": "2", "amount": l["coins"]}] if l.get("coins") else []) + ([{"group": "PR", "code": "1", "amount": l["deductible"]}] if l.get("deductible") else [])} for l in c.get("lines", [])]
                rm["claims"].append({"acct": c.get("acct"), "patient": c.get("patient"), "member": c.get("member"), "payer_claim": c.get("payer_claim"), "check_number": c.get("check_number"), "check_date": c.get("check_date"),
                                     "billed": sum(l["billed"] or 0 for l in lines) if lines else None, "paid": c.get("claim_paid"), "lines": lines, "claim_cas": []})
                if not rm["check_number"]: rm["check_number"] = c.get("check_number")
        elif ty == "wn_remit":
            p = r["payment"]
            rm = new_remit(family="WN", payer=p["payer"], method=("vcard" if "Virtual" in (p.get("type") or "") else "check"), check_number=p.get("trace"), date=p.get("date"), amount=p.get("amount"),
                           pages=[key(r)], doccode=r.get("doccode"), summary=p.get("summary", []))
        elif ty == "wn_detail":
            # attach to the most recent WN remit
            wn = [x for x in remits if x["family"] == "WN"]
            target = wn[-1] if wn else new_remit(family="WN", payer="WASHINGTON NATIONAL / BANKERS LIFE", method="?", pages=[], notes=["detail without cover"])
            for c in r.get("claims", []):
                lines = [{"dos": l["dos"], "cpt": l["cpt"], "mod": "", "billed": l["billed"], "allowed": l["allowed"], "paid": l["paid"],
                          "cas": ([{"group": "OA", "code": "23", "amount": r2(l["billed"] - l["paid"] - (l.get("ptresp") or 0))}] if l["billed"] and l["paid"] is not None else [])} for l in c.get("lines", [])]
                target["claims"].append({"acct": c.get("acct"), "patient": c.get("patient"), "member": c.get("member"), "payer_claim": c.get("payer_claim"),
                                         "billed": (c.get("totals") or {}).get("billed"), "paid": (c.get("totals") or {}).get("paid"), "lines": lines, "claim_cas": []})
            target["pages"].append(key(r))
        elif ty == "simply_remit":
            p = r["payment"]
            sm = [x for x in remits if x["family"] == "SIM01" and x["pages"] and x["pages"][-1][0] == b and x["pages"][-1][1] == r["page"] - 1 and not p.get("payment_id")]
            if sm: rm = sm[-1]
            else: rm = new_remit(family="SIM01", payer=p["payer"], method="vcard", check_number=p.get("check_number"), payment_id=p.get("payment_id"), date=p.get("date"), amount=p.get("amount"), pages=[], doccode=r.get("doccode"))
            rm["pages"].append(key(r))
            for c in p.get("claims", []):
                tot = c.get("totals") or {}
                lines = [{"dos": l["dos"], "cpt": l["cpt"], "mod": l.get("mod") or "", "billed": l["billed"], "allowed": l["allowed"], "paid": l["paid"],
                          "cas": ([{"group": "OA", "code": "23", "amount": l["other_adj"]}] if l.get("other_adj") else []) + ([{"group": "CO", "code": "45", "amount": l["contractual"]}] if l.get("contractual") else [])} for l in c.get("lines", [])]
                rm["claims"].append({"acct": c.get("acct"), "patient": c.get("patient"), "member": c.get("member"), "payer_claim": c.get("payer_claim"), "plan": c.get("plan"),
                                     "billed": tot.get("billed"), "allowed": tot.get("allowed"), "paid": tot.get("paid"), "contractual": tot.get("contractual"), "other_adj": tot.get("other_adj"), "lines": lines, "claim_cas": []})
        elif ty in ("fcc_remit", "fcc_zero_payment"):
            p = r["payment"]
            k = ("FCC", p.get("check_number") or ("ZERO-" + str(p.get("date"))))
            ex = [x for x in remits if x["family"] == "FLO99" and x.get("_k") == k]
            rm = ex[0] if ex else new_remit(family="FLO99", payer="FLORIDA COMMUNITY CARE", method=("none" if p.get("zero_payment") else "check"), check_number=p.get("check_number"),
                                             date=p.get("date"), amount=(0.0 if p.get("zero_payment") else p.get("amount")), pages=[], _k=k, zero_payment=bool(p.get("zero_payment")))
            if not rm["date"] and p.get("date"): rm["date"] = p["date"]
            rm["pages"].append(key(r))
            for c in p.get("claims", []):
                lines = [{"dos": l["dos"], "cpt": l["cpt"], "mod": l.get("mod") or "", "billed": l["billed"], "allowed": l["allowed"], "paid": l["paid"], "cas": []} for l in c.get("lines", [])]
                rm["claims"].append({"acct": c.get("acct"), "patient": c.get("patient"), "member": c.get("member"), "payer_claim": c.get("payer_claim"), "provider": c.get("provider"),
                                     "billed": (c.get("totals") or {}).get("billed"), "paid": c.get("claim_paid"), "cob_adj": c.get("cob_adj"), "lines": lines, "claim_cas": []})
        elif ty == "bcbs_remit":
            p = r["payment"]
            if p.get("check_number") or p.get("nonpay_ref"):
                rm = new_remit(family="BCBS", payer="FLORIDA BLUE", method=("eft" if p.get("check_number") else "none"), check_number=p.get("check_number") or p.get("nonpay_ref"), date=p.get("date"),
                               amount=p.get("amount") if p.get("check_number") else 0.0, pages=[key(r)])
            else:
                bl = [x for x in remits if x["family"] == "BCBS"]
                rm = bl[-1] if bl else new_remit(family="BCBS", payer="FLORIDA BLUE", method="?", pages=[])
                rm["pages"].append(key(r))
            for c in p.get("claims", []):
                lines = [{"dos": l["dos"], "cpt": l["cpt"], "mod": l.get("mod") or "", "billed": l["billed"], "allowed": l["allowed"], "paid": l["paid"], "cas": []} for l in c.get("lines", [])]
                rm["claims"].append({"acct": c.get("acct"), "patient": c.get("patient"), "member": c.get("member"), "payer_claim": c.get("payer_claim"), "paid": c.get("claim_paid"),
                                     "billed": sum(l["billed"] or 0 for l in lines) if lines else None, "lines": lines, "claim_cas": []})
        elif ty == "champva_eob":
            p = r["payment"]
            rm = new_remit(family="CHAMPVA", payer="CHAMPVA", method=("eft" if p.get("by_eft") else "none"), check_number=p.get("ref"), date=p.get("date"), amount=p.get("amount") or 0.0, pages=[key(r)], info_only=p.get("info_only"))
            for c in p.get("claims", []):
                rm["claims"].append({"acct": c.get("acct"), "patient": c.get("patient"), "payer_claim": c.get("control"), "billed": c.get("billed"), "allowed": c.get("allowed"), "paid": c.get("paid"),
                                     "ohi_paid": c.get("ohi_paid"), "lines": [{"dos": c["dos"], "cpt": c["cpt"], "mod": "", "billed": c["billed"], "allowed": c["allowed"], "paid": c.get("paid"), "cas": []}], "claim_cas": []})
        elif ty in ("moo_remit", "moo_detail"):
            p = r.get("payment") or {}
            mo = [x for x in remits if x["family"] == "MUT01"]
            if ty == "moo_detail" and mo and not p: rm = mo[-1]; rm["pages"].append(key(r))
            else: rm = new_remit(family="MUT01", payer=p.get("payer") or "UNITED OF OMAHA LIFE (MUTUAL OF OMAHA)", method="check", check_number=p.get("ref"), date=p.get("date"), amount=p.get("amount"), pages=[key(r)], doccode=r.get("doccode"), summary=p.get("summary", []))
            for c in r.get("claims", []):
                lines = [{"dos": l["dos"], "cpt": l["cpt"], "mod": l.get("mod") or "", "billed": l["billed"], "allowed": None, "paid": l["paid"],
                          "cas": ([{"group": "OA", "code": "23", "amount": l["other_ins"]}] if l.get("other_ins") else [])} for l in c.get("lines", [])]
                rm["claims"].append({"acct": c.get("acct"), "patient": c.get("patient"), "member": c.get("member"), "payer_claim": c.get("payer_claim"), "billed": sum(l["billed"] or 0 for l in lines) if lines else None,
                                     "paid": r2(sum(l["paid"] or 0 for l in lines)) if lines else None, "lines": lines, "claim_cas": []})
        elif ty == "payment_summary":
            mo = [x for x in remits if x["family"] == "MUT01"]
            if mo: mo[-1]["summary"] += r.get("summary", []); mo[-1]["pages"].append(key(r))
        elif ty == "echo_vcard":
            p = r["payment"]
            rm = new_remit(family="ECHO", payer=p.get("payer"), method="vcard", check_number=p.get("draft"), date=p.get("date"), amount=None, pages=[key(r)], card=p.get("card"), exp=p.get("exp"))
            for c in p.get("claims", []):
                lines = [{"dos": l["dos"], "cpt": l["cpt"], "mod": "", "billed": l["billed"], "allowed": l["allowed"], "paid": l["paid"],
                          "cas": [{"group": "CO", "code": l.get("carc") or "45", "amount": r2((l["billed"] or 0) - (l["paid"] or 0))}]} for l in c.get("lines", [])]
                rm["claims"].append({"acct": c.get("acct"), "patient": c.get("patient"), "member": c.get("policy"), "payer_claim": c.get("payer_claim"), "billed": sum(l["billed"] or 0 for l in lines) if lines else None,
                                     "paid": r2(sum(l["paid"] or 0 for l in lines)) if lines else None, "lines": lines, "claim_cas": []})
            rm["amount"] = r2(sum(c["paid"] or 0 for c in rm["claims"])) if rm["claims"] else None
        elif ty == "check_front":
            p = r["payment"]
            new_remit(family={"UNITED AMERICAN": "UA", "FCC": "FLO99", "USAA": "USAA", "MUTUAL OF OMAHA": "MUT01"}.get(p.get("payer"), p.get("payer")), payer=p.get("payer"), method="paper_check",
                      check_number=p.get("check_number"), date=p.get("date"), amount=p.get("amount"), pages=[key(r)], icn=p.get("icn"), is_physical_check=True, doccode=r.get("doccode"))
        elif ty == "zelis_vcard":
            p = r["payment"]
            new_remit(family="ZELIS-VCARD", payer=None, method="vcard_stub", payment_id=p.get("payment_id"), amount=p.get("amount"), pages=[key(r)], card=p.get("card"), exp=p.get("exp"), cvc=p.get("cvc"), doccode=r.get("doccode"), is_stub=True)

# ---------------------------------------------------------------- 3. link physical checks / vcard stubs to remits
def link():
    stubs = [x for x in remits if x.get("is_stub")]
    checks = [x for x in remits if x.get("is_physical_check")]
    docs = [x for x in remits if not x.get("is_stub") and not x.get("is_physical_check")]
    for s in stubs:
        # by payment id
        hit = [d for d in docs if s.get("payment_id") and d.get("payment_id") == s["payment_id"]]
        if not hit and s.get("doccode") and s["doccode"].get("seq"):
            hit = [d for d in docs if d.get("doccode") and d["doccode"].get("seq") == s["doccode"]["seq"] and (not s["doccode"].get("jcode") or not d["doccode"].get("jcode") or d["doccode"]["jcode"] == s["doccode"]["jcode"])]
        if len(hit) == 1:
            d = hit[0]; d["method"] = "vcard"; d["card"] = s.get("card"); d["exp"] = s.get("exp"); d["cvc"] = s.get("cvc"); d["stub_pages"] = s["pages"]; d["stub_amount"] = s.get("amount"); s["linked_to"] = d["id"]
            if not d.get("payment_id"): d["payment_id"] = s.get("payment_id")
        elif len(hit) > 1: s["notes"].append("ambiguous stub link: %s" % [h["id"] for h in hit])
    for c in checks:
        hit = []
        if c.get("icn"): hit = [d for d in docs if any(cl.get("icn") == c["icn"] for cl in d["claims"])]
        if not hit and c.get("amount") is not None:
            hit = [d for d in docs if d["family"] == c["family"] and eq(d.get("amount"), c["amount"])]
        if len(hit) == 1:
            d = hit[0]; d["physical_check"] = {"number": c.get("check_number"), "date": c.get("date"), "amount": c.get("amount"), "pages": c["pages"]}; c["linked_to"] = d["id"]
        elif len(hit) > 1: c["notes"].append("ambiguous check link (%d candidates)" % len(hit))

# ---------------------------------------------------------------- 4. validate arithmetic per remit
def validate(rm):
    notes = rm["notes"]; ok = True
    cl = rm["claims"]
    if rm.get("is_stub") or rm.get("is_physical_check"): return
    paid_sum = r2(sum((c.get("paid") or 0) for c in cl)) if cl else None
    rm["claims_paid_sum"] = paid_sum
    if rm.get("amount") is not None and paid_sum is not None and not eq(rm["amount"], paid_sum):
        notes.append("claims paid %.2f != remit amount %.2f" % (paid_sum, rm["amount"])); ok = False
    if rm.get("stub_amount") is not None and rm.get("amount") is not None and not eq(rm["stub_amount"], rm["amount"]):
        notes.append("vcard stub %.2f != remit %.2f" % (rm["stub_amount"], rm["amount"])); ok = False
    for c in cl:
        if not c.get("acct") or "?" in (c.get("acct") or ""): notes.append("claim without a clean AMD account number: %s %s" % (c.get("acct"), c.get("patient"))); ok = False
        ls = c.get("lines", [])
        if ls and c.get("billed") is not None and not eq(sum(l["billed"] or 0 for l in ls), c["billed"]): notes.append("%s: line billed sum != claim billed" % c.get("acct")); ok = False
        if ls and all(l.get("paid") is not None for l in ls) and c.get("paid") is not None and not eq(sum(l["paid"] for l in ls), c["paid"]): notes.append("%s: line paid sum != claim paid" % c.get("acct")); ok = False
        # UA: billed - CO45 = allowed; allowed_total - OA23 - OA253 = paid
        if rm["family"] == "UA" and ls:
            for l in ls:
                co = sum(a["amount"] for a in l["cas"])
                if l.get("allowed") is not None and l.get("billed") is not None and not eq(l["billed"] - co, l["allowed"]): notes.append("%s %s: billed-CO45 != allowed" % (c.get("acct"), l["cpt"])); ok = False
            if c.get("allowed") is not None and c.get("paid") is not None:
                ca = sum(a["amount"] for a in c.get("claim_cas", []))
                if not eq(c["allowed"] - ca - (c.get("ptresp") or 0), c["paid"]): notes.append("%s: allowed - claim adj != paid" % c.get("acct")); ok = False
    if not cl and rm.get("amount"): notes.append("money remit with no claim detail parsed"); ok = False
    rm["valid"] = ok

for i, r in enumerate(remits): r["id"] = "R%03d" % (i + 1)
link()
for r in remits: validate(r)
json.dump(remits, open(os.environ.get("SCANS_DIR", "/home/claude/scans") + "/remits.json", "w"), indent=1, default=str)
if __name__ == "__main__":
    from collections import Counter
    print(Counter((r["family"], r["method"]) for r in remits))
    money = [r for r in remits if not r.get("is_stub") and not r.get("is_physical_check") and (r.get("amount") or 0) > 0]
    print("money remits:", len(money), "valid:", sum(1 for r in money if r["valid"]), "total $%.2f" % sum(r["amount"] for r in money))
    for r in remits:
        if r.get("is_stub") or r.get("is_physical_check"):
            if not r.get("linked_to"): print("UNLINKED", r["id"], r["family"], r["method"], r.get("check_number"), r.get("payment_id"), r.get("amount"), r["pages"], r["notes"])
            continue
        print(r["id"], r["family"], r["method"], "chk", r.get("check_number"), "pid", r.get("payment_id"), r.get("date"), "$", r.get("amount"), "claims", len(r["claims"]), "sum", r.get("claims_paid_sum"), "VALID" if r["valid"] else "REVIEW", r["notes"][:3], r["pages"][:3])
