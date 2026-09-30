#!/usr/bin/env python3
import os
# PLAIN ENGLISH (Florida Blue paper Remittance Advice parser, v2)
# Decides: Nothing. Reads every OCR'd page that is a Florida Blue RA (any batch, whatever classify.py called it) and writes
#          fb_claims_v2.json: one record per claim (RA date, check/EFT, patient, member, AMD account, every service line with
#          charges / allowed / other-carrier paid / copay / coins / deductible / patient resp / paid, remark codes) + the legend.
# Never touches: anything in AMD.
import re, json, os, glob, collections
D = os.environ.get("SCANS_DIR", "/home/claude/scans") + ""; OCR = D + "/ocr"
LINE = re.compile(r"^\s*([A-Z][A-Z0-9]{10,17})\s+(\d{8}[A-Z0-9])\s+(\d\d/\d\d/\d{4})\s+(\d\d/\d\d/\d{4})\s+(99\d{3}|G\d{4}|\d{5})\s+(?:(\d\d)\s+)?(?:(\d\d)\s+)?(\d{4})\s+"
                  r"\$?(-?[\d,]+\.\d\d)\s+\$?(-?[\d,]+\.\d\d)\s+\$?(-?[\d,]+\.\d\d)\s+\$?(-?[\d,]+\.\d\d)\s+\$?(-?[\d,]+\.\d\d)\s+\$?(-?[\d,]+\.\d\d)\s+\$?(-?[\d,]+\.\d\d)\s+\$?(-?[\d,]+\.\d\d)\s*([\d,\. ]*)$")
HDR = re.compile(r"^\s*(\w{5})\s+(WILLIAM L EFFINGER|PAMELA P GARLAND-G)\s+(.+?)\s+([A-Z]{1,4}\d{6,12}|\d{9,12}|R\d{8})\s+\$?(-?[\d,]+\.\d\d)\s*$")
REM = re.compile(r"Remarks/Reasons:\s*(.*)")
REMCODE = re.compile(r"\(\s*\d+\s*\)\s*([A-Z0-9]{4,6})")
LEG = re.compile(r"^\s*[\dlIiJoO,\]\)\|=_]*\s*([A-Z]{4,6})\s+[—_\-:]*\s*(.{8,})$")
CHK = re.compile(r"Check/EFT Number:\s*(\d{6,12})\s+Total Paid:\s*\$?(-?[\d,]+\.\d\d)")
DATE = re.compile(r"\b(\d\d/\d\d/\d{4})\b")
def money(s): return float(s.replace(",", "").replace("$", "")) if s else None
claims = []; legend = {}; pages_used = []
for batch in sorted(os.listdir(OCR)):
    for fn in sorted(glob.glob(os.path.join(OCR, batch, "p-*.txt"))):
        txt = open(fn, errors="ignore").read()
        if "BlueCross" not in txt and "Blue Cross" not in txt and "Remarks/Reasons" not in txt: continue
        if "Remarks/Reasons" not in txt and not LINE.search(txt): continue
        page = "%s p%02d" % (batch[-6:], int(os.path.basename(fn)[2:4]))
        pages_used.append(page)
        m = CHK.search(txt); check, total = (m.group(1), money(m.group(2))) if m else (None, None)
        head = txt[:600]; dm = DATE.findall(head); radate = dm[0] if dm else None
        plan = "State Employees PPO" if "State Employees" in head or "Employees" in head else ("FEP" if "Federal Employee" in head else "Florida Blue")
        cur = None; open_claim = None
        for raw in txt.splitlines():
            line = raw.strip()
            h = HDR.match(line)
            if h:
                cur = {"provider_code": h.group(1), "provider": h.group(2), "patient": h.group(3).strip(), "member": h.group(4), "mpd": money(h.group(5))}; open_claim = None; continue
            l = LINE.match(line)
            if l:
                claimno, acct = l.group(1), l.group(2)
                if open_claim is None or open_claim["claim"] != claimno:
                    open_claim = {"claim": claimno, "acct": acct, "page": page, "ra_date": radate, "check": check, "ra_total_paid": total, "plan": plan,
                                  "lines": [], "remarks": [], **({k: cur[k] for k in ("provider_code", "provider", "patient", "member")} if cur else {"patient": None, "member": None, "provider": None})}
                    claims.append(open_claim)
                open_claim["lines"].append({"dos": l.group(3), "dos_to": l.group(4), "cpt": l.group(5), "mod": l.group(6), "mod2": l.group(7), "units": l.group(8),
                                            "charges": money(l.group(9)), "allowed": money(l.group(10)), "other_carrier": money(l.group(11)), "copay": money(l.group(12)),
                                            "coins": money(l.group(13)), "deductible": money(l.group(14)), "pt_resp": money(l.group(15)), "paid": money(l.group(16)), "remark_refs": l.group(17).strip()})
                continue
            r = REM.search(line)
            if r:
                codes = REMCODE.findall(r.group(1))
                if open_claim is not None: open_claim["remarks"] = codes
                elif claims and claims[-1]["page"] == page and not claims[-1]["remarks"]: claims[-1]["remarks"] = codes
                open_claim = None; continue
            g = LEG.match(line)
            if g and g.group(1) not in ("TOTAL", "PAGE", "CPT", "HCPC", "NPI", "MPD", "SCCF"):
                code, desc = g.group(1), g.group(2).strip()
                if code not in legend or len(desc) > len(legend[code]): legend[code] = desc
for c in claims:
    c["billed"] = round(sum(l["charges"] or 0 for l in c["lines"]), 2); c["paid"] = round(sum(l["paid"] or 0 for l in c["lines"]), 2)
    c["other_carrier"] = round(sum(l["other_carrier"] or 0 for l in c["lines"]), 2); c["pt_resp"] = round(sum(l["pt_resp"] or 0 for l in c["lines"]), 2)
json.dump({"claims": claims, "legend": legend, "pages": pages_used}, open(D + "/fb_claims_v2.json", "w"), indent=1)
print(len(pages_used), "FB pages;", len(claims), "claims;", sum(len(c["lines"]) for c in claims), "lines; paid", round(sum(c["paid"] for c in claims), 2), "billed", round(sum(c["billed"] for c in claims), 2))
print("no patient header:", sum(1 for c in claims if not c.get("patient")))
print(collections.Counter(tuple(sorted(set(c["remarks"]) - {"PPSCH", "PPRCT"})) for c in claims).most_common(40))
print(json.dumps(legend, indent=0))
