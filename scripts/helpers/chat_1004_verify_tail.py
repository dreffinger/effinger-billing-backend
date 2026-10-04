# PLAIN ENGLISH (chat 10/4/2026, before writing the board rows): read-backs + the last two authorized write-offs.
#  reads: Crewe's $5 line; Christensen's TRICARE plan; Rossiter's Sunshine id (chart vs Pam's sheet) via AMD's free 271; Sayer III's Medicare
#         name match (Stedi CMS with the suffix); Sikora's MBI by the corrected first name; Merriwether-Paxton's open balances.
#  writes (William's words on the rows): pat24039 FCC CO-26 residuals -> WOCAID2ND ('the 9/22 residuals are the same money');
#         pat17471755 7/16/2026 99497 denied by Sunshine 7/24 -> WONCS (same ACP-not-a-benefit as the 7/13 line the 9/29 run wrote off).
import sys, os, re, json, time
import chat_1004_board_act as A
from chat_1004_board_act import L, rec, done, DRY
import amd, stedi, elig_amd
amd.login_cached()
def bal(pid, cid):
    for r in A.live(A.chart_rows(pid)):
        if r["id"] == cid: return A.fmt(r)
    return "not live"
L("== verify tail (DRY=%s)" % DRY)
L("crewe 22437857: " + bal("20989", "22437857"))
t = amd.post(amd.msg("getdemographic", "demographics", {"patientid": "pat17477946"}))
for p in re.findall(r'<insplan [^>]*>', t):
    n = re.search(r'subscribernum="([^"]*)"', p).group(1); L("christensen plan: carrier %s num %s len %d seq %s" % (re.search(r'carrier="([^"]*)"', p).group(1), n[:3] + "*" * (len(n) - 3), len(n), re.search(r'sequence="([^"]*)"', p).group(1)))
# Rossiter Sunshine id check
sc, j = amd.check_eligibility("9520651")
txt = json.dumps(j) if not isinstance(j, str) else j
L("rossiter SUN01 ins9520651 271: %s | %s" % (sc, elig_amd.one_line(elig_amd.summarize(txt)) if hasattr(elig_amd, "one_line") else txt[:200]))
# Sayer III name match on Medicare
for last in ("SAYER", "SAYER III"):
    try:
        j = stedi.elig("CMS", "RUPERT", last, os.environ.get("SAYER_DOB8", ""), os.environ.get("SAYER_MBI", ""), "20260325")
        aaa = [(e.get("code"), e.get("description")) for e in (j.get("errors") or [])]
        L("scott CMS last=%r: errors %s plan %s" % (last, aaa, [(b.get("code"), b.get("name")) for b in (j.get("benefitsInformation") or [])[:4]]))
    except Exception as e: L("scott CMS last=%r: %s" % (last, str(e)[:160]))
# Sikora MBI by the corrected first name
try:
    j = stedi.mbi("LORENA", "SIKORA", os.environ.get("SIKORA_DOB8", ""), "FL", "20251113")
    L("sikora MBI lookup (LORENA): %s" % json.dumps(stedi.med_summ(j))[:400])
except Exception as e: L("sikora MBI lookup: %s" % str(e)[:160])
# Merriwether-Paxton open balances
rows = A.chart_rows("17475906"); op = [A.fmt(r) for r in A.live(rows) if float(r.get("insbal") or 0) > 0 or float(r.get("patbal") or 0) > 0]
L("merriwether open (%d): %s" % (len(op), op[:12]))
# Jacobsen pat24039 FCC residuals -> WOCAID2ND (William 10/4 02:58Z)
for r in A.live(A.chart_rows("24039")):
    if float(r.get("insbal") or 0) > 0 and r.get("visit") in ("19453377", "19453357", "19453215", "19453385"):
        L("jacobsen residual: " + A.fmt(r))
        A.writeoff("jacobsen", r["id"], "FLO99", float(r["insbal"]), "WOCAID2ND", "FCC CO-26 N650 'prior to coverage' on the Medicare coinsurance - dual coinsurance FCC will not pay - William 10/4/2026 ('the 9/22 residuals are the same money')")
# Walcott 7/16/2026 99497 -> WONCS
for r in A.live(A.chart_rows("17471755")):
    if r["id"] == "23357945" and float(r.get("insbal") or 0) > 0:
        L("walker 7/16 99497: " + A.fmt(r))
        A.writeoff("walcott", r["id"], "SUN01", float(r["insbal"]), "WONCS", "Sunshine 0.00 7/24/2026 on 99497 - advance care planning not a benefit, same as the 7/13/2026 line written off 9/29 - chat 10/4/2026")
L("== done")
