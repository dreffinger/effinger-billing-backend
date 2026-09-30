# PLAIN ENGLISH (Claim Inspector pass, 9am ET 9/30/2026 run 2026-09-30T1310Z): three NEW inspector rows beyond the 25 standing holds -
#   pat17477638 v19455623 (batch 127783, Pattern 35790 CCM add-on advisory; the 99489 already carries modifier 25 = mcode7),
#   pat17476681 v19455801 (batch 127783) and v19456218 (batch 127793), Pattern 11256 (M25.559 / S70.00XA unspecified laterality) - advisories.
# Decides: (1) PRIMARY-DX GATE on every live charge of each visit (dx_primary_fix.never_primary on the FIRST code; read live by charge id) -
#   only then (2) re-list the batch and bypass the advisory with the FRESH error ids (ids change on every re-inspection), logging the
#   laterality visits to laterality_flag_log.md. A visit whose gate fails or whose errors are anything but the named advisory is left alone.
# Rules it uses: 99487 never carries 25, the add-on 99489 does (mcode7) - verified on the live detail before the bypass; missing-data errors are never bypassed.
# Also applies William's outpatient stroke rule on v19455623 (SODALIS ALF, fac65): I63.9 -> I69.30 (dcode1034545425) on both CCM charges, full-visit echo, then fresh ids.
# Never touches: payments, write-offs, other diagnosis codes, modifiers, hospitalization dates, insurance plans, the 25 standing holds.
#   python3 insp_0930_1310.py          # dry: gate + fresh ids, no write
#   python3 insp_0930_1310.py --live   # bypass, log, register registers/insp_2026-09-30T1310Z.json
import amd, resave, recode, dx_primary_fix, re, json, time, sys, datetime
import xml.etree.ElementTree as ET
LIVE = "--live" in sys.argv; STAMP = "2026-09-30T1310Z"
TARGETS = {"127783": {"19455623": "Pattern 35790", "19455801": "Pattern 11256"}, "127793": {"19456218": "Pattern 11256"}}
amd.login_cached()
out = {"stamp": STAMP, "live": LIVE, "visits": []}
for batch, wanted in TARGETS.items():
    t = amd.post(amd.msg("getclaiminspectorcharges", "chargeentry", {"batchid": batch, "nocookie": "1"}), timeout=120)
    root = ET.fromstring(t)
    for v in root.iter("visit"):
        vid = v.get("id")
        if vid not in wanted: continue
        pattern = wanted[vid]
        errs = [(e.get("id"), re.sub(r"\s+", " ", (e.text or "") + "".join((c.text or "") for c in e.iter()))) for e in v.iter("error")]
        chgs = [c.get("id") for c in v.iter("charge")]
        rec = {"batch": batch, "vid": vid, "pid": v.get("patientid"), "pattern": pattern, "errs": errs, "charges": chgs, "gate": [], "bypassed": None}
        for cid in chgs:
            x = resave.detail(cid.replace("charge", ""))
            codes = re.findall(r'<diagcode id="(dcode\d+)"[^>]*?\bcode="([^"]*)"', x)
            m = re.search(r'<charge [^>]*diagcodes="([^"]*)"', x)
            order = (m.group(1).split() if m else [])
            dmap = dict(codes); first = dmap.get(order[0], "") if order else ""
            cpt = re.search(r'<charge [^>]*proccode="([^"]*)"', x)
            mods = re.findall(r'<modcode [^>]*code="([^"]*)"', x)
            rec["gate"].append({"cid": cid, "cpt": cpt.group(1) if cpt else "", "mods": mods, "dx": [dmap.get(d, d) for d in order],
                                "first_never_primary": bool(first and dx_primary_fix.never_primary(first))})
        # William's standing outpatient rule: I63.9 (acute stroke, dcode1034545006) on a non-hospital visit -> I69.30 (dcode1034545425), never deleted.
        # fac65 = SODALIS ALF; the swap is a full-visit echo (recode._save), after which the batch is re-listed for FRESH error ids.
        fac = v.get("facility") or ""
        has_i63 = any("I63.9" in g["dx"] for g in rec["gate"]) and fac not in ("fac29",)
        rec["i63_swap"] = None
        if has_i63:
            if not LIVE: rec["i63_swap"] = "dry: would swap I63.9 -> I69.30 on %s (facility %s)" % (chgs, fac)
            else:
                def _e(a):
                    d = (a.get("diagcodes") or "").split()
                    if "dcode1034545006" in d: a["diagcodes"] = " ".join("dcode1034545425" if x == "dcode1034545006" else x for x in d); return True
                    return False
                c2, msg = recode._save(chgs[0].replace("charge", ""), _e)
                rec["i63_swap"] = msg
                if c2 is None:
                    rec["bypassed"] = "held (swap fault)"; out["visits"].append(rec); print(json.dumps(rec)[:700], flush=True); continue
                time.sleep(1.0)
                t2 = amd.post(amd.msg("getclaiminspectorcharges", "chargeentry", {"batchid": batch, "nocookie": "1"}), timeout=120)
                errs = []
                for v2 in ET.fromstring(t2).iter("visit"):
                    if v2.get("id") == vid:
                        errs = [(e.get("id"), re.sub(r"\s+", " ", (e.text or "") + "".join((c.text or "") for c in e.iter()))) for e in v2.iter("error")]
                rec["errs_after_swap"] = errs
                if not errs:
                    rec["bypassed"] = "clean after swap"; out["visits"].append(rec); print(json.dumps(rec)[:700], flush=True); continue
        only_adv = bool(errs) and all(pattern in e[1] for e in errs)
        gate_ok = not any(g["first_never_primary"] for g in rec["gate"])
        mod_ok = True
        if pattern == "Pattern 35790":
            # the add-on line must carry 25 and the 99487 line must not; pcode492677 = 99489, pcode492676 = 99487 on this chart
            for g in rec["gate"]:
                if g["cpt"] == "pcode492677" and "25" not in g["mods"]: mod_ok = False
                if g["cpt"] == "pcode492676" and "25" in g["mods"]: mod_ok = False
        rec["only_adv"] = only_adv; rec["gate_ok"] = gate_ok; rec["mod_ok"] = mod_ok
        if only_adv and gate_ok and mod_ok:
            if not LIVE: rec["bypassed"] = "dry"
            else:
                r = amd.post(amd.msg("bypassclaimedits", "chargeentry", {"nocookie": "1"}, '<visitlist><visit id="%s"><claimeditlist>%s</claimeditlist></visit></visitlist>' % (vid, "".join('<claimedit id="%s"/>' % e[0] for e in errs))))
                rec["bypassed"] = "Fault" not in r; rec["resp"] = r[:200]
                if pattern == "Pattern 11256" and rec["bypassed"]:
                    open("laterality_flag_log.md", "a").write("- %s run %s: pat%s visit %s charges %s - Pattern 11256 M25.559 (pain in unspecified hip) + S70.00XA (contusion of unspecified hip) bypassed as advisory; documentation may support a laterality code (William)\n" % (datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%MZ"), STAMP, rec["pid"], vid, ",".join(chgs)))
        else:
            rec["bypassed"] = "held"
        out["visits"].append(rec); print(json.dumps(rec)[:700], flush=True); time.sleep(0.3)
json.dump(out, open("registers/insp_%s%s.json" % (STAMP, "" if LIVE else "_dry"), "w"), indent=1)
print("SUMMARY", [(r["vid"], r["bypassed"]) for r in out["visits"]])
