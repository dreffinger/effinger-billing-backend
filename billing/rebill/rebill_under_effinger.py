# PLAIN ENGLISH (Rebill Garcia denials under Dr. Effinger)
# Decides: Which Garcia-rendered denials (N290/N767) to re-send with you as rendering provider, and does it without voiding the originals.
# Rules it uses: Your 9/3 call: Medicare/MA with FS modifier, the rest under your NPI. A profile change voids charges, so it recreates them carefully.
# Never touches: Paid visits; TRICARE secondary lines on Medicare-paid visits.
# ---
"""Rebill Garcia-rendered denials (N290 / N767) under Dr. Effinger as rendering provider.
William 9/3/2026: 'rebill the Medicare/MA ones with FS and the rest under my NPI as-is'.
Mechanics (learned on White/Felix 9/2): a profile change via updvisitwithnewcharges makes AMD VOID the
charges and create new ones under the new profile (possibly a new visit id).  Safe only on unpaid charges.
Steps per visit: verify nothing paid -> resave with profile=prof13 (+FS on E/M lines for Medicare/MA payers
once the FS modifier exists in Master Files) -> locate the new charges -> resubmissioncode=1 -> rebill.
Usage: python3 rebill_under_effinger.py [--carrier SUN01,MCAD] [--visits id,id] [--fs mcodeNNN] [--dry]"""
import amd, resave, json, re, sys, time
import xml.etree.ElementTree as ET

EFFINGER = "prof13"
FS_PAYERS = {"FLO02", "HUM01", "UNI20", "TRI05", "AAR01", "UHCMA", "BCBS1"}
NO_FS_CPTS = {"pcode492676", "pcode492677", "pcode492674", "pcode492675", "pcode67716", "pcode67715"}  # CCM / AWV
LOG = open("rebill_effinger.log", "a")
def L(m): print(m); LOG.write(m + "\n"); LOG.flush()

def visit_state(cid):
    rt = ET.fromstring(resave.detail(cid))
    vis = rt.find(".//visit"); pat = rt.find(".//patient")
    charges = [c for c in vis.findall(".//charge") if c.get("void") != "1"]
    paid = any(float(x.get("amount") or 0) != 0 and x.get("void") != "1" for x in rt.iter("payment"))
    return rt, vis, pat, charges, paid

def do_visit(vid, info, fs_code, dry):
    unp = json.load(open("unpaid_20260903.json"))
    rows = [r for r in unp if r["visitid"] == int(vid)]
    if not rows:
        return "not on unpaid list"
    cid = rows[0]["chargedetailids"].split(",")[0]
    rt, vis, pat, charges, paid = visit_state(cid)
    if vis.get("profile") == EFFINGER:
        return "already Effinger"
    if paid:
        return "SKIP: has posted payments (would unapply)"
    want_fs = info["car"] in FS_PAYERS
    if want_fs and not fs_code:
        return "HOLD: FS modifier not in Master Files yet"
    chg = ""
    for c in charges:
        a = {"id": c.get("id")}
        for f in resave.CHG_FIELDS:
            v = c.get(f)
            if v is not None: a[f] = v
        if want_fs and c.get("proccode") not in NO_FS_CPTS:
            mods = (a.get("modcodes") or "").split()
            if fs_code not in mods: mods.append(fs_code)
            a["modcodes"] = " ".join(mods)
        chg += "<charge %s/>" % " ".join('%s="%s"' % (k, v) for k, v in a.items())
    va = dict(vis.attrib); va["profile"] = EFFINGER; va["force"] = "1"
    vs = " ".join('%s="%s"' % (k, v) for k, v in va.items())
    if dry:
        return "DRY would resave %d charges profile->%s fs=%s" % (len(charges), EFFINGER, want_fs)
    r = amd.post(amd.msg("updvisitwithnewcharges", "chargeentry",
        {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1", "inspectorenabled": "1",
         "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"},
        "<visit %s><chargelist>%s</chargelist></visit>" % (vs, chg)))
    if "Fault" in r:
        return "ERR resave: " + re.sub(r"\s+", " ", (re.search(r"<description>([^<]*)", r) or [None, r[:150]])[1])[:150]
    time.sleep(0.8)
    # find the live (non-void) charges now — same visit or a new one
    rr = ET.fromstring(r)
    newvis = rr.find(".//visit"); newvid = (newvis.get("id") if newvis is not None else vis.get("id")) or vis.get("id")
    live = [c for c in rr.iter("charge") if c.get("void") != "1"] or []
    if not live:
        rt2, vis2, _, live, _ = visit_state(cid)
        newvid = vis2.get("id")
    newvid_num = re.sub(r"\D", "", newvid)
    seq = (vis.get("insorder") or "1").split(",")[0]
    out = []
    for c in live:
        ncid = c.get("id")
        ext = ('<extins txtChargeCode="%s" resubmissioncode="1" origrefnum="" patsignature="1" emergency="0" epsdt="0" payprov="1" employment="0" autoaccident="0" otheraccident="0" pregnant="0" outsidelab="0"/>') % c.get("proccode")
        amd.post(amd.msg("updextrainsinfo", "chargeentry", {"visitid": newvid_num, "nocookie": "1"}, ext))
        code, _ = amd.rebill_charge(ncid, seq)
        out.append((ncid, code))
    return "OK visit %s -> %s profile %s charges %s" % (vid, newvid, EFFINGER, out)

if __name__ == "__main__":
    a = sys.argv
    targets = json.load(open("effinger_rebill_targets.json"))
    cars = set(a[a.index("--carrier") + 1].split(",")) if "--carrier" in a else None
    only = set(a[a.index("--visits") + 1].split(",")) if "--visits" in a else None
    fs = a[a.index("--fs") + 1] if "--fs" in a else None
    dry = "--dry" in a
    done = {m.group(1) for line in open("rebill_effinger.log") for m in [re.search(r"OK visit (\d+)", line)] if m} if not dry else set()
    L("=== rebill under Effinger %s carriers=%s fs=%s dry=%s ===" % (time.ctime(), cars, fs, dry))
    for vid, info in targets.items():
        if cars and info["car"] not in cars: continue
        if only and vid not in only: continue
        if vid in done: continue
        try:
            res = do_visit(vid, info, fs, dry)
        except Exception as e:
            res = "EXC " + str(e)[:150]
        L("%s %-22s %s %s -> %s" % (info["car"], info["name"][:22], info["dos"], vid, res))
        time.sleep(0.8)
