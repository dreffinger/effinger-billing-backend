# PLAIN ENGLISH (Add a modifier and rebill)
# Decides: Adds one modifier (e.g. GV) to every charge on a visit and rebills.
# Rules it uses: Hospice denials get GV.
# Never touches: Paid visits.
# ---
"""Add a modifier to every charge on a visit (full-echo resave) and rebill. William 9/2: hospice
denials (COB9) -> rebill with GV (mcode713). Usage: python3 add_modifier_rebill.py mcode713 <visitid> ..."""
import amd, resave, json, sys, time, re
import xml.etree.ElementTree as ET
unp = json.load(open("unpaid_20260902b.json"))
def charges_for_visit(vid):
    r = [x for x in unp if x["visitid"] == vid]
    return r[0]["chargedetailids"].split(",") if r else []
def resave_with_mod(cid, mcode):
    x = resave.detail(cid); root = ET.fromstring(x)
    pat = root.find(".//patient"); vis = root.find(".//visit")
    chg = ""; changed = []
    for c in vis.findall(".//charge"):
        a = {"id": c.get("id")}
        for f in resave.CHG_FIELDS:
            v = c.get(f)
            if v is not None: a[f] = v
        if c.get("void") != "1":
            mods = (a.get("modcodes") or "").split()
            if mcode not in mods: mods.append(mcode)
            a["modcodes"] = " ".join(mods); changed.append(c.get("id"))
        chg += "<charge %s/>" % " ".join('%s="%s"' % (k, v) for k, v in a.items())
    va = dict(vis.attrib); va["force"] = "1"
    vs = " ".join('%s="%s"' % (k, v) for k, v in va.items())
    body = amd.msg("updvisitwithnewcharges", "chargeentry",
        {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1", "inspectorenabled": "1",
         "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"},
        "<visit %s><chargelist>%s</chargelist></visit>" % (vs, chg))
    r = amd.post(body); time.sleep(0.8)
    x2 = resave.detail(cid)
    ok = all(mcode in (dict(re.findall(r'(\w+)="([^"]*)"', ch)).get("modcodes") or "") for ch in re.findall(r"<charge [^>]*>", x2) if 'void="0"' in ch)
    io = (vis.get("insorder") or "1").split(",")[0]
    return ("Fault" not in r), ok, io, changed
if __name__ == "__main__":
    mcode = sys.argv[1]
    for vid in sys.argv[2:]:
        cids = charges_for_visit(int(vid))
        if not cids: print(vid, "not on unpaid list"); continue
        saved, verified, io, changed = resave_with_mod(cids[0], mcode)
        code = None
        if saved and verified:
            try: code, _ = amd.rebill_charge(cids[0], int(io))
            except Exception as e: code = "exc:%s" % e
        print("visit %s charges %s -> save=%s verified=%s rebill=%s" % (vid, changed, saved, verified, code))
        time.sleep(1)
