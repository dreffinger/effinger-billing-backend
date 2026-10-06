#!/usr/bin/env python3
# PLAIN ENGLISH (ERA input - turn the LLM-parsed documents into the paper-remit engine's records)
# Decides: Nothing about posting. Reads SCANS_DIR/llm/*_parse.json (one per batch, written by the parsing agents from the scan text),
#          maps every money document onto the remits.json shape assemble.py produces (one record per remittance: family, method,
#          check_number / payment_id, date, amount, claims with lines and CAS adjustments), links Zelis/ECHO card stubs and physical
#          checks to their remits by payment id / document code / amount, and writes:
#            remits.json           (what plan.py reads; the regex-built remits.json, when present, is merged in - an LLM record wins
#                                   only where the regex record is invalid or missing)
#            correspondence.json   (letters / notices / record requests -> report sheet rows + board rows)
#            vcc_stubs.json        (virtual cards to key in Square, with the physical-check twin warning)
#            llm_merge_report.txt  (what was merged, dropped, held)
# Rules it uses: family names follow billing/paper_remits (UA WN AET12 MUT01 ECHO SIM01 FLO99 USAA CHAMPVA) plus MER01 (Meritain) and
#          BLUE (a Blue plan paying by PAPER CHECK or card - posted under the Blue carrier on the chart); a Blue RA for an EFT/ACH payment
#          or a $0 statement keeps family BCBS and stays held (its 835 arrives on its own; read it for denials). Medicare / Humana / UHC /
#          Centene paper = held. Patient checks (family BANK) are never posted by the engine - they go to William's list.
# Never touches: AMD, Drive, Gmail. Only SCANS_DIR files.
# ---
import os, sys, json, glob, re
D = os.environ.get("SCANS_DIR", "/home/claude/scans")
def r2(x): return None if x is None else round(float(x) + 1e-9, 2)
def eq(a, b, tol=0.011): return a is not None and b is not None and abs(float(a) - float(b)) < tol
def norm_acct(a):
    if not a: return None
    a = str(a).strip().upper().replace(" ", "")
    m = re.match(r"^(\d{8})([A-Z])?$", a)
    if m: return m.group(1) + (m.group(2) or "?")
    b = a[:8].replace("S", "5").replace("O", "0").replace("I", "1").replace("L", "1").replace("Z", "2").replace("B", "8")
    m = re.match(r"^(\d{8})", b)
    if m:
        tail = a[8:9]; return m.group(1) + (tail if re.match(r"[A-Z]", tail or "") else "?")
    return None
FAMILY_MAP = {"UA": "UA", "WN": "WN", "AET12": "AET12", "MUT01": "MUT01", "ECHO": "ECHO", "SIM01": "SIM01", "FLO99": "FLO99", "USAA": "USAA", "CHAMPVA": "CHAMPVA",
              "MERITAIN": "MER01", "MER01": "MER01", "BCBS": "BCBS", "ANTHEM": "BCBS", "BLUE": "BCBS", "MEDICARE": "MEDICARE", "HUMANA": "HUMANA", "UHC": "UHC",
              "BANK": "BANK", "GAINWELL": "GAINWELL", "ZELIS": "ZELIS-VCARD", "OTHER": "OTHER"}
out = []; corr = []; stubs = []; report = []
def L(s): report.append(s); print(s)
docs = []
for f in sorted(glob.glob(D + "/llm/*_parse.json")):
    try: j = json.load(open(f))
    except Exception as e: L("BAD JSON %s: %s" % (f, e)); continue
    for d in j.get("documents", []):
        d["_batch"] = d.get("batch") or j.get("batch"); d["_src"] = os.path.basename(f); docs.append(d)
