# PLAIN ENGLISH (hospice GV on ONE visit + frequency-1 rebill - written 10/1/2026 run 2026-10-01T0510Z)
# Decides: nothing new - applies William's 9/20/2026 standing rule "a hospice denial (Medicare CO-B9 / PR-B9) = add the GV modifier
#   and rebill the claim" to one named visit when the denial was never posted (a $0 no-pay ERA check that era_clear dismissed), so
#   gv_rebill.py - which finds visits by their POSTED CO-B9 line - cannot see it. Adds GV (mcode713) to every live charge of the
#   visit through gv_rebill.add_gv (full-visit echo), then freq1_visit.run (frequency 1, no payer reference, chargerebill to the
#   plan sequence named). Refuses when a non-void payment > 0 sits on any charge of the visit, or when a charge already carries GV.
# Never touches: payments, write-offs, other visits, the plan list.
#   python3 gv_visit.py <patientid> <anchor chargeid> <plan seq>          # dry: shows the charges, their modifiers and what would change
#   python3 gv_visit.py <patientid> <anchor chargeid> <plan seq> --live   # add GV + rebill; register registers/hospice_gv_register.json (appended)
import amd, resave, gv_rebill, freq1_visit, json, re, sys, os, time, datetime
a = sys.argv[1:]; LIVE = "--live" in a
pid = re.sub(r"\D", "", a[0]); cid = re.sub(r"\D", "", a[1]); seq = a[2]
stamp = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H%MZ"); os.makedirs("registers", exist_ok=True)
amd.login_cached()
vis, pat, allc = resave.visit_charges(cid); vid = re.sub(r"\D", "", vis.get("id"))
rec = {"stamp": stamp, "live": LIVE, "pid": pid, "vid": vid, "anchor": cid, "seq": seq,
       "charges": [{"id": c.get("id"), "proc": c.get("proccode"), "mods": c.get("modcodes"), "insbalance": c.get("insbalance")} for c in allc]}
if re.sub(r"\D", "", pat.get("id")) != pid:
    rec["error"] = "anchor charge belongs to %s, not %s" % (pat.get("id"), pid); print(json.dumps(rec)); sys.exit(2)
# payments on any charge of the visit (gettxhistory, non-void, amount > 0) -> refuse
import xml.etree.ElementTree as ET
th = ET.fromstring(amd.post(amd.msg('gettxhistory', 'demographics', {'patientid': pid, 'filterhistory': '0', 'pagenumber': '1', 'typefilter': '0', 'sortbypayment': 'false', 'groupbyvisit': '0', 'sortdescending': '1', 'visitid': vid, 'profileid': '', 'getmemo': 'false', 'nocookie': '1'}), timeout=120))
paid = [(p.get("id"), p.get("amount")) for p in th.iter("payment") if p.get("void") != "1" and abs(float(p.get("amount") or 0)) > 0]
rec["payments"] = paid
if paid:
    rec["result"] = "REFUSED - a non-void payment with money is on the visit; not a GV rebill case"; print(json.dumps(rec)); sys.exit(1)
if any("713" in (c.get("modcodes") or "") for c in allc):
    rec["result"] = "REFUSED - a charge already carries GV (mcode713)"; print(json.dumps(rec)); sys.exit(1)
if not LIVE:
    rec["result"] = "dry: would add GV to %d charge(s) then frequency-1 rebill seq %s" % (len(allc), seq); print(json.dumps(rec)); sys.exit(0)
rec["add_gv"] = [str(gv_rebill.add_gv(re.sub(r"\D", "", c.get("id"))))[:160] for c in allc]
time.sleep(0.6)
v2, p2, c2 = resave.visit_charges(cid); rec["mods_after"] = [(c.get("id"), c.get("modcodes")) for c in c2]
if len(c2) != len(allc) or not all("713" in (c.get("modcodes") or "") for c in c2):
    rec["result"] = "GV not on every live charge after the echo - NOT rebilled"; print(json.dumps(rec)); open("registers/hospice_gv_register.json", "a").write(json.dumps(rec) + "\n"); sys.exit(1)
rec["rebill"] = str(freq1_visit.run(vid, cid, seq))[:200]
rec["result"] = "GV added + frequency-1 rebill seq %s" % seq
print(json.dumps(rec)); open("registers/hospice_gv_register.json", "a").write(json.dumps(rec) + "\n")
