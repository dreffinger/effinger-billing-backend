# PLAIN ENGLISH (9/3 frequency-1 sweep)
# Decides: Every unpaid visit still carrying the 6/9 'corrected claim' flag with no payer ICN gets reset to frequency 1 and rebilled.
# Rules it uses: Your 9/3 order: 'do all rebills as the 1'.
# Never touches: Visits with a payment.
# ---
"""William 9/3/2026 (11:45 PM): 'fix this and do all rebills as the 1 ... and rebill all the claims ... do it now'.
For every unpaid visit carrying the 6/9 corrected-claim flag with no ICN: set resubmissioncode=1 / origrefnum blank
on each charge (updextrainsinfo) and rebill the claim (chargerebill, rebillentireclaim) to its first active sequence.
Skips: visits with any posted non-void payment (settling); patients whose carrier denied PR27/PR200/PR26/PI109
(wrong payer - see audit_pr_transfer.json) for that same carrier.  Order: non-UNI20/BCBS first, then UNI20/BCBS.
Resumable via reset_freq_rebill.log.  Usage: python3 reset_freq_rebill.py [--dry] [--limit N]"""
import amd, resave, json, re, sys, time, collections
import xml.etree.ElementTree as ET
LOG = open("reset_freq_rebill.log", "a")
def L(m): print(m, flush=True); LOG.write(m + "\n"); LOG.flush()
dry = "--dry" in sys.argv
limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else 10**9
done = set()
for line in open("reset_freq_rebill.log"):
    m = re.search(r"(DONE|SKIP) visit (\d+)", line)
    if m: done.add(m.group(2))
for line in open("fix_freq7.log"):
    m = re.search(r"DONE visit (\d+)", line)
    if m: done.add(m.group(1))
unp = json.load(open("unpaid_20260903.json"))
# wrong-payer patients: (patientid, carrier) pairs from the 9/3 audit
wrong = set()
for x in json.load(open("audit_pr_transfer.json")):
    for r in x["reasons"]:
        if r[0] in ("PR27", "PR200", "PR26", "PI109", "PR109", "PR31") and x["dos"][-4:] >= "2025":
            wrong.add((x["patientid"], r[2]))
byv = collections.OrderedDict()
for r in unp:
    if r["correctedclaim"] and not r["icn"]:
        byv.setdefault(r["visitid"], []).append(r)
order = sorted(byv, key=lambda v: (byv[v][0]["carriercode"].strip() in ("UNI20", "BCBS"), byv[v][0]["dateofservice"]))
L("=== reset_freq_rebill %s: %d visits (%d done), wrong-payer pairs %d, dry=%s ===" % (time.ctime(), len(order), len(done), len(wrong), dry))
n = 0; stats = collections.Counter()
for vid in order:
    if str(vid) in done or n >= limit: continue
    rows = byv[vid]; car = rows[0]["carriercode"].strip(); name = rows[0]["patientname"]
    if (rows[0]["patientid"], car) in wrong:
        L("SKIP visit %s %s %s (wrong payer per PR audit - needs new insurance)" % (vid, name, car)); stats["wrongpayer"] += 1; continue
    try:
        cid = rows[0]["chargedetailids"].split(",")[0]
        root = ET.fromstring(resave.detail(cid)); vv = root.find(".//visit")
        charges = [c for c in root.iter("charge") if c.get("void") != "1"]
        if vv is None or not charges:
            L("ERR visit %s: no detail" % vid); stats["err"] += 1; continue
        if any(x.get("void") != "1" and float(x.get("amount") or 0) != 0 for x in root.iter("payment")):
            L("SKIP visit %s %s %s (has posted payment - settling)" % (vid, name, car)); stats["paid"] += 1; continue
        seq = (vv.get("insorder") or "1").split(",")[0]
        if dry:
            L("DRY visit %s %s %s seq %s charges %d" % (vid, name, car, seq, len(charges))); n += 1; continue
        ok = True
        for pc in sorted({c.get("proccode") for c in charges}):
            ext = ('<extins txtChargeCode="%s" resubmissioncode="1" origrefnum="" patsignature="1" emergency="0" epsdt="0" '
                   'payprov="1" employment="0" autoaccident="0" otheraccident="0" pregnant="0" outsidelab="0"/>') % pc
            r = amd.post(amd.msg("updextrainsinfo", "chargeentry", {"visitid": str(vid), "nocookie": "1"}, ext))
            if "Fault" in r:
                L("ERR extins visit %s: %s" % (vid, re.sub(r"\s+", " ", r[:200]))); ok = False; break
        if not ok: stats["err"] += 1; continue
        code, txt = amd.rebill_charge(charges[0].get("id"), seq)
        if code != 204:
            L("ERR rebill visit %s: %s %s" % (vid, code, txt[:150])); stats["err"] += 1; continue
        L("DONE visit %s %s %s seq %s (%d charges) $%.2f" % (vid, name, car, seq, len(charges), sum(x["insbalance"] for x in rows)))
        n += 1; stats["done"] += 1
    except Exception as e:
        L("ERR visit %s: %s" % (vid, str(e)[:150])); stats["err"] += 1; time.sleep(3)
    time.sleep(0.4)
L("=== finished %s: %s ===" % (time.ctime(), dict(stats)))