L("documents: %d from %d files" % (len(docs), len(glob.glob(D + "/llm/*_parse.json"))))
def pages_of(d): return [(str(d["_batch"]), int(p)) for p in (d.get("pages") or [])]
n = 0
for d in docs:
    fam0 = (d.get("family") or "OTHER").upper(); fam = FAMILY_MAP.get(fam0, "OTHER"); typ = (d.get("doc_type") or "other").lower(); method = (d.get("method") or "unknown").lower()
    if typ == "letter" or d.get("correspondence"):
        c = d.get("correspondence") or {}
        corr.append([("%s: %s" % (d.get("payer_name") or fam0, c.get("about") or d.get("notes") or ""))[:200], ("%s | ids %s" % (c.get("from") or "", ", ".join(c.get("identifiers") or [])))[:160],
                     ("%s%s" % (c.get("action_requested") or "", (" | by " + c["deadline"]) if c.get("deadline") else ""))[:300], "%s p%s" % (str(d["_batch"])[-6:], ",".join(str(p) for p in d.get("pages") or []))])
        if not d.get("claims"): continue
    if typ == "other" and not d.get("claims") and not d.get("payment_amount"): continue
    n += 1; rid = "L%03d" % n
    rec = {"id": rid, "family": fam, "payer": d.get("payer_name"), "method": method, "check_number": d.get("check_number"), "payment_id": d.get("payment_id") or d.get("trace"),
           "date": d.get("payment_date"), "amount": r2(d.get("payment_amount")), "claims": [], "pages": pages_of(d), "notes": [], "valid": None, "doc_id": d.get("doc_id"), "source": "llm:" + d["_src"]}
    if typ == "vcard_stub" or (fam == "ZELIS-VCARD"):
        card = d.get("card") or {}
        rec.update({"family": "ZELIS-VCARD", "payer": None, "method": "vcard_stub", "card": card.get("number"), "exp": card.get("exp"), "cvc": card.get("cvc"), "is_stub": True, "doccode": d.get("doccode")})
    elif typ == "check" and not d.get("claims"):
        rec.update({"method": "paper_check", "is_physical_check": True})
        if fam == "BANK": rec["notes"].append("patient payment - William deposits and posts it as a patient payment (never the ERA engine)")
    elif typ == "eft_notice" or method == "eft":
        rec["method"] = "eft"; rec["notes"].append("EFT/ACH payment notice - the 835 should reach the ERA Center on its own; verify, never post from paper")
    if typ == "zero_statement" or (rec["amount"] is not None and rec["amount"] == 0 and d.get("claims")): rec["zero_payment"] = True; rec["method"] = "none"
    # Blues: paper check or card -> postable family BLUE; EFT / $0 -> held BCBS
    if fam == "BCBS" and typ == "remittance" and method in ("check", "vcard") and (rec["amount"] or 0) > 0: rec["family"] = "BLUE"
    if d.get("card") and typ != "vcard_stub": rec.update({"card": (d["card"] or {}).get("number"), "exp": (d["card"] or {}).get("exp"), "cvc": (d["card"] or {}).get("cvc")})
    for c in d.get("claims") or []:
        lines = []
        for l in c.get("lines") or []:
            cas = [{"group": (a.get("group") or "CO").upper(), "code": str(a.get("code") or "45").replace("CO", "").replace("OA", "").replace("PR", "").strip(), "amount": r2(a.get("amount"))} for a in (l.get("adjustments") or []) if a.get("amount") not in (None, 0, 0.0)]
            if l.get("other_payer_paid") and not any(x["code"] == "23" for x in cas): cas.append({"group": "OA", "code": "23", "amount": r2(l["other_payer_paid"])})
            if l.get("patient_resp") and not any(x["group"] == "PR" for x in cas): cas.append({"group": "PR", "code": "2", "amount": r2(l["patient_resp"])})
            lines.append({"dos": l.get("dos"), "cpt": l.get("cpt"), "mod": l.get("mod") or "", "billed": r2(l.get("billed")), "allowed": r2(l.get("allowed")), "paid": r2(l.get("paid")), "cas": cas, "remarks": l.get("remark_codes") or []})
        rec["claims"].append({"acct": norm_acct(c.get("acct") or c.get("acct_raw")), "acct_raw": c.get("acct_raw"), "patient": c.get("patient"), "member": c.get("member_id"), "payer_claim": c.get("payer_claim"), "provider": c.get("provider"),
                              "billed": r2(c.get("claim_billed")), "allowed": r2(c.get("claim_allowed")), "paid": r2(c.get("claim_paid")), "ptresp": r2(c.get("patient_resp")), "other_paid": r2(c.get("other_payer_paid")),
                              "status": c.get("status"), "remarks": c.get("remarks") or [], "lines": lines, "claim_cas": []})
    if d.get("notes"): rec["notes"].append(str(d["notes"])[:300])
    out.append(rec)
# link stubs / checks (payment id, document code sequence, amount)
docs_m = [r for r in out if not r.get("is_stub") and not r.get("is_physical_check")]
for s in [r for r in out if r.get("is_stub")]:
    hit = [m for m in docs_m if s.get("payment_id") and m.get("payment_id") == s["payment_id"]]
    if not hit and s.get("doccode") and s["doccode"].get("seq"): hit = [m for m in docs_m if (m.get("doccode") or {}).get("seq") == s["doccode"]["seq"]]
    if not hit and s.get("amount"): hit = [m for m in docs_m if m["method"] in ("vcard", "unknown", "check") and eq(m.get("amount"), s["amount"]) and m["family"] in ("SIM01", "WN", "AET12", "MUT01", "USAA")]
    if len(hit) == 1:
        m = hit[0]; m["method"] = "vcard"; m["card"] = s.get("card"); m["exp"] = s.get("exp"); m["cvc"] = s.get("cvc"); m["stub_pages"] = s["pages"]; m["stub_amount"] = s.get("amount"); s["linked_to"] = m["id"]
        if not m.get("payment_id"): m["payment_id"] = s.get("payment_id")
for c in [r for r in out if r.get("is_physical_check")]:
    hit = [m for m in docs_m if c.get("check_number") and str(m.get("check_number") or "").lstrip("0") == str(c["check_number"]).lstrip("0")]
    if not hit and c.get("amount") is not None: hit = [m for m in docs_m if eq(m.get("amount"), c["amount"]) and m["family"] in (c["family"], "BLUE", "BCBS") and not m.get("zero_payment")]
    if len(hit) == 1:
        m = hit[0]; m["physical_check"] = {"number": c.get("check_number"), "date": c.get("date"), "amount": c.get("amount"), "pages": c["pages"]}; c["linked_to"] = m["id"]
        if m["family"] == "BCBS": m["family"] = "BLUE"; m["method"] = "check"
