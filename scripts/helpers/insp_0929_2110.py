# PLAIN ENGLISH (Claim Inspector pass, 5pm ET 9/29/2026 run 2026-09-29T2110Z): two new rows on batch 127827 (pat17477843, two visits)
#   raise only Pattern 11256 (H91.90 unspecified laterality) - an advisory. Decides: (1) PRIMARY-DX GATE on every live charge of the
#   two visits (dx_primary_fix.never_primary on the FIRST code) - only then (2) re-list the batch and bypass Pattern 11256 with the FRESH
#   error ids, logging the visit/code to laterality_flag_log.md. Anything else on the batch is left alone (the 25 standing holds).
# Never touches: payments, write-offs, diagnosis lists (no never-primary code found), hospitalization dates, insurance plans.
import amd, resave, dx_primary_fix, re, json, time, sys, datetime
import xml.etree.ElementTree as ET
DRY = "--dry" in sys.argv; STAMP = "2026-09-29T2110Z"; BATCH = "127827"; PID = "17477843"
amd.login_cached()
out = {"stamp": STAMP, "visits": []}
t = amd.post(amd.msg("getclaiminspectorcharges", "chargeentry", {"batchid": BATCH, "nocookie": "1"}), timeout=120)
root = ET.fromstring(t)
for v in root.iter("visit"):
    if v.get("patientid") != PID: continue
    vid = v.get("id"); errs = [(e.get("id"), re.sub(r"\s+", " ", (e.text or "") + "".join((c.text or "") for c in e.iter()))) for e in v.iter("error")]
    chgs = [c.get("id") for c in v.iter("charge")]
    rec = {"vid": vid, "errs": errs, "charges": chgs, "gate": [], "bypassed": None}
    for cid in chgs:
        x = resave.detail(cid.replace("charge", ""))
        codes = re.findall(r'<diagcode id="(dcode\d+)"[^>]*?\bcode="([^"]*)"', x)
        m = re.search(r'<charge [^>]*diagcodes="([^"]*)"', x)
        order = (m.group(1).split() if m else [])
        dmap = dict(codes); first = dmap.get(order[0], "") if order else ""
        cpt = re.search(r'<charge [^>]*proccode="([^"]*)"', x)
        rec["gate"].append({"cid": cid, "cpt": cpt.group(1) if cpt else "", "dx": [dmap.get(d, d) for d in order], "first_never_primary": bool(first and dx_primary_fix.never_primary(first))})
    only_adv = all("Pattern 11256" in e[1] for e in errs)
    gate_ok = not any(g["first_never_primary"] for g in rec["gate"])
    if only_adv and gate_ok and errs:
        if DRY: rec["bypassed"] = "dry"
        else:
            r = amd.post(amd.msg("bypassclaimedits", "chargeentry", {"nocookie": "1"}, '<visitlist><visit id="%s"><claimeditlist>%s</claimeditlist></visit></visitlist>' % (vid, "".join('<claimedit id="%s"/>' % e[0] for e in errs))))
            rec["bypassed"] = "Fault" not in r; rec["resp"] = r[:200]
            open("laterality_flag_log.md", "a").write("- %s run %s: pat%s visit %s charges %s - Pattern 11256 H91.90 (unspecified hearing loss) bypassed as advisory; documentation may support a laterality code (William)\n" % (datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%MZ"), STAMP, PID, vid, ",".join(chgs)))
    out["visits"].append(rec); print(json.dumps(rec)[:600], flush=True); time.sleep(0.3)
json.dump(out, open("registers/insp_%s.json" % STAMP, "w"), indent=1)
