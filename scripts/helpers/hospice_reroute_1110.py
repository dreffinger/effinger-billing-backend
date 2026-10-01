# PLAIN ENGLISH (hospice re-route to Medicare + GV, 7 AM ET 10/1/2026 run 2026-10-01T1110Z - UHC ERA check 1052921 / W0616257)
# Decides: nothing new - applies William's 9/20/2026 standing rule "a hospice denial (CO-B9 / PR-B9) = straight Medicare + the GV
#   modifier, rebilled as an original claim" to the visits named in VISITS: UHC (UNI20 / UHCMA) answered CO-B9 'enrolled in hospice'
#   on them and the chart already carries a Medicare plan at the sequence given. Per visit: read the live charges (full-visit echo),
#   refuse when the NET of the non-void payments on the visit is money (a paid-then-recouped visit nets $0 and is allowed - that is
#   what UHC's takeback means), add GV (mcode713) through gv_rebill.add_gv to every live charge that lacks it (gv_visit.py refuses a
#   visit where one charge already carries GV - the 5/17 and 6/25 CCM visits of pat21263 and the 5/17 / 7/17 ones of pat17473477 have
#   GV on the 99487 but not on the 99489 / were never re-sent), verify GV is on every live charge, then freq1_visit.run (frequency 1,
#   no payer reference, chargerebill to the Medicare sequence). --dry (default) only reads and prints the plan; --live writes.
# Never touches: payments, write-offs, plans, any visit not in VISITS. Register: registers/hospice_reroute_2026-10-01T1110Z[_dry].json
import amd, resave, gv_rebill, freq1_visit, json, re, sys, time
import xml.etree.ElementTree as ET
LIVE = "--live" in sys.argv; S = "2026-10-01T1110Z"; GV = "mcode713"
# (patientid, anchor chargeid, Medicare plan sequence, why)
VISITS = [
    ("22023", "23326012", "1", "UHCMA CO-B9 10/25/2025 99487"),
    ("22023", "23334147", "1", "UHCMA CO-B9 12/28/2025 99487"),
    ("22023", "23337128", "1", "UHCMA CO-B9 01/27/2026 99487"),
    ("22023", "23338626", "1", "UHCMA CO-B9 02/02/2026 99307"),
    ("21263", "23350599", "1", "UNI20 OA-18/CO-B9 05/17/2026 99487+99489 (GV on 99487 only)"),
    ("21263", "23355341", "1", "UNI20 CO-B9 06/25/2026 99487+99489 (GV on 99487 only)"),
    ("21263", "23326392", "1", "UNI20 CO-B9 10/25/2025 99487+99489 (paid then recouped, net $0)"),
    ("17473477", "23350410", "2", "UNI20 CO-B9 05/17/2026 99487 (GV present, never re-sent; DOS before the 9/15/2026 date of death)"),
    ("17473477", "23358095", "2", "UNI20 CO-B9 07/17/2026 99487 (GV present, never re-sent; DOS before the 9/15/2026 date of death)"),
]
amd.login_cached(); reg = []
for pid, cid, seq, why in VISITS:
    rec = {"stamp": S, "live": LIVE, "pid": pid, "anchor": cid, "seq": seq, "why": why}
    try:
        vis, pat, allc = resave.visit_charges(cid); vid = re.sub(r"\D", "", vis.get("id"))
    except Exception as e:
        rec["result"] = "ERROR reading visit: %s" % str(e)[:120]; print(json.dumps(rec)); reg.append(rec); continue
    rec["vid"] = vid
    if re.sub(r"\D", "", pat.get("id")) != pid:
        rec["result"] = "REFUSED - anchor charge belongs to %s" % pat.get("id"); print(json.dumps(rec)); reg.append(rec); continue
    rec["charges"] = [{"id": c.get("id"), "proc": c.get("proccode"), "mods": c.get("modcodes"), "insbalance": c.get("insbalance")} for c in allc]
    th = ET.fromstring(amd.post(amd.msg('gettxhistory', 'demographics', {'patientid': pid, 'filterhistory': '0', 'pagenumber': '1', 'typefilter': '0', 'sortbypayment': 'false', 'groupbyvisit': '0', 'sortdescending': '1', 'visitid': vid, 'profileid': '', 'getmemo': 'false', 'nocookie': '1'}), timeout=120))
    pays = [(p.get("id"), float(p.get("amount") or 0)) for p in th.iter("payment") if p.get("void") != "1" and abs(float(p.get("amount") or 0)) > 0]
    net = round(sum(a for _, a in pays), 2); rec["payments"] = pays; rec["net_paid"] = net
    time.sleep(0.4)
    if abs(net) > 0.005:
        rec["result"] = "REFUSED - non-void payments net $%.2f on the visit; not a GV rebill case" % net; print(json.dumps(rec)); reg.append(rec); continue
    missing = [c.get("id") for c in allc if GV not in (c.get("modcodes") or "")]
    rec["gv_missing_before"] = missing
    if not LIVE:
        rec["result"] = "dry: would add GV to %d charge(s) %s then frequency-1 rebill seq %s" % (len(missing), missing, seq); print(json.dumps(rec)); reg.append(rec); continue
    if missing:
        rec["add_gv"] = str(gv_rebill.add_gv(cid))[:160]; time.sleep(0.6)
    v2, p2, c2 = resave.visit_charges(cid); rec["mods_after"] = [(c.get("id"), c.get("modcodes")) for c in c2]
    if len(c2) != len(allc) or not all(GV in (c.get("modcodes") or "") for c in c2):
        rec["result"] = "GV not on every live charge after the echo (or charge count changed) - NOT rebilled"; print(json.dumps(rec)); reg.append(rec); continue
    rec["rebill"] = str(freq1_visit.run(vid, cid, seq))[:200]; time.sleep(0.5)
    rec["result"] = "GV on every charge + frequency-1 rebill seq %s" % seq
    print(json.dumps(rec)); reg.append(rec)
    open("registers/hospice_gv_register.json", "a").write(json.dumps(rec) + "\n")
json.dump(reg, open("registers/hospice_reroute_%s%s.json" % (S, "" if LIVE else "_dry"), "w"), indent=1)
print("DONE", "LIVE" if LIVE else "dry", sum(1 for r in reg if r.get("rebill")), "rebilled of", len(reg))