# validate
for r in docs_m:
    cl = r["claims"]; paid_sum = r2(sum((c.get("paid") or 0) for c in cl)) if cl else None; r["claims_paid_sum"] = paid_sum; ok = True
    if r.get("amount") is not None and paid_sum is not None and not eq(r["amount"], paid_sum): r["notes"].append("claims paid %.2f != document amount %.2f" % (paid_sum, r["amount"])); ok = False
    for c in cl:
        if not c.get("acct") or "?" in (c.get("acct") or ""): r["notes"].append("unreadable AMD account %r (%s)" % (c.get("acct_raw"), c.get("patient"))); ok = False
        ls = c.get("lines", [])
        if ls and c.get("paid") is not None and all(l.get("paid") is not None for l in ls) and not eq(sum(l["paid"] for l in ls), c["paid"]): r["notes"].append("%s: line paid sum != claim paid" % c.get("acct")); ok = False
    if not cl and (r.get("amount") or 0) > 0 and r["method"] != "eft": r["notes"].append("money document with no claim lines"); ok = False
    r["valid"] = ok
# virtual cards -> keying list
for r in out:
    if r.get("card") and (r.get("is_stub") or r["method"] == "vcard"):
        stubs.append({"card": r["card"], "last4": str(r["card"])[-4:], "exp": r.get("exp"), "cvc_ocr": r.get("cvc"), "zip": None, "amount": r.get("stub_amount") or r.get("amount"), "payment_id": r.get("payment_id"), "family": r["family"], "remit": r.get("linked_to") or r["id"],
                      "claims": len(r.get("claims", [])), "square": None, "batch": r["pages"][0][0] if r["pages"] else "", "page": r["pages"][0][1] if r["pages"] else 0, "mailing": (r.get("doccode") or {}).get("seq"), "warning": None})
# physical-check twins of a card (payer re-issued the expired card as a check): deposit the check, never key both
checks = [r for r in out if r.get("is_physical_check") or r.get("physical_check")]
for s in stubs:
    for c in checks:
        amt = (c.get("physical_check") or {}).get("amount", c.get("amount"))
        if eq(amt, s["amount"]): s["warning"] = "a physical check of the same amount is in the pile (%s) - deposit the check, do not key the card" % ((c.get("physical_check") or {}).get("number") or c.get("check_number"))
# merge with the regex remits.json (if present): keep regex records that validated; add LLM records whose (family, ref) or claim set is not covered
regex_path = D + "/remits_regex.json"
merged = []
if os.path.exists(regex_path):
    R = json.load(open(regex_path)); keep = [r for r in R if not r.get("is_stub") and not r.get("is_physical_check") and r.get("valid")]
    refs = {(r["family"], str(r.get("check_number") or r.get("payment_id") or "")) for r in keep}; accts = {(r["family"], c.get("acct"), r2(c.get("paid"))) for r in keep for c in r["claims"]}
    merged += keep; added = 0
    for r in out:
        if r.get("is_stub") or r.get("is_physical_check"): merged.append(r); continue
        key = (r["family"], str(r.get("check_number") or r.get("payment_id") or ""))
        if key in refs and all((r["family"], c.get("acct"), c.get("paid")) in accts for c in r["claims"]): L("llm %s %s duplicates a valid regex record - dropped" % (r["id"], key)); continue
        merged.append(r); added += 1
    L("merge: %d valid regex records kept, %d llm records added" % (len(keep), added))
else:
    merged = out; L("merge: no regex remits (remits_regex.json absent) - llm records only")
json.dump(merged, open(D + "/remits.json", "w"), indent=1, default=str)
json.dump(corr, open(D + "/correspondence.json", "w"), indent=1)
json.dump(stubs, open(D + "/vcc_stubs.json", "w"), indent=1)
money = [r for r in merged if not r.get("is_stub") and not r.get("is_physical_check") and (r.get("amount") or 0) > 0]
from collections import Counter
L("remits.json: %d records (%d money $%.2f, %d valid); families %s" % (len(merged), len(money), sum(r["amount"] for r in money), sum(1 for r in money if r.get("valid")), Counter(r["family"] for r in merged).most_common()))
L("correspondence: %d items; virtual cards: %d ($%.2f), %d with a check twin" % (len(corr), len(stubs), sum(s["amount"] or 0 for s in stubs), sum(1 for s in stubs if s.get("warning"))))
for r in money: L("  %s %-8s %-7s ref=%s pid=%s %s $%s claims=%d %s %s" % (r["id"], r["family"], r["method"], r.get("check_number"), r.get("payment_id"), r.get("date"), r.get("amount"), len(r["claims"]), "VALID" if r["valid"] else "REVIEW", r["notes"][:2]))
open(D + "/llm_merge_report.txt", "w").write("\n".join(report))
