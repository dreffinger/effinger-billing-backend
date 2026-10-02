# PLAIN ENGLISH (Claim Inspector pass, 1 AM ET 10/2/2026 run 2026-10-02T0510Z - ehpa cloud)
# Decides: the two CCM visits of pat17472396 re-routed to Humana this run (v19442523 batch 126912, v19446223 batch 127180) were
#   re-inspected and raise only Pattern 35790 (add-on 99489 reported with 99487) - the standing advisory. Checked live first:
#   the 99489 on each visit already carries modifier 25 (mcode7) and the 99487 does not (William's CCM rule), and the FIRST
#   diagnosis (C18.9) passes the PRIMARY-DX GATE (dx_primary_fix.never_primary). So: re-list each batch and bypass Pattern 35790
#   with the FRESH error ids (ids change on every re-inspection). Anything else on those batches is left alone.
# Never touches: payments, write-offs, diagnosis lists, modifiers (already right), hospitalization dates, insurance plans.
#   python3 insp_0510.py          # dry (default): gate + list what would be bypassed
#   python3 insp_0510.py --live   # bypass; register registers/insp_2026-10-02T0510Z.json
import sys, re, json, time
import xml.etree.ElementTree as ET
import amd, resave, dx_primary_fix
LIVE = "--live" in sys.argv; DRY = not LIVE; STAMP = "2026-10-02T0510Z"; PID = "17472396"
TARGETS = {"126912": "19442523", "127180": "19446223"}
amd.login_cached()
out = {"stamp": STAMP, "live": LIVE, "visits": []}
for batch, want in TARGETS.items():
    t = amd.post(amd.msg("getclaiminspectorcharges", "chargeentry", {"batchid": batch, "nocookie": "1"}), timeout=120)
    root = ET.fromstring(t)
    for v in root.iter("visit"):
        if v.get("patientid") != PID or v.get("id") != want: continue
        vid = v.get("id"); errs = [(e.get("id"), re.sub(r"\s+", " ", (e.get("name") or "") + " " + (e.text or "") + "".join((c.text or "") for c in e.iter()))) for e in v.iter("error")]
        chgs = [c.get("id") for c in v.iter("charge")]
        rec = {"batch": batch, "vid": vid, "errs": errs, "charges": chgs, "gate": [], "bypassed": None}
        for cid in chgs:
            x = resave.detail(cid.replace("charge", ""))
            codes = re.findall(r'<diagcode id="(dcode\d+)"[^>]*?\bcode="([^"]*)"', x)
            m = re.search(r'<charge [^>]*id="%s"[^>]*>' % cid, x) or re.search(r'<charge [^>]*>', x)
            a = dict(re.findall(r'(\w+)="([^"]*)"', m.group(0)))
            order = (a.get("diagcodes") or "").split(); dmap = dict(codes); first = dmap.get(order[0], "") if order else ""
            rec["gate"].append({"cid": cid, "cpt": a.get("proccode"), "modcodes": a.get("modcodes"), "dx": [dmap.get(d, d) for d in order],
                                "first_never_primary": bool(first and dx_primary_fix.never_primary(first))})
        only_adv = bool(errs) and all(("35790" in e[1]) or ("68065080" in e[1]) for e in errs)
        gate_ok = not any(g["first_never_primary"] for g in rec["gate"])
        rec["only_advisory"] = only_adv; rec["gate_ok"] = gate_ok
        if only_adv and gate_ok:
            if DRY: rec["bypassed"] = "dry"
            else:
                r = amd.post(amd.msg("bypassclaimedits", "chargeentry", {"nocookie": "1"}, '<visitlist><visit id="%s"><claimeditlist>%s</claimeditlist></visit></visitlist>' % (vid, "".join('<claimedit id="%s"/>' % e[0] for e in errs))))
                rec["bypassed"] = "Fault" not in r; rec["resp"] = re.sub(r"\s+", " ", r[:200])
        out["visits"].append(rec); print(json.dumps(rec)[:900], flush=True); time.sleep(0.3)
json.dump(out, open("registers/insp_%s%s.json" % (STAMP, "" if LIVE else "_dry"), "w"), indent=1)
print("DONE", "live" if LIVE else "dry", len(out["visits"]), "visit(s)")
