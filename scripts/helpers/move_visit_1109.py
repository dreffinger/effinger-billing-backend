# PLAIN ENGLISH (Move a feed visit off a duplicate placeholder chart onto the real chart, 11/9/2026)
# Decides: Nothing. William's standing answer (board row smith-myrtle-17478345, 11/9/2026): "if a duplicate chart shows up
#          with visits in it just put the visits in the proper chart"; he named the old chart as the correct one. AMD has no
#          call that re-points a visit at another patient, so this does it the way the Claimocity importer enters any visit:
#          the proven two-step create on the TARGET chart (addvisit <appt> makes the empty visit, then
#          updvisitwithnewcharges adds the charge), and only once the new charge is verified live does it void the charge on
#          the placeholder chart.
# Rules it uses: Reads the source charge live and copies its DOS, procedure, diagnoses, modifiers, POS, units and fee
#          unchanged; takes the episode / profile / facility / referral plan / insurance order from the TARGET chart's own
#          most recent visit; refuses if the source carries a payment, if the target already holds the same CPT on that DOS
#          (the importer's same-DOS dedupe), or if the new charge cannot be read back.
# Never touches: Any other visit on either chart. The placeholder chart itself is left in place for William to merge.
# Usage: python3 move_visit_1109.py <source_pid> <source_chargeid> <target_pid> [--live]
# Register: registers/move_visit_1109.json
import json, os, re, sys, time
import xml.etree.ElementTree as ET
import amd, resave, txh, void_tx

args = [a for a in sys.argv[1:] if not a.startswith("--")]
SPID, SCID, TPID = args[0], args[1], args[2]
live = "--live" in sys.argv
amd.login_cached()

# ---- source
sroot = ET.fromstring(resave.detail(SCID))
sc = [c for c in sroot.iter("charge") if c.get("id") == "charge" + SCID]
if not sc: print("source charge%s not found" % SCID); sys.exit(1)
sc = sc[0]; svis = sroot.find(".//visit")
pays = [p.attrib for p in sc.iter("payment") if float(p.attrib.get("amount") or 0) != 0]
if pays: print("REFUSED - a payment is posted on the source charge:", pays); sys.exit(1)
src = {k: sc.get(k) for k in ("proccode", "begindate", "enddate", "diagcodes", "modcodes", "pos", "tos", "units", "fee", "aging")}
print("source  pat%s chg%s vst%s : %s" % (SPID, SCID, re.sub(r"\D", "", svis.get("id")), src))

# ---- target context from its own most recent visit
troot = txh.fetch(TPID)
tcs = [c.attrib for c in troot.iter("charge") if c.attrib.get("void") != "1" and c.attrib.get("dos")]
if not tcs: print("target pat%s has no visit to copy context from" % TPID); sys.exit(1)
dup = [c for c in tcs if c.get("dos") == src["begindate"] and c.get("proccode") == src["proccode"]]
if dup: print("REFUSED - target already holds %s on %s:" % (src["proccode"], src["begindate"]), dup); sys.exit(1)
tcs.sort(key=lambda a: (a.get("dos") or ""))
tdet = ET.fromstring(resave.detail(tcs[-1]["id"]))
tvis = tdet.find(".//visit")
tpat = tdet.find(".//patient")
resp = None
d = ET.fromstring(amd.post(amd.msg("getdemographic", "demographics", {"patientid": TPID, "nocookie": "1"})))
for rp in d.iter("respparty"): resp = rp.attrib.get("id"); break
ctx = {"episode": tvis.get("episode"), "profile": tvis.get("profile"), "facility": tvis.get("facility"),
       "refplan": tvis.get("refplan"), "insorder": d.find(".//patient").attrib.get("insorder") or tvis.get("insorder"),
       "onhcfa": svis.get("onhcfa") or tvis.get("onhcfa") or "0", "resp": resp}
print("target  pat%s context: %s" % (TPID, ctx))

