# PLAIN ENGLISH (visit insurance order + Unbilled release, written 10/1/2026 run 2026-10-01T0510Z - the generic named helper for
#   the two Unbilled fixes the standing rules already allow: (a) 'Date of service is outside insurance coverage effective dates'
#   = the VISIT insorder still lists an end-dated plan -> resave the visit with the live order only; (b) 'Insurance order is missing
#   on visit' once the correct plan is on the chart (cascade done, AMD 271 ACTIVE) -> resave the visit with that order; then
#   hideunbillablevisits (the Unbilled 'release'). Also used as release-only (no --order) after another named helper fixed the
#   chart, e.g. the MSP code on a Medicare seq-2 plan (ins_update.py mspcode=).
# Decides: nothing on its own - the caller names the patient, ONE live charge of the visit (the anchor), the order to write and
#   whether to release. The full-visit echo (resave.visit_charges) re-sends EVERY live charge so none is voided; onhcfa=1 is set
#   with the order (Box 18 / claim print flag, the proven shape of apply_0928_2310.resave_full). Reads the visit back and refuses
#   to release when the readback order differs from what was asked.
# Never touches: diagnosis codes, modifiers, dates, plans, payments, balances, any other visit.
#   python3 visit_order_release.py <patientid> <anchor chargeid> [--order "2"] [--release]          # dry: prints what it would do
#   python3 visit_order_release.py <patientid> <anchor chargeid> [--order "2"] [--release] --live   # writes; register registers/visit_order_release_<stamp>.json
import amd, resave, payreasons, json, re, sys, time, os, datetime
a = sys.argv[1:]
LIVE = "--live" in a; REL = "--release" in a
pid = re.sub(r"\D", "", a[0]); cid = re.sub(r"\D", "", a[1])
order = a[a.index("--order") + 1] if "--order" in a else None
stamp = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H%MZ")
os.makedirs("registers", exist_ok=True)
amd.login_cached()
vis, pat, allc = resave.visit_charges(cid)
vid = re.sub(r"\D", "", vis.get("id"))
rec = {"stamp": stamp, "live": LIVE, "pid": pid, "vid": vid, "anchor": cid, "order_before": vis.get("insorder"),
       "onhcfa_before": vis.get("onhcfa"), "order_asked": order, "charges": [c.get("id") for c in allc], "release_asked": REL}
if re.sub(r"\D", "", pat.get("id")) != pid:
    rec["error"] = "anchor charge belongs to patient %s, not %s - nothing done" % (pat.get("id"), pid); print(json.dumps(rec)); sys.exit(2)
def resave_full(insorder):
    chg = ""
    for c in allc:
        at = {"id": c.get("id")}
        for f in resave.CHG_FIELDS:
            if c.get(f) is not None: at[f] = c.get(f)
        chg += "<charge %s/>" % " ".join('%s="%s"' % (k, v) for k, v in at.items())
    va = dict(vis.attrib); va["force"] = "1"; va["insorder"] = insorder; va["onhcfa"] = "1"
    r = amd.post(amd.msg("updvisitwithcharges", "chargeentry", {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1", "inspectorenabled": "1", "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"}, "<visit %s><chargelist>%s</chargelist></visit>" % (" ".join('%s="%s"' % (k, v) for k, v in va.items()), chg)), timeout=180)
    if "Fault" in r: return False, "FAULT " + re.sub(r"\s+", " ", r[:200]), None
    time.sleep(0.6); v2, p2, c2 = resave.visit_charges(cid)
    return len(c2) == len(allc), "saved live=%d/%d insorder=%s onhcfa=%s" % (len(c2), len(allc), v2.get("insorder"), v2.get("onhcfa")), v2
if order is not None:
    if not LIVE:
        rec["resave"] = "dry: would resave %d charge(s) with insorder=%s onhcfa=1" % (len(allc), order)
    else:
        ok, msg, v2 = resave_full(order); rec["resave"] = msg
        if not ok or (v2 is not None and v2.get("insorder") != order):
            rec["release"] = "held - resave not clean"; print(json.dumps(rec)); open("registers/visit_order_release_%s.json" % stamp, "a").write(json.dumps(rec) + "\n"); sys.exit(1)
if REL:
    rec["release"] = payreasons.release_visit(vid) if LIVE else "dry: would release vst%s" % vid
print(json.dumps(rec))
if LIVE: open("registers/visit_order_release_%s.json" % stamp, "a").write(json.dumps(rec) + "\n")
