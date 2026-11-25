#!/usr/bin/env python3
# PLAIN ENGLISH (Enter ONE visit on a chart from the words of a feed message William ordered entered - 11/25/2026)
# Decides: nothing. William 11/25/2026 on card garland-g-mercy-[first]-17478434: the 11/09/2026 feed message (99309 + G0439, feed id
#          65d64419b78e42196e835c6c, file 20261117) was never entered because the import's code table did not know G0439; he said 'move awv
#          to the next day after that'. This enters a visit the way the charge feed enters any visit - the proven two-step create (addvisit,
#          then updvisitwithnewcharges) - with the date, procedure(s), fee(s), diagnoses (resolved to AdvancedMD's own ids by lookupdiagcode,
#          codeset 10), place of service and clinician given on the command line; the episode and referral plan come from the chart's own
#          most recent visit, the insurance order from the chart. Refuses when the chart already holds one of the codes on that date; reads
#          every new charge back (procedure, fee, place of service) before it says done.
# Never touches: any other visit, plan or balance. Usage:
#   python3 enter_visit_1125.py <pid> <mm/dd/yyyy> --proc <pcode>:<CPT>:<fee>[,...] --dx <ICD>[,...] --pos 32 --profile prof15 --facility fac33 [--live]
# Register: registers/enter_visit_1125.json
import json, os, re, sys, time
import xml.etree.ElementTree as ET
import amd, resave, txh
def opt(k, d=None): return sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
args = [a for a in sys.argv[1:] if not a.startswith("--")]; PID, DOS = args[0], args[1]
PROCS = [p.split(":") for p in opt("--proc").split(",")]; DX = opt("--dx").split(","); POS = opt("--pos", "31"); PROF = opt("--profile"); FAC = opt("--facility")
live = "--live" in sys.argv
amd.login_cached()
dcodes = []
for code in DX:
    r = amd.post(amd.msg("lookupdiagcode", "lookup", {"code": code, "codeset": "10", "nocookie": "1"}))
    m = [x for x in re.findall(r'<diagcode id="(dcode\d+)" code="([^"]*)"', r) if x[1] == code]
    if not m: print("diagnosis %s is not in AdvancedMD's list - stop" % code); sys.exit(2)
    dcodes.append(m[0][0])
root = txh.fetch(PID)
tcs = [c.attrib for c in root.iter("charge") if c.attrib.get("void") != "1" and c.attrib.get("dos")]
dup = [c for c in tcs if c.get("dos") == DOS and c.get("proccode") in {p[0] for p in PROCS}]
if dup: print("REFUSED - chart already holds a code of this visit on %s:" % DOS, [(d.get("id"), d.get("proccode")) for d in dup]); sys.exit(1)
tcs.sort(key=lambda a: (a.get("dos") or "")[-4:] + (a.get("dos") or "")[:5])
tdet = ET.fromstring(resave.detail(tcs[-1]["id"])); tvis = tdet.find(".//visit")
d = ET.fromstring(amd.post(amd.msg("getdemographic", "demographics", {"patientid": PID, "nocookie": "1"})))
resp = next((rp.attrib.get("id") for rp in d.iter("respparty")), None)
ctx = {"episode": tvis.get("episode"), "profile": PROF or tvis.get("profile"), "facility": FAC or tvis.get("facility"), "refplan": tvis.get("refplan"),
       "insorder": d.find(".//patient").attrib.get("insorder") or tvis.get("insorder"), "onhcfa": "0", "resp": resp}
print("pat%s %s: %s dx %s pos %s | context %s" % (PID, DOS, PROCS, DX, POS, ctx))
dxl = "".join('<diagcode id="%s"/>' % re.sub(r"\D", "", x) for x in dcodes)
chg = "".join(('<charge id="" respparty="%s" begindate="%s" enddate="%s" diagcodes="%s" modcodes="" aging="%s" billins="1" proccode="%s" cobcode="" pos="%s" tos="01" units="1" '
                'netfee="0" fee="%s" allowed="%s" patportion="0.00" insportion="%s" patbalance="0.00" insbalance="%s" finclasscode="MC" lineitemnote=""><diagcodelist>%s</diagcodelist></charge>')
               % (resp, DOS, DOS, " ".join(dcodes), DOS, p[0], POS, p[2], p[2], p[2], p[2], dxl) for p in PROCS)
appt = ('<appt id="" patient="pat%s" episode="%s" date="%s" profile="%s" facility="%s" refplan="%s" insorder="%s" onhcfa="0" acceptassign="1" forcepaper="0" isappt="0" note="" billingnote="" referenceid=""/>') % (
    PID, ctx["episode"], DOS, ctx["profile"], ctx["facility"], ctx["refplan"], ctx["insorder"])
if not live: print("DRY would addvisit then add %d charge(s)" % len(PROCS)); sys.exit(0)
r0 = amd.post(amd.msg("addvisit", "chargeentry", {"patientid": "pat" + PID, "episodeid": ctx["episode"], "approval": "1", "inspectorenabled": "1", "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"}, appt))
if "Fault" in r0: print("FAULT addvisit:", re.sub(r"\s+", " ", r0[:400])); sys.exit(1)
m = re.search(r'<visit id="(vst\d+)"', r0) or re.search(r'id="(vst\d+)"', r0)
if not m: print("addvisit gave no visit id:", re.sub(r"\s+", " ", r0[:400])); sys.exit(1)
NEWV = m.group(1); print("addvisit ->", NEWV); time.sleep(0.8)
vis = ('<visit id="%s" date="%s" profile="%s" facility="%s" refplan="%s" insorder="%s" onhcfa="0" acceptassign="1" forcepaper="0" force="1"><chargelist>%s</chargelist></visit>') % (
    NEWV, DOS, ctx["profile"], ctx["facility"], ctx["refplan"], ctx["insorder"], chg)
r1 = amd.post(amd.msg("updvisitwithnewcharges", "chargeentry", {"patientid": "pat" + PID, "episodeid": ctx["episode"], "approval": "1", "inspectorenabled": "1", "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"}, vis))
if "Fault" in r1: print("FAULT updvisitwithnewcharges:", re.sub(r"\s+", " ", r1[:400])); sys.exit(1)
time.sleep(1.0)
back = txh.fetch(PID)
newc = [c.attrib for c in back.iter("charge") if c.attrib.get("void") != "1" and re.sub(r"\D", "", c.attrib.get("visit") or "") == re.sub(r"\D", "", NEWV)]
pos_back = re.findall(r'<charge [^>]*\bpos="(\d+)"', resave.detail(newc[0]["id"])) if newc else []
print("verify:", [(n.get("id"), n.get("proccode"), n.get("fee"), n.get("dos")) for n in newc], "pos", pos_back)
reg = json.load(open("registers/enter_visit_1125.json")) if os.path.exists("registers/enter_visit_1125.json") else []
reg.append({"pid": PID, "dos": DOS, "visit": NEWV, "charges": newc, "procs": PROCS, "dx": DX, "pos": POS, "pos_back": pos_back, "ctx": ctx, "why": "William 11/25/2026 - card garland-g-mercy-[first]-17478434"})
json.dump(reg, open("registers/enter_visit_1125.json", "w"), indent=1)
