# PLAIN ENGLISH (Claim Inspector advisory bypass, generic - written 10/1/2026 run 2026-10-01T0110Z):
#   one named helper for the standing rule "advisories (add-on 35790, CCM frequency 7011/3429/35777/33799, timely 20657, AWV 27261,
#   provider-history 4310, mod-25 4426, unspecified laterality 11256) -> bypassclaimedits with FRESH error ids".
# Decides: for the ONE visit named on the command line: (1) PRIMARY-DX GATE on every live charge (dx_primary_fix.never_primary on the
#   first code, read live by charge id); (2) for Pattern 35790 the modifier rule (99489 = pcode492677 carries 25, 99487 = pcode492676
#   does not); (3) re-lists the batch so the error ids are fresh; (4) bypasses ONLY when every error on the visit is the named advisory
#   pattern and the gates pass. A missing-data error, a dx-order error or a failed gate = held, nothing written. Pattern 11256 bypasses are
#   logged to laterality_flag_log.md.
# Never touches: diagnosis codes, modifiers, dates, plans, payments, any other visit in the batch.
#   python3 insp_bypass.py --batch 127783 --visit 19455716 --pattern 35790           # dry: gate + fresh ids, no write
#   python3 insp_bypass.py --batch 127783 --visit 19455716 --pattern 35790 --live    # bypass; register registers/insp_bypass_<stamp>.json
import amd, resave, dx_primary_fix, re, json, time, sys, datetime, os
import xml.etree.ElementTree as ET
a = sys.argv
LIVE = "--live" in a
batch = a[a.index("--batch") + 1]; vid = a[a.index("--visit") + 1]
pat_num = a[a.index("--pattern") + 1].replace("Pattern", "").strip(); pattern = "Pattern " + pat_num
STAMP = a[a.index("--stamp") + 1] if "--stamp" in a else datetime.datetime.utcnow().strftime("%Y-%m-%dT%H%MZ")
amd.login_cached()
t = amd.post(amd.msg("getclaiminspectorcharges", "chargeentry", {"batchid": batch, "nocookie": "1"}), timeout=120)
rec = {"stamp": STAMP, "live": LIVE, "batch": batch, "vid": vid, "pattern": pattern, "found": False}
for v in ET.fromstring(t).iter("visit"):
    if v.get("id") != vid: continue
    rec["found"] = True; rec["pid"] = v.get("patientid")
    errs = [(e.get("id"), re.sub(r"\s+", " ", (e.text or "") + "".join((c.text or "") for c in e.iter()))) for e in v.iter("error")]
    chgs = [c.get("id") for c in v.iter("charge")]
    rec["errs"] = errs; rec["charges"] = chgs; rec["gate"] = []
    for cid in chgs:
        x = resave.detail(cid.replace("charge", ""))
        codes = dict(re.findall(r'<diagcode id="(dcode\d+)"[^>]*?\bcode="([^"]*)"', x))
        m = re.search(r'<charge [^>]*diagcodes="([^"]*)"', x); order = m.group(1).split() if m else []
        first = codes.get(order[0], "") if order else ""
        cpt = re.search(r'<charge [^>]*proccode="([^"]*)"', x); mods = re.findall(r'<modcode [^>]*code="([^"]*)"', x)
        rec["gate"].append({"cid": cid, "cpt": cpt.group(1) if cpt else "", "mods": mods, "dx": [codes.get(d, d) for d in order],
                            "first_never_primary": bool(first and dx_primary_fix.never_primary(first))})
    only_adv = bool(errs) and all(pattern in e[1] for e in errs)
    gate_ok = not any(g["first_never_primary"] for g in rec["gate"])
    mod_ok = True
    if pat_num == "35790":
        for g in rec["gate"]:
            if g["cpt"] == "pcode492677" and "25" not in g["mods"]: mod_ok = False
            if g["cpt"] == "pcode492676" and "25" in g["mods"]: mod_ok = False
    rec.update({"only_adv": only_adv, "gate_ok": gate_ok, "mod_ok": mod_ok})
    if only_adv and gate_ok and mod_ok:
        if not LIVE: rec["bypassed"] = "dry"
        else:
            r = amd.post(amd.msg("bypassclaimedits", "chargeentry", {"nocookie": "1"}, '<visitlist><visit id="%s"><claimeditlist>%s</claimeditlist></visit></visitlist>' % (vid, "".join('<claimedit id="%s"/>' % e[0] for e in errs))))
            rec["bypassed"] = "Fault" not in r; rec["resp"] = r[:200]
            if pat_num == "11256" and rec["bypassed"]:
                open("laterality_flag_log.md", "a").write("- %s run %s: pat%s visit %s charges %s - Pattern 11256 bypassed as advisory (%s); documentation may support a laterality code (William)\n" % (datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%MZ"), STAMP, rec["pid"], vid, ",".join(chgs), errs[0][1][:120]))
    else:
        rec["bypassed"] = "held"
os.makedirs("registers", exist_ok=True)
regf = "registers/insp_bypass_%s%s.json" % (STAMP, "" if LIVE else "_dry")
old = json.load(open(regf)) if os.path.exists(regf) else []
old.append(rec); json.dump(old, open(regf, "w"), indent=1)
print(json.dumps({k: rec.get(k) for k in ("vid", "pid", "pattern", "errs", "only_adv", "gate_ok", "mod_ok", "bypassed", "found")})[:900])
