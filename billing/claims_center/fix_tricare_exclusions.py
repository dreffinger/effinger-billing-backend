# PLAIN ENGLISH (TRICARE referral numbers)
# Decides: Puts the TRICARE referral/auth from the facesheet on each excluded visit, resaves, rebills, completes the exclusion.
# Rules it uses: 'NR/27447' style registrar codes are sent as-is (your 9/2 call).
# Never touches: Non-TRICARE visits.
# ---
"""Fix the TRICARE EAST exclusions (PREF0201 MISSING ORIGINAL REF NUMBER): set the TRICARE
referral/auth number as preauth on each visit (lands on the refplan, prints as claim auth —
same mechanism as the VA auth fix), resave (full echo), rebill, then complete the exclusion.
Usage: edit AUTHS below (patient -> auth number), then run. Skips patients with no auth."""
import amd, resave, json, time
import xml.etree.ElementTree as ET

# patient name (exactly as in AMD) -> TRICARE referral/auth number
AUTHS = {
    # "[name]": "0000-25239000235",   # done 9/2
    "[name]": "NR27447",       # HCA facesheet auth field "Auth NR/27447" — William 9/2: submit as-is
    "PRYCE VALE,PATIENT864": "NR27447",
    "JESSOP,RUPERT": "0000-25324017793/R",   # HCA 11/21/25-12/18/25 stroke admission facesheet (William 9/2: use prior-admit auth)    # same value on her HCA facesheet — William 9/2: submit as-is
}
CLAIMRUNID = "1700088"
LOG = open("tricare_fix.log", "a")
def L(m):
    print(m); LOG.write(m + "\n"); LOG.flush()

def set_preauth(chargeid, auth):
    x = resave.detail(chargeid); root = ET.fromstring(x)
    pat = root.find(".//patient"); vis = root.find(".//visit")
    chg = ""
    for c in vis.findall(".//charge"):
        a = {"id": c.get("id")}
        for f in resave.CHG_FIELDS:
            v = c.get(f)
            if v is not None: a[f] = v
        chg += "<charge %s/>" % " ".join('%s="%s"' % (k, v) for k, v in a.items())
    va = dict(vis.attrib); va["preauth"] = auth; va["force"] = "1"
    vs = " ".join('%s="%s"' % (k, v) for k, v in va.items())
    body = amd.msg("updvisitwithnewcharges", "chargeentry",
        {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1",
         "inspectorenabled": "1", "getfinancials": "-1", "customclaimfieldsavailable": "1",
         "nocookie": "1"},
        "<visit %s><chargelist>%s</chargelist></visit>" % (vs, chg))
    r = amd.post(body)
    time.sleep(0.8)
    x2 = resave.detail(chargeid)
    return ("Fault" not in r), (auth in x2)

def complete_exclusion(visitid, claimid):
    # hideexclusions hide=-1 (skill); try visit-scoped child
    child = '<visitlist><visit id="%s" claimid="%s"/></visitlist>' % (visitid, claimid)
    r = amd.post(amd.msg("hideexclusions", "claimsreports",
                {"claimrunid": CLAIMRUNID, "hide": "-1", "nocookie": "1"}, child))
    return "Fault" not in r, r[:200]

def main():
    root = ET.fromstring(open("exclusions_raw_now.xml").read())
    done = []
    for v in root.findall(".//visit"):
        name = v.get("patientname"); auth = AUTHS.get(name, "").strip()
        if not auth:
            L("SKIP %s (no auth provided)" % name); continue
        vid = v.get("id"); claimid = v.get("claimid")
        for c in v.findall(".//charge"):
            cid = str(c.get("id")).replace("charge", "")
            ok, verified = set_preauth(cid, auth)
            io = (v.get("insorder") or "1").split(",")[0] if v.get("insorder") else "1"
            code = None
            if ok:
                try: code, _ = amd.rebill_charge(cid, int(io))
                except Exception as e: code = "exc:%s" % e
            L("  %-22s charge %s %s  preauth=%s verified=%s rebill=%s" % (name, cid, c.get("dos"), auth, verified, code))
            time.sleep(0.8)
        cok, ctxt = complete_exclusion(vid, claimid)
        L("     complete exclusion visit %s -> %s %s" % (vid, "OK" if cok else "FAULT", "" if cok else ctxt))
        done.append(name); time.sleep(0.6)
    L("=== done: %s ===" % sorted(set(done)))

if __name__ == "__main__":
    main()
