#!/usr/bin/env python3
# PLAIN ENGLISH (Move a WHOLE visit - every live charge of it - from the wrong chart to the right chart, 11/25/2026)
# Decides: nothing. William 11/25/2026 on the Castellane cards: 'they should be billed to the young castellane if they are not duplicates
#          with the young chart already billed' / 'void the old ones'. move_visit_1109.py moves ONE charge and makes one visit per charge;
#          a care-management visit (99487 + 99489) must stay ONE visit (the add-on rides the same claim), so this one copies every live
#          charge of the source visit into ONE new visit on the target chart - the proven two-step create of the charge feed (addvisit,
#          then updvisitwithnewcharges with the whole charge list) - and only once every new charge is read back live does it void the
#          source charges one by one.
# Rules it uses: copies DOS, procedure, diagnoses, modifiers, units and fee unchanged; the place of service is given on the command line
#          (the standing rule: care management 32; a monthly nursing visit of a long-term resident 32) or kept as the source carries it;
#          episode / profile / facility / referral plan from the target chart's own most recent visit, the insurance order from the target
#          chart (Medicare first); refuses when any source charge carries a real payment, when the target already holds one of the codes
#          on that date, or when a new charge cannot be read back (then nothing is voided).
# Never touches: any other visit on either chart. Usage: python3 move_visit_1125.py <source_pid> <source_visitid> <target_pid> [--pos 32] [--live]
# Register: registers/move_visit_1125.json
import json, os, re, sys, time
import xml.etree.ElementTree as ET
import amd, resave, txh, void_tx
args = [a for a in sys.argv[1:] if not a.startswith("--")]
SPID, SVID, TPID = args[0], args[1], args[2]
POS = sys.argv[sys.argv.index("--pos") + 1] if "--pos" in sys.argv else None
live = "--live" in sys.argv
amd.login_cached()
# ---- source: every live charge of the visit
sroot = txh.fetch(SPID)
scs = [c for c in sroot.iter("charge") if c.get("void") != "1" and re.sub(r"\D", "", c.get("visit") or "") == SVID]
if not scs: print("source visit %s not found on pat%s" % (SVID, SPID)); sys.exit(1)
for c in scs:
    pays = [p.attrib for p in c.iter("payment") if p.get("void") != "1" and abs(float(p.get("amount") or 0)) > 0.001]
    if pays: print("REFUSED - a real payment is posted on source charge %s:" % c.get("id"), pays); sys.exit(1)
src = []
for c in scs:
    det = ET.fromstring(resave.detail(c.get("id"))); sc = [x for x in det.iter("charge") if x.get("id") == "charge" + c.get("id")][0]; svis = det.find(".//visit")
    src.append({k: sc.get(k) for k in ("id", "proccode", "begindate", "enddate", "diagcodes", "modcodes", "pos", "tos", "units", "fee", "aging")})
dos = src[0]["begindate"]
print("source pat%s vst%s %s: %s" % (SPID, SVID, dos, [(s["id"], s["proccode"], s["pos"], s["fee"], s["modcodes"]) for s in src]))
# ---- target context
troot = txh.fetch(TPID)
tcs = [c.attrib for c in troot.iter("charge") if c.attrib.get("void") != "1" and c.attrib.get("dos")]
if not tcs: print("target pat%s has no visit to copy context from" % TPID); sys.exit(1)
dup = [c for c in tcs if c.get("dos") == dos and c.get("proccode") in {s["proccode"] for s in src}]
if dup: print("REFUSED - target already holds a code of this visit on %s:" % dos, [(d.get("id"), d.get("proccode")) for d in dup]); sys.exit(1)
tcs.sort(key=lambda a: (a.get("dos") or "")[-4:] + (a.get("dos") or "")[:5])
tdet = ET.fromstring(resave.detail(tcs[-1]["id"])); tvis = tdet.find(".//visit")
d = ET.fromstring(amd.post(amd.msg("getdemographic", "demographics", {"patientid": TPID, "nocookie": "1"})))
resp = next((rp.attrib.get("id") for rp in d.iter("respparty")), None)
# the clinician and the building are the OLD visit's own (the one who saw him, where); episode / referral plan / order are the target chart's
ctx = {"episode": tvis.get("episode"), "profile": svis.get("profile") or tvis.get("profile"), "facility": svis.get("facility") or tvis.get("facility"), "refplan": tvis.get("refplan"),
       "insorder": d.find(".//patient").attrib.get("insorder") or tvis.get("insorder"), "onhcfa": svis.get("onhcfa") or tvis.get("onhcfa") or "0", "resp": resp}
