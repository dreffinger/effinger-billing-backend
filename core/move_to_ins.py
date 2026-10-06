# PLAIN ENGLISH (Move balance to insurance + rebill)
# Decides: Moves a visit's patient-responsibility balance back to insurance, sets the plan order on the visit, and rebills it.
# Rules it uses: Moves every charge on the visit (the whole visit belongs to insurance, your 9/3 rule). Full-visit echo.
# Never touches: Payments already posted.
# ONE REBILL PER VISIT (William 10/6/2026): with seq it rebills the first plan of the new order itself. When a frequency-1
#   reset + rebill follows (freq1_visit.run), pass rebill=False (CLI --no-rebill) - or use freq1_visit.reroute for a pure
#   re-route. amd.rebill_charge also skips (204 'SKIPPED') a second rebill of the same VISIT + sequence in one script run.
# ---
"""Move a charge's balance from patient responsibility back to insurance (or vice-versa) and optionally rebill (rebill=False: never).
Full-echo updvisitwithcharges with insportion/patportion/insbalance/patbalance overridden.
Usage: python3 move_to_ins.py <chargeid> [--seq N] [--dry] [--no-rebill]"""
import amd, resave, re, sys, time
import xml.etree.ElementTree as ET
def move(cid, seq=None, dry=False, rebill_seq=None, rebill=True):
    vis, pat, allc = resave.visit_charges(cid)   # ALL live charges - omitting one voids it
    if not any(c.get("id") == "charge" + cid for c in allc): return "charge not live on visit"
    chg = ""; moved = 0.0
    for c in allc:
        a = {"id": c.get("id")}
        for f in resave.CHG_FIELDS:
            v = c.get(f)
            if v is not None: a[f] = v
        if c.get("void") != "1":   # move EVERY charge on the visit (William 9/3: whole visit belongs to insurance)
            pb = float(c.get("patbalance") or 0)
            if pb > 0:
                a["insbalance"] = "%.2f" % (float(c.get("insbalance") or 0) + pb); a["patbalance"] = "0.00"
                a["insportion"] = "%.2f" % (float(c.get("insportion") or 0) + float(c.get("patportion") or 0)); a["patportion"] = "0.00"
                moved += pb
        chg += "<charge %s/>" % " ".join('%s="%s"' % (k, v) for k, v in a.items())
    va = dict(vis.attrib); va["force"] = "1"
    if seq: va["insorder"] = str(seq)
    vs = " ".join('%s="%s"' % (k, v) for k, v in va.items())
    if dry: return "DRY move %.2f seq %s" % (moved, va.get("insorder"))
    if moved == 0 and not seq: return "nothing to move"
    r = amd.post(amd.msg("updvisitwithcharges", "chargeentry",
        {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1", "inspectorenabled": "1",
         "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"},
        "<visit %s><chargelist>%s</chargelist></visit>" % (vs, chg)))
    if "Fault" in r: return "FAULT " + re.sub(r"\s+", " ", r[:200])
    time.sleep(0.8)
    x2 = resave.detail(cid); m = re.search(r'<charge [^>]*id="charge%s"[^>]*>' % cid, x2); v2 = re.search(r'<visit [^>]*>', x2).group(0)
    st = dict(re.findall(r'(insbalance|patbalance)="([^"]*)"', m.group(0))); st["insorder"] = re.search(r'insorder="([^"]*)"', v2).group(1)
    rb = ""
    if seq and not rebill:
        rb = " (no rebill - the caller rebills ONCE via freq1_visit)"
    elif seq:
        rs = int(rebill_seq) if rebill_seq else int(str(seq).split(",")[0]); code, _ = amd.rebill_charge(cid, rs, visitid=vis.get("id")); rb = " rebill seq %s (sent to %s) -> %s" % (seq, rs, code)
    return "moved %.2f -> %s%s" % (moved, st, rb)
if __name__ == "__main__":
    a = sys.argv; seq = a[a.index("--seq") + 1] if "--seq" in a else None
    print(move(a[1], seq, "--dry" in a, rebill="--no-rebill" not in a))
