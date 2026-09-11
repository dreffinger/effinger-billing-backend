# PLAIN ENGLISH (Direct write-offs)
# Decides: Writes off approved visits whose ERA lines are unmatched or gone.
# Rules it uses: Only CPTs in the approved set; balances read live.
# Never touches: Unapproved visits or CPTs.
# ---
"""Direct (non-ERA-linked) insurance write-offs via Payment Entry 'addpayments' — for approved visits whose
ERA lines are unmatched (chargedetailid -1) or already gone.  Proven on Morrow 07/10/2026 (9/3/2026).
Only charges whose proccode maps to the approved CPT set are written off; balances read live.
Usage: python3 wo_direct.py --carrier MCAD --code WOMCAD --visits-file mcad_ccm_writeoff_visits.json [--only id,id] [--dry]"""
import amd, resave, json, re, sys, time
import xml.etree.ElementTree as ET

PCODES = json.load(open("wo_pcodes.json"))          # pcode -> CPT (approved set)
CARRIER_ID = {"MCAD": "car6113"}

def write_off_visit(vid, rows, carrier, code, note):
    cids = sorted({c for r in rows for c in r["chargedetailids"].split(",")})
    pid = rows[0]["patientid"]
    charges = []; total = 0.0; skipped = []; prof = ""
    for cid in cids:
        rt = ET.fromstring(resave.detail(cid))
        vv = rt.find(".//visit"); prof = (vv.get("profile") if vv is not None else "") or prof
        c = [x for x in rt.iter("charge") if x.get("id") == "charge" + cid]
        if not c: skipped.append((cid, "not found")); continue
        c = c[0]
        cpt = PCODES.get(c.get("proccode"))
        bal = float(c.get("insbalance") or 0)
        if not cpt: skipped.append((cid, "cpt %s not approved" % c.get("proccode"))); continue
        if c.get("void") == "1" or bal <= 0: skipped.append((cid, "bal 0")); continue
        total += bal
        charges.append('<charge id="charge%s" allowed="0.00" insportion="%s" patportion="%s" insbalance="%.2f" patbalance="%s" profile="%s">'
                       '<paymentlist><payment amount="0.00" id="" status="B"/></paymentlist>'
                       '<writeofflist><writeoff id="" risk="0" amount="%.2f" code="%s" status="B"/></writeofflist></charge>'
                       % (cid, c.get("insportion") or "%.2f" % bal, c.get("patportion") or "0.00", bal, c.get("patbalance") or "0.00", prof, bal, code))
    if not charges:
        return False, "nothing to write off %s" % skipped, 0.0
    xml = ('<ppmdmsg action="addpayments" class="paymententry" msgtime="%s" useopenedge="1" checkout="0" date="" nocookie="1">'
           '<patient patientid="pat%s" paysource="2" postingmethod="" amount="0.00" paycode="PE" woamount="%.2f" paymethod="10" carrierid="%s" '
           'depositdate="%s" case_note="%s" checknumber="WO-%s" inclstmt="0" postedby="POI0712" batch="">'
           '<unappliedpaymentlist/><unappliedwriteofflist/><chargelist>%s</chargelist></patient></ppmdmsg>'
           % (amd._msgtime(), pid, total, CARRIER_ID[carrier], time.strftime("%m/%d/%Y"), note, carrier, "".join(charges)))
    r = amd.post(xml)
    ok = 'success="1"' in r
    return ok, re.sub(r"\s+", " ", r[:160]) + " skipped=%s" % skipped, total

if __name__ == "__main__":
    a = sys.argv
    carrier = a[a.index("--carrier") + 1] if "--carrier" in a else "MCAD"
    code = a[a.index("--code") + 1] if "--code" in a else "WOMCAD"
    want = set(json.load(open(a[a.index("--visits-file") + 1]))) if "--visits-file" in a else set()
    if "--only" in a: want = set(int(x) for x in a[a.index("--only") + 1].split(","))
    dry = "--dry" in a
    note = "CCM/AWV non-covered by FL Medicaid - approved write-off 9/3/2026"
    unp = json.load(open("unpaid_20260903.json"))
    byv = {}
    for r in unp:
        if r["carriercode"].strip() == carrier and r["visitid"] in want: byv.setdefault(r["visitid"], []).append(r)
    log = open("wo_post.log", "a")
    def L(m): print(m); log.write(m + "\n"); log.flush()
    L("=== wo_direct %s carrier=%s code=%s dry=%s visits=%d (on unpaid list %d) ===" % (time.ctime(), carrier, code, dry, len(want), len(byv)))
    n = 0; tot = 0.0
    for vid, rows in byv.items():
        if dry:
            L("DRY visit %s %s %s $%s charges %s" % (vid, rows[0]["patientname"], rows[0]["dateofservice"][:10], rows[0]["insbalance"], rows[0]["chargedetailids"])); continue
        ok, msg, t = write_off_visit(vid, rows, carrier, code, note)
        L("%s visit %s %s %s -> %s | $%.2f" % ("OK " if ok else "ERR", vid, rows[0]["patientname"], rows[0]["dateofservice"][:10], msg, t))
        if ok: n += 1; tot += t
        time.sleep(0.7)
    L("=== done: %d visits, $%.2f ===" % (n, tot))
