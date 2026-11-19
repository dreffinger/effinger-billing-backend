# PLAIN ENGLISH (Re-enter one denied visit line on another date under another code, then void the old line - 11/19/2026)
# Decides: Nothing. William in chat 11/19/2026: "there was one bcbs one denied for initial code 99344 that should have been a
#          99349, that date of service was a day early anyway push it to the next date we were on site with her that day too
#          and bill a 99349 and void the 99344". AdvancedMD cannot change a charge's code in place without voiding it (the
#          recode trap), so this enters a NEW visit on the SAME chart for the date and code he names - the proven two-step
#          create of the charge feed (addvisit, then updvisitwithnewcharges) - copying the old line's diagnoses, modifiers,
#          place of service and units, and the old visit's own clinician, building, referral plan and insurance order. Only
#          after the new charge is read back live does it void the old line's write-off and $0 denial posting and then the
#          old charge itself.
# Rules it uses: refuses when the old line carries real money (a payment that is not $0); refuses when the chart already
#          holds the new code on the new date; every other line of the old visit is left exactly as it is.
# Never touches: any other charge, visit, plan or balance.
# Usage: python3 redate_recode_1119.py <pid> <old chargeid> <new date mm/dd/yyyy> <new pcode> <new fee> [--live]
# Register: registers/redate_recode_1119.json
import json, os, re, sys, time
import xml.etree.ElementTree as ET
import amd, resave, txh, void_tx
a = [x for x in sys.argv[1:] if not x.startswith("--")]
PID, SCID, NEWDOS, NEWP, NEWFEE = a[0], a[1], a[2], a[3], a[4]
live = "--live" in sys.argv
amd.login_cached()
sroot = ET.fromstring(resave.detail(SCID))
sc = [c for c in sroot.iter("charge") if c.get("id") == "charge" + SCID]
if not sc: print("charge%s not found" % SCID); sys.exit(1)
sc = sc[0]; svis = sroot.find(".//visit")
ch, wos, pays = void_tx.charge_state(SCID)
money = [p for p in pays if p.get("void") != "1" and abs(float(p.get("amount") or 0)) > 0.005]
if money: print("REFUSED - real money is posted on the old line:", [(p.get("id"), p.get("amount")) for p in money]); sys.exit(1)
src = {k: sc.get(k) for k in ("proccode", "begindate", "enddate", "diagcodes", "modcodes", "pos", "tos", "units", "fee")}
print("old line pat%s chg%s %s : %s" % (PID, SCID, svis.get("id"), src))
print("old line postings: writeoffs %s payments %s" % ([(w.get("id"), w.get("amount"), w.get("void")) for w in wos], [(p.get("id"), p.get("amount"), p.get("void")) for p in pays]))
have = [c.attrib for c in txh.fetch(PID).iter("charge") if c.attrib.get("void") != "1" and c.attrib.get("dos") == NEWDOS]
print("chart on %s already holds: %s" % (NEWDOS, [(c.get("id"), c.get("proccode")) for c in have]))
if any(re.match(r"99\d\d\d", c.get("proccode") or "") and (c.get("proccode") or "")[:3] in ("993", "992") for c in have):
    print("REFUSED - the chart already holds a visit code on %s" % NEWDOS); sys.exit(1)
d = amd.post(amd.msg("getdemographic", "demographics", {"patientid": PID, "nocookie": "1"}))
resp = re.search(r'<respparty id="(resp\d+)"', d).group(1)
ctx = {k: svis.get(k) for k in ("episode", "profile", "facility", "refplan", "insorder", "onhcfa")}
print("context from the old visit:", ctx)
dcodes = (src["diagcodes"] or "").split()
chg = ('<charge id="" respparty="%s" begindate="%s" enddate="%s" diagcodes="%s" modcodes="%s" aging="%s" billins="1" '
       'proccode="%s" cobcode="" pos="%s" tos="%s" units="%s" netfee="0" fee="%s" allowed="%s" patportion="0.00" '
       'insportion="%s" patbalance="0.00" insbalance="%s" finclasscode="CC" lineitemnote=""><diagcodelist>%s</diagcodelist></charge>') % (
    resp, NEWDOS, NEWDOS, src["diagcodes"], src["modcodes"] or "", NEWDOS, NEWP, src["pos"], src["tos"] or "01", src["units"] or "1",
    NEWFEE, NEWFEE, NEWFEE, NEWFEE, "".join('<diagcode id="%s"/>' % re.sub(r"\D", "", x) for x in dcodes))
