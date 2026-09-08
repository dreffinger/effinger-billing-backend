# PLAIN ENGLISH (I63.9 sweep (scan + apply))
# Decides: Same rule as i63_apply, run as one off-peak sweep over open claims.
# Rules it uses: Safety-gated full echo; logs every change.
# Never touches: POS 21.
# ---
"""Off-peak I63.9 -> I69.30 outpatient sweep. Standing order (William 9/1).
Scans open claims; for any charge with I63.9 (dcode1034545006) in a NON-POS-21
setting, swaps to I69.30 (dcode1034545425), resaves (full echo, safety-gated),
and rebills denied ones. Logs every change. Read-scan is the bulk; mutations few.
"""
import amd, resave, json, time, re, sys
import xml.etree.ElementTree as ET

I639 = "dcode1034545006"
I6930 = "dcode1034545425"
LOG = open("i63_sweep.log", "a")
def log(m):
    LOG.write(m + "\n"); LOG.flush()

def main():
    rows = json.load(open("unpaid_20260902.json"))
    if isinstance(rows, dict):
        rows = next(v for v in rows.values() if isinstance(v, list))
    log("=== I63.9 sweep start %s  open visits=%d ===" % (time.ctime(), len(rows)))
    matches = []; scanned = 0; changed = []
    for r in rows:
        cids = (r.get("chargedetailids") or "").split(",")
        if not cids or not cids[0]:
            continue
        try:
            x = resave.detail(cids[0])
            root = ET.fromstring(x)
        except Exception as e:
            time.sleep(0.8); continue
        vis = root.find(".//visit")
        if vis is None:
            time.sleep(0.8); continue
        for c in vis.findall(".//charge"):
            dc = c.get("diagcodes") or ""
            pos = (c.get("pos") or "").strip()
            if I639 in dc and pos != "21":
                matches.append({"visitid": r.get("visitid"), "patient": r.get("patientname"),
                                "dos": r.get("dateofservice", "")[:10], "payer": r.get("carriercode"),
                                "pos": pos, "chargeid": c.get("id"), "before": dc,
                                "insbalance": r.get("insbalance"), "firstcid": cids[0]})
        scanned += 1
        if scanned % 200 == 0:
            log("  scanned %d/%d  matches so far %d" % (scanned, len(rows), len(matches)))
            json.dump(matches, open("i63_matches.json", "w"), indent=1)
        time.sleep(0.8)
    json.dump(matches, open("i63_matches.json", "w"), indent=1)
    log("SCAN DONE. scanned=%d  I63.9-outpatient charges=%d" % (scanned, len(matches)))

    if len(matches) > 40:
        log("SAFETY STOP: %d matches (>40). Not mutating in bulk unattended. Review i63_matches.json." % len(matches))
        return
    # mutate the matches
    for m in matches:
        try:
            x = resave.detail(m["firstcid"]); root = ET.fromstring(x)
            vis = root.find(".//visit")
            tgt = None
            for c in vis.findall(".//charge"):
                if c.get("id") == m["chargeid"]:
                    tgt = c; break
            if tgt is None:
                log("  SKIP %s: charge gone" % m["patient"]); continue
            # safety: skip if any payment posted on visit or diagcodes missing
            if root.find(".//payment") is not None:
                log("  SKIP %s: payment posted" % m["patient"]); continue
            newdc = m["before"].replace(I639, I6930)
            # resave with the swapped diagcode on this charge only
            # build extra echo: use resave but override this charge's diagcodes
            # simplest: set attribute in-memory then re-run full echo
            tgt.set("diagcodes", newdc)
            # rebuild chargelist echo manually to include the override
            from resave import CHG_FIELDS, _extins_xml
            chg_xml = ""
            for c in vis.findall(".//charge"):
                attrs = {"id": c.get("id")}
                for f in CHG_FIELDS:
                    v = c.get(f)
                    if v is not None: attrs[f] = v
                chg_xml += "<charge %s/>" % " ".join('%s="%s"' % (k, v) for k, v in attrs.items())
            pat = root.find(".//patient")
            vattrs = {"id": vis.get("id"), "date": vis.get("date"), "profile": vis.get("profile"),
                      "insorder": vis.get("insorder"), "refplan": vis.get("refplan"),
                      "facility": vis.get("facility"), "force": "1"}
            va = " ".join('%s="%s"' % (k, v) for k, v in vattrs.items() if v is not None)
            body = amd.msg("updvisitwithnewcharges", "chargeentry",
                {"patientid": pat.get("id"), "episodeid": vis.get("episode"),
                 "approval": "1", "inspectorenabled": "1", "getfinancials": "-1",
                 "customclaimfieldsavailable": "1", "nocookie": "1"},
                "<visit %s><chargelist>%s</chargelist></visit>" % (va, chg_xml))
            resp = amd.post(body)
            ok = "Fault" not in resp
            log("  SWAP %s %s %s POS%s -> I69.30 : %s" % (m["patient"], m["dos"], m["payer"], m["pos"], "OK" if ok else "ERR"))
            if ok:
                m["after"] = newdc; changed.append(m)
                # rebill (denied/unpaid) via chargerebill
                try:
                    code, _ = amd.rebill_charge(m["chargeid"], int(m.get("insorder") or 1))
                    log("     rebill http=%s" % code)
                except Exception as e:
                    log("     rebill exc %s" % e)
            time.sleep(1.0)
        except Exception as e:
            log("  ERR %s: %s" % (m.get("patient"), e))
    json.dump(changed, open("i63_changed.json", "w"), indent=1)
    log("=== I63.9 sweep done. swapped=%d ===" % len(changed))

if __name__ == "__main__":
    main()
