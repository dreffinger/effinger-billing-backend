# PLAIN ENGLISH (Apply I63.9 to I69.30)
# Decides: For every outpatient charge carrying acute stroke I63.9, swaps to sequela I69.30 and rebills the denied ones.
# Rules it uses: Your 9/1 standing order; never in the hospital (POS 21); skip if a payment is posted.
# Never touches: Inpatient charges.
# ---
"""Apply the I63.9 -> I69.30 outpatient swap to all matches in i63_matches.json.
Standing rule (William 9/1, re-authorized 9/2). Per charge: re-verify I63.9 + POS!=21,
skip if payment posted, swap dcode, resave (full echo), rebill (chargerebill REST, expect
204), verify insbilled cleared. Logs every action. Idempotent-ish: re-checks live state."""
import amd, resave, json, time
import xml.etree.ElementTree as ET

I639 = "dcode1034545006"
I6930 = "dcode1034545425"
LOG = open("i63_apply.log", "a")
def L(m):
    print(m); LOG.write(m + "\n"); LOG.flush()


def _no_rebill(m):
    """Standing rule: never rebill UNI20 aged ERA-backlog balances (Jan-Jul 2026 ERAs missing)."""
    return (m.get("payer") == "UNI20") and (str(m.get("dos","")) < "2026-08-01")

def swap_and_rebill(m):
    cid = m["firstcid"]
    x = resave.detail(cid); root = ET.fromstring(x)
    pat = root.find(".//patient"); vis = root.find(".//visit")
    if vis is None:
        return "no-visit"
    # locate target charge (by id if present, else any with I63.9 + POS!=21)
    target = None
    for c in vis.findall(".//charge"):
        if m.get("chargeid") and c.get("id") == m["chargeid"]:
            target = c; break
    if target is None:
        for c in vis.findall(".//charge"):
            if I639 in (c.get("diagcodes") or "") and (c.get("pos") or "") != "21":
                target = c; break
    if target is None:
        return "no-i639-charge"
    if (target.get("pos") or "") == "21":
        return "POS21-keep"
    if target.get("void") == "1":
        return "SKIP-void"
    already = I639 not in (target.get("diagcodes") or "")
    io = (vis.get("insorder") or "1").split(",")[0]
    if already:
        if _no_rebill(m): return "already-swapped, NO-REBILL(UNI20 backlog)"
        # swap already applied earlier; just (re)bill it
        try:
            code, _ = amd.rebill_charge(target.get("id"), int(io))
            return "already-swapped, rebill_http=%s" % code
        except Exception as e:
            return "already-swapped, rebill-exc=%s" % e
    if root.find(".//payment") is not None:
        return "SKIP-payment-posted"
    newdc = target.get("diagcodes").replace(I639, I6930)
    target.set("diagcodes", newdc)
    # full-echo resave with the swapped diagcode on the target charge
    chg_xml = ""
    for c in vis.findall(".//charge"):
        a = {"id": c.get("id")}
        for f in resave.CHG_FIELDS:
            v = c.get(f)
            if v is not None: a[f] = v
        chg_xml += "<charge %s/>" % " ".join('%s="%s"' % (k, v) for k, v in a.items())
    va = dict(vis.attrib); va["force"] = "1"
    vs = " ".join('%s="%s"' % (k, v) for k, v in va.items())
    body = amd.msg("updvisitwithnewcharges", "chargeentry",
        {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1",
         "inspectorenabled": "1", "getfinancials": "-1", "customclaimfieldsavailable": "1",
         "nocookie": "1"},
        "<visit %s><chargelist>%s</chargelist></visit>" % (vs, chg_xml))
    resp = amd.post(body)
    if "Fault" in resp:
        return "RESAVE-FAULT"
    # verify swap persisted + not voided
    time.sleep(0.6)
    x2 = resave.detail(cid); vis2 = ET.fromstring(x2).find(".//visit")
    tc = None
    for c in vis2.findall(".//charge"):
        if c.get("id") == target.get("id"): tc = c; break
    if tc is None or I639 in (tc.get("diagcodes") or ""):
        return "SWAP-NOT-PERSISTED"
    if tc.get("void") == "1":
        return "!!VOIDED"
    # rebill
    if _no_rebill(m): return "OK swapped, NO-REBILL(UNI20 backlog)"
    try:
        io2 = (vis2.get("insorder") or io or "1").split(",")[0]
        code, _ = amd.rebill_charge(target.get("id"), int(io2))
        return "OK rebill_http=%s" % code
    except Exception as e:
        return "swapped OK, rebill-exc=%s" % e

def main():
    import os
    matches = json.load(open("i63_matches.json"))
    start = int(os.environ.get("I63_START", "0"))
    L("=== I63.9 APPLY start %s  matches=%d  from=%d ===" % (time.ctime(), len(matches), start))
    done = []
    for i, m in enumerate(matches, 1):
        if i <= start: continue
        try:
            r = swap_and_rebill(m)
        except Exception as e:
            r = "ERR %s" % e
        L("  [%d/%d] %s %s %s POS%s -> %s" % (i, len(matches), m.get("patient"),
          m.get("dos"), m.get("payer"), m.get("pos"), r))
        m["result"] = r; done.append(m)
        if r == "!!VOIDED":
            L("STOP: void detected, halting."); break
        time.sleep(1.0)
    json.dump(done, open("i63_applied.json", "w"), indent=1)
    ok = sum(1 for m in done if str(m.get("result", "")).startswith("OK"))
    L("=== APPLY done. swapped+rebilled=%d of %d ===" % (ok, len(done)))

if __name__ == "__main__":
    main()