print("target pat%s context: %s (from its visit of %s)" % (TPID, ctx, tcs[-1].get("dos")))
chg = ""
for s in src:
    pos = POS or s["pos"]
    chg += ('<charge id="" respparty="%s" begindate="%s" enddate="%s" diagcodes="%s" modcodes="%s" aging="%s" billins="1" proccode="%s" cobcode="" pos="%s" '
            'tos="%s" units="%s" netfee="0" fee="%s" allowed="%s" patportion="0.00" insportion="%s" patbalance="0.00" insbalance="%s" finclasscode="MC" lineitemnote="">'
            '<diagcodelist>%s</diagcodelist></charge>') % (ctx["resp"], s["begindate"], s["enddate"], s["diagcodes"], s["modcodes"] or "", s["aging"] or s["begindate"],
            s["proccode"], pos, s["tos"] or "01", s["units"] or "1", s["fee"], s["fee"], s["fee"], s["fee"], "".join('<diagcode id="%s"/>' % re.sub(r"\D", "", x) for x in (s["diagcodes"] or "").split()))
appt = ('<appt id="" patient="pat%s" episode="%s" date="%s" profile="%s" facility="%s" refplan="%s" insorder="%s" onhcfa="%s" acceptassign="1" forcepaper="0" isappt="0" note="" billingnote="" referenceid=""/>') % (
    TPID, ctx["episode"], dos, ctx["profile"], ctx["facility"], ctx["refplan"], ctx["insorder"], ctx["onhcfa"])
if not live:
    print("DRY would addvisit on pat%s for %s then add %d charge(s) %s at POS %s, then void source charges %s" % (TPID, dos, len(src), [s["proccode"] for s in src], POS or "as source", [s["id"] for s in src])); sys.exit(0)
r0 = amd.post(amd.msg("addvisit", "chargeentry", {"patientid": "pat" + TPID, "episodeid": ctx["episode"], "approval": "1", "inspectorenabled": "1", "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"}, appt))
if "Fault" in r0: print("FAULT addvisit:", re.sub(r"\s+", " ", r0[:400])); sys.exit(1)
m = re.search(r'<visit id="(vst\d+)"', r0) or re.search(r'id="(vst\d+)"', r0)
if not m: print("addvisit gave no visit id:", re.sub(r"\s+", " ", r0[:400])); sys.exit(1)
NEWV = m.group(1); print("addvisit ->", NEWV); time.sleep(0.8)
vis = ('<visit id="%s" date="%s" profile="%s" facility="%s" refplan="%s" insorder="%s" onhcfa="%s" acceptassign="1" forcepaper="0" force="1"><chargelist>%s</chargelist></visit>') % (
    NEWV, dos, ctx["profile"], ctx["facility"], ctx["refplan"], ctx["insorder"], ctx["onhcfa"], chg)
r1 = amd.post(amd.msg("updvisitwithnewcharges", "chargeentry", {"patientid": "pat" + TPID, "episodeid": ctx["episode"], "approval": "1", "inspectorenabled": "1", "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"}, vis))
if "Fault" in r1: print("FAULT updvisitwithnewcharges:", re.sub(r"\s+", " ", r1[:400])); sys.exit(1)
time.sleep(1.0)
back = txh.fetch(TPID)
newc = [c.attrib for c in back.iter("charge") if c.attrib.get("void") != "1" and c.attrib.get("dos") == dos and re.sub(r"\D", "", c.attrib.get("visit") or "") == re.sub(r"\D", "", NEWV)]
print("verify on target:", [(n.get("id"), n.get("proccode"), n.get("fee"), n.get("pos")) for n in newc])
if len(newc) != len(src): print("NOT VOIDING the source - %d of %d new charges read back on pat%s" % (len(newc), len(src), TPID)); sys.exit(1)
voided = []
for s in src:
    # a $0 posting (a payer's $0 answer) on the old charge is voided first, as a charge after a date of death is voided ([DOB] lesson)
    c0 = [c for c in scs if re.sub(r"\D", "", c.get("id") or "") == re.sub(r"\D", "", s["id"])][0]
    for p in c0.iter("payment"):
        if p.get("void") != "1": okp, msgp = void_tx.void_payment(SPID, s["id"], p.get("id")); print("  void $0 payment %s on charge %s -> %s" % (p.get("id"), s["id"], okp))
    for w in c0.iter("writeoff"):
        if w.get("void") != "1": okw, msgw = void_tx.void_writeoff(SPID, s["id"], w.get("id")); print("  void write-off %s on charge %s -> %s" % (w.get("id"), s["id"], okw))
    ok, msg = void_tx.void_charge(SPID, s["id"]); voided.append((s["id"], ok)); print("void source charge %s -> %s %s" % (s["id"], ok, msg[:120]))
reg = json.load(open("registers/move_visit_1125.json")) if os.path.exists("registers/move_visit_1125.json") else []
reg.append({"source": {"pid": SPID, "visit": SVID, "charges": [s["id"] for s in src], "voided": voided}, "target": {"pid": TPID, "visit": NEWV, "charges": newc}, "pos": POS, "ctx": ctx,
            "why": "William 11/25/2026: the visits of 2024-2026 on chart 20752 are the younger Castellane's (12182776) - bill them there if not duplicates, void the old ones"})
json.dump(reg, open("registers/move_visit_1125.json", "w"), indent=1); print("register -> registers/move_visit_1125.json")
