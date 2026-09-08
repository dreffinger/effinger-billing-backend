# PLAIN ENGLISH (Bill a visit to another plan)
# Decides: Nothing on its own: re-points one visit at plan sequence N (optionally with a pre-auth) and rebills.
# Rules it uses: Full-visit echo.
# Never touches: Balances.
# ---
"""Bill a visit to another plan sequence: full-echo resave with insorder=<seq> (+ optional preauth), then chargerebill seq.
Usage: python3 rebill_to_seq.py <seq> [--preauth X] <visitid> ..."""
import amd, resave, json, sys, time
import xml.etree.ElementTree as ET
unp = json.load(open("unpaid_20260903.json"))
def do(vid, seq, preauth=None):
    rows = [x for x in unp if x["visitid"] == vid]
    if not rows: return "not on unpaid list"
    cid = rows[0]["chargedetailids"].split(",")[0]
    x = resave.detail(cid); root = ET.fromstring(x)
    pat = root.find(".//patient"); vis = root.find(".//visit")
    chg = ""
    for c in vis.findall(".//charge"):
        a = {"id": c.get("id")}
        for f in resave.CHG_FIELDS:
            v = c.get(f)
            if v is not None: a[f] = v
        chg += "<charge %s/>" % " ".join('%s="%s"' % (k, v) for k, v in a.items())
    va = dict(vis.attrib); va["insorder"] = str(seq); va["force"] = "1"
    if preauth: va["preauth"] = preauth
    vs = " ".join('%s="%s"' % (k, v) for k, v in va.items())
    r = amd.post(amd.msg("updvisitwithnewcharges", "chargeentry",
        {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1", "inspectorenabled": "1",
         "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"},
        "<visit %s><chargelist>%s</chargelist></visit>" % (vs, chg)))
    if "Fault" in r: return "RESAVE-FAULT"
    time.sleep(0.7)
    x2 = resave.detail(cid); v2 = ET.fromstring(x2).find(".//visit")
    ok = (v2.get("insorder") or "").startswith(str(seq)) and (not preauth or preauth in x2)
    code, _ = amd.rebill_charge(cid, int(seq))
    return "insorder=%s preauth_ok=%s rebill=%s" % (v2.get("insorder"), (preauth in x2) if preauth else "n/a", code)
if __name__ == "__main__":
    seq = int(sys.argv[1]); args = sys.argv[2:]; pre = None
    if "--preauth" in args: i = args.index("--preauth"); pre = args[i+1]; args = args[:i] + args[i+2:]
    for v in args:
        print("visit", v, "->", do(int(v), seq, pre)); time.sleep(1)
