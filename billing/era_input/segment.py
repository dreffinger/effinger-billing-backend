#!/usr/bin/env python3
# PLAIN ENGLISH (ERA input - cut each OCR'd scan batch into DOCUMENTS)
# Decides: Nothing about billing. A ScanSnap batch is a stack of unrelated mailings; this groups consecutive pages into one document
#          per remittance / check / letter so a reader (regex parser or an LLM agent) sees one payer's pages at a time.
# Rules it uses: a new document starts at a page that (a) carries a Zelis/ECHO document code with sequence "1 of N" or "Page 1 of N" /
#          "PAGE 1", (b) is a check front or a virtual-card stub after a non-stub page, (c) names a different payer family than the
#          page before, or (d) follows a blank page when the payer changes. Blank / noise pages are dropped. Writes documents.json.
# Never touches: anything but SCANS_DIR/documents.json.
# ---
import os, re, json, glob, sys
D = os.environ.get("SCANS_DIR", "/home/claude/scans")
PAGES = json.load(open(D + "/pages.json"))
PAYER_KEYS = [("MERITAIN", "MERITAIN"), ("PHYSICIANS MUTUAL", "PHYSICIANS MUTUAL"), ("PHYSICIANS LIFE", "PHYSICIANS MUTUAL"), ("FLORIDA COMMUNITY CARE", "FCC"), ("FCCHEALTHPLAN", "FCC"),
              ("UNITED AMERICAN", "UNITED AMERICAN"), ("GLOBE LIFE", "UNITED AMERICAN"), ("WASHINGTON NATIONAL", "WASHINGTON NATIONAL"), ("BANKERS LIFE", "WASHINGTON NATIONAL"),
              ("SENIOR SUPPLEMENTAL", "AETNA SSI"), ("AMERICAN CONTINENTAL", "AETNA SSI"), ("CONTINENTAL LIFE", "AETNA SSI"), ("UNITED OF OMAHA", "MUTUAL OF OMAHA"), ("MUTUAL OF OMAHA", "MUTUAL OF OMAHA"),
              ("SIMPLY", "SIMPLY"), ("CHAMPVA", "CHAMPVA"), ("ANTHEM", "ANTHEM"), ("BLUECROSS", "BLUE"), ("BLUE CROSS", "BLUE"), ("FLORIDA BLUE", "BLUE"), ("STATE EMPLOYEES", "BLUE"),
              ("HUMANA", "HUMANA"), ("USAA", "USAA"), ("MEDICARE", "MEDICARE"), ("WELLCARE", "WELLCARE"), ("OPTUM", "OPTUM"), ("UNITEDHEALTH", "UHC"), ("UNITED HEALTHCARE", "UHC"),
              ("CAPITAL CITY", "BANK CHECK"), ("MEDICAID", "MEDICAID"), ("GAINWELL", "GAINWELL"), ("TRICARE", "TRICARE"), ("CIGNA", "CIGNA"), ("AETNA", "AETNA"), ("ZELIS", "ZELIS"), ("ECHO", "ECHO")]
def payer_of(t):
    u = t.upper()
    for k, fam in PAYER_KEYS:
        if k in u: return fam
    return None
def page_marker(t):
    m = re.search(r"\bPage\s+(\d+)\s+of\s+(\d+)", t, re.I) or re.search(r"\b(\d+)\s+of\s+(\d+)\b", t[:400])
    if m: return int(m.group(1)), int(m.group(2))
    m = re.search(r"^\s*PAGE\s+(\d+)\s*$", t[:200], re.M | re.I)
    if m: return int(m.group(1)), None
    return None
docs = []
for batch in sorted({p["batch"] for p in PAGES}):
    pages = sorted([p for p in PAGES if p["batch"] == batch], key=lambda p: p["page"])
    cur = None; prev_blank = False; prev_payer = None
    for p in pages:
        if p["type"] in ("blank_or_noise", "blank"): prev_blank = True; continue
        t = open(p["file"], errors="ignore").read()
        payer = payer_of(t) or (p.get("payer") or None)
        mk = page_marker(t)
        starts = cur is None
        if mk and mk[0] == 1: starts = True
        if p["type"] in ("check_front", "zelis_vcard") and cur and cur["pages"] and cur["types"][-1] not in ("check_front", "check_back"): starts = True
        if p["type"] == "check_back" and cur and cur["types"][-1] == "check_front": starts = False
        if payer and prev_payer and payer != prev_payer and not (mk and mk[0] > 1): starts = True
        if prev_blank and payer and prev_payer and payer != prev_payer: starts = True
        if starts:
            cur = {"doc_id": "%s_d%02d" % (batch[-6:], len([d for d in docs if d["batch"] == batch]) + 1), "batch": batch, "pages": [], "types": [], "payer": payer, "heads": []}
            docs.append(cur)
        cur["pages"].append(p["page"]); cur["types"].append(p["type"]); cur["heads"].append(p["head"][:80])
        if payer and not cur["payer"]: cur["payer"] = payer
        prev_payer = payer or prev_payer; prev_blank = False
for d in docs:
    d["files"] = ["%s/ocr/%s/p-%s.txt" % (D, d["batch"], ("%02d" % n if len(glob.glob("%s/ocr/%s/p-0*.txt" % (D, d["batch"]))) else str(n))) for n in d["pages"]]
    d["files"] = [f for f in d["files"] if os.path.exists(f)] or [f for n in d["pages"] for f in glob.glob("%s/ocr/%s/p-*%d.txt" % (D, d["batch"], n))]
    d["chars"] = sum(os.path.getsize(f) for f in d["files"])
    d["money_doc"] = any(t in ("check_front", "zelis_vcard", "ua_eop_cover", "ua_eob_detail", "wn_remit", "aetna_ssi_remit", "moo_remit", "simply_remit", "fcc_remit", "fcc_zero_payment", "champva_eob", "bcbs_remit", "medicare_remit", "humana_remit", "va_remit", "eob_generic", "eob_other", "payment_summary") for t in d["types"]) or bool(re.search(r"\$\s?[\d,]+\.\d\d", " ".join(d["heads"])))
json.dump(docs, open(D + "/documents.json", "w"), indent=1)
from collections import Counter
print(len(docs), "documents;", Counter(d["payer"] for d in docs).most_common())
if "--list" in sys.argv:
    for d in docs: print(d["doc_id"], d["payer"], d["pages"], d["types"][:4], d["chars"], "MONEY" if d["money_doc"] else "")