dcodes = (src["diagcodes"] or "").split()
chg = ('<charge id="" respparty="%s" begindate="%s" enddate="%s" diagcodes="%s" modcodes="%s" aging="%s" billins="1" '
       'proccode="%s" cobcode="" pos="%s" tos="%s" units="%s" netfee="0" fee="%s" allowed="%s" patportion="0.00" '
       'insportion="%s" patbalance="0.00" insbalance="%s" finclasscode="MC" lineitemnote=""><diagcodelist>%s</diagcodelist></charge>') % (
    ctx["resp"], src["begindate"], src["enddate"], src["diagcodes"], src["modcodes"] or "", src["aging"] or src["begindate"],
    src["proccode"], src["pos"], src["tos"] or "01", src["units"] or "1", src["fee"], src["fee"], src["fee"], src["fee"],
    "".join('<diagcode id="%s"/>' % re.sub(r"\D", "", x) for x in dcodes))
appt = ('<appt id="" patient="pat%s" episode="%s" date="%s" profile="%s" facility="%s" refplan="%s" insorder="%s" onhcfa="%s" '
        'acceptassign="1" forcepaper="0" isappt="0" note="" billingnote="" referenceid=""/>') % (
    TPID, ctx["episode"], src["begindate"], ctx["profile"], ctx["facility"], ctx["refplan"], ctx["insorder"], ctx["onhcfa"])

if not live:
    print("DRY would addvisit on pat%s then add 1 charge %s %s fee %s, then void source chg%s" % (TPID, src["proccode"], src["begindate"], src["fee"], SCID))
    sys.exit(0)

r0 = amd.post(amd.msg("addvisit", "chargeentry", {"patientid": "pat" + TPID, "episodeid": ctx["episode"], "approval": "1",
              "inspectorenabled": "1", "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"}, appt))
if "Fault" in r0: print("FAULT addvisit:", re.sub(r"\s+", " ", r0[:400])); sys.exit(1)
m = re.search(r'<visit id="(vst\d+)"', r0) or re.search(r'id="(vst\d+)"', r0)
if not m: print("addvisit gave no visit id:", re.sub(r"\s+", " ", r0[:400])); sys.exit(1)
NEWV = m.group(1)
print("addvisit ->", NEWV)
time.sleep(0.8)

vis = ('<visit id="%s" date="%s" profile="%s" facility="%s" refplan="%s" insorder="%s" onhcfa="%s" acceptassign="1" '
       'forcepaper="0" force="1"><chargelist>%s</chargelist></visit>') % (
    NEWV, src["begindate"], ctx["profile"], ctx["facility"], ctx["refplan"], ctx["insorder"], ctx["onhcfa"], chg)
r1 = amd.post(amd.msg("updvisitwithnewcharges", "chargeentry", {"patientid": "pat" + TPID, "episodeid": ctx["episode"],
              "approval": "1", "inspectorenabled": "1", "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"}, vis))
if "Fault" in r1: print("FAULT updvisitwithnewcharges:", re.sub(r"\s+", " ", r1[:400])); sys.exit(1)
time.sleep(1.0)

back = txh.fetch(TPID)
newc = [c.attrib for c in back.iter("charge")
        if c.attrib.get("void") != "1" and c.attrib.get("dos") == src["begindate"] and c.attrib.get("proccode") == src["proccode"]]
print("verify on target:", newc)
if not newc:
    print("NOT VOIDING the source - the new charge could not be read back on pat%s" % TPID); sys.exit(1)

ok, msg = void_tx.void_charge(SPID, SCID)
print("void source chg%s -> %s %s" % (SCID, ok, msg))
os.makedirs("registers", exist_ok=True)
reg = json.load(open("registers/move_visit_1109.json")) if os.path.exists("registers/move_visit_1109.json") else []
reg.append({"source": {"pid": SPID, "charge": SCID, "visit": re.sub(r"\D", "", svis.get("id")), "voided": ok},
            "target": {"pid": TPID, "visit": NEWV, "charges": newc}, "copied": src, "ctx": ctx,
            "why": "William 11/9/2026: duplicate placeholder chart - put the visit in the proper (old) chart"})
json.dump(reg, open("registers/move_visit_1109.json", "w"), indent=1)
print("register -> registers/move_visit_1109.json")