appt = ('<appt id="" patient="pat%s" episode="%s" date="%s" profile="%s" facility="%s" refplan="%s" insorder="%s" onhcfa="%s" '
        'acceptassign="1" forcepaper="0" isappt="0" note="" billingnote="" referenceid=""/>') % (
    PID, ctx["episode"], NEWDOS, ctx["profile"], ctx["facility"], ctx["refplan"], ctx["insorder"], ctx["onhcfa"] or "0")
if not live:
    print("DRY would add a visit %s with %s fee %s (dx %s, pos %s), then void the postings and charge %s" % (NEWDOS, NEWP, NEWFEE, src["diagcodes"], src["pos"], SCID)); sys.exit(0)
hdr = {"patientid": "pat" + PID, "episodeid": ctx["episode"], "approval": "1", "inspectorenabled": "1", "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"}
r0 = amd.post(amd.msg("addvisit", "chargeentry", hdr, appt))
if "Fault" in r0: print("FAULT addvisit:", re.sub(r"\s+", " ", r0[:400])); sys.exit(1)
m = re.search(r'id="(vst\d+)"', r0)
if not m: print("addvisit gave no visit id:", re.sub(r"\s+", " ", r0[:400])); sys.exit(1)
NEWV = m.group(1); print("addvisit ->", NEWV); time.sleep(0.8)
vis = ('<visit id="%s" date="%s" profile="%s" facility="%s" refplan="%s" insorder="%s" onhcfa="%s" acceptassign="1" forcepaper="0" force="1">'
       '<chargelist>%s</chargelist></visit>') % (NEWV, NEWDOS, ctx["profile"], ctx["facility"], ctx["refplan"], ctx["insorder"], ctx["onhcfa"] or "0", chg)
r1 = amd.post(amd.msg("updvisitwithnewcharges", "chargeentry", hdr, vis))
if "Fault" in r1: print("FAULT updvisitwithnewcharges:", re.sub(r"\s+", " ", r1[:400])); sys.exit(1)
time.sleep(1.0)
newc = [c.attrib for c in txh.fetch(PID).iter("charge") if c.attrib.get("void") != "1" and c.attrib.get("dos") == NEWDOS and c.attrib.get("visit") == re.sub(r"\D", "", NEWV)]
print("new charge read back:", [(c.get("id"), c.get("proccode"), c.get("fee"), c.get("insbal"), c.get("provcode"), c.get("faccode")) for c in newc])
if not newc: print("NOT VOIDING the old line - the new charge could not be read back"); sys.exit(1)
res = []
for w in wos:
    if w.get("void") != "1": res.append(("writeoff", w.get("id"), void_tx.void_writeoff(PID, SCID, w.get("id")))); time.sleep(0.4)
for p in pays:
    if p.get("void") != "1": res.append(("payment", p.get("id"), void_tx.void_payment(PID, SCID, p.get("id")))); time.sleep(0.4)
ok, msg = void_tx.void_charge(PID, SCID); res.append(("charge", SCID, (ok, msg)))
for x in res: print("void", x)
os.makedirs("registers", exist_ok=True); f = "registers/redate_recode_1119.json"
reg = json.load(open(f)) if os.path.exists(f) else []
reg.append({"pid": PID, "old_charge": SCID, "old_visit": re.sub(r"\D", "", svis.get("id")), "new_visit": NEWV, "new_dos": NEWDOS, "new_code": NEWP, "fee": NEWFEE,
            "new_charges": [c.get("id") for c in newc], "voids": [(k, i, bool(r[0])) for k, i, r in res], "why": "William 11/19/2026 chat: void the 99344, bill 99349 on the next date"})
json.dump(reg, open(f, "w"), indent=1); print("register ->", f)
