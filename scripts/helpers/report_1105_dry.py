#!/usr/bin/env python3
# PLAIN ENGLISH (write the button-run/1 report file for the DRY ehpa Billing Button run 2026-11-05T0545Z)
# Decides: nothing. Ids and dollars only - never a patient name or member id. Dry: read and count only, nothing written in AMD.
import json, datetime, os
STAMP="2026-11-05T0545Z"; REPO="/home/claude/effinger-billing-backend"
now=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
out=json.load(open("/home/claude/unbilled/outstanding_claims_dry.json"))
den=json.load(open(REPO+"/reports/button/working_denials_latest.json"))
def st(n,t,s,c=None,d=None,l=None):
    return {"name":n,"title":t,"status":"ok","summary":s,"counts":c or {},"dollars":d or {},"lines":l or [],"errors":[],"started":now,"ended":now}
rep={"schema":"button-run/1","stamp":STAMP,"mode":"dry","status":"ok",
 "headline":"DRY: Columns 0/15/0/1 -> 0/15/0/1 (read only); ERA 0 checks; nothing written",
 "note":"dry run (brief: feed,columns,era,cascade,packages,cred,outstanding; packages none) - read and counted, nothing written in AMD, no board file",
 "run_url":"https://claude.ai/code/session_01HHfWRCaiLjEcwyXQ5KHUEU","started":"2026-11-05T05:45:00Z","ended":now,"engine":"claude","trigger":"trig_01S771Si8VJ8DvcwgHMHGYB5",
 "summary":{"columns":{"before":{"charge_review":0,"claim_inspector":15,"unbilled":0,"exclusions":1},"after":{"charge_review":0,"claim_inspector":15,"unbilled":0,"exclusions":1}},
  "era":{"before":{"checks":0,"unposted":0.0},"after":{"checks":0,"unposted":0.0}},
  "posted":{"pay":0.0,"woins":0.0,"wocaid2nd":0.0,"wolate":0.0},"resent":{"visits":0,"dollars":0.0},"written_off":{"count":0,"dollars":0.0},
  "packages":{"applied":0,"refused":0,"skipped":0},
  "outstanding":{"total":out["total"],"visits":out["visits"],"charts":out["charts"],"over_365":out["over_365"]}},
 "steps":[
  st("feed","Feed","17 objects, 0 new, newest 20261104"),
  st("columns","Claims Center columns","dry: CR 0, CI 15 (held), Unbilled 0, Exclusions 1 (AET12 carrier hold); nothing changed",{"charge review":0,"claim inspector":15,"unbilled":0,"exclusions":1}),
  st("era","ERA posting","dry: 0 checks / $0.00"),
  st("cascade","Cascade pre-check","dry: 19 pairs, 0 new lookups, 2 known flags (no change)",{"pairs":19,"lookups":0,"flagged":2}),
  st("packages","Approved packages","brief says none"),
  st("cred","Credentialing check","clean"),
  st("outstanding","Outstanding claims","%d visits on %d charts, $%.2f open; %d over a year ($%.2f)"%(out["visits"],out["charts"],out["total"],out["over_365"]["n"],out["over_365"]["dollars"]),{"visits":out["visits"],"charts":out["charts"]},{"total":out["total"]})],
 "packages":[],
 "waiting":[
  "Claim Inspector: 15 feed visits dated 11/07 (v19459901-v19459915, Pattern 4543) are Claimocity mistakes that should have been 11/01 (already entered correctly on 11/01). Void only after 11/07 and only those patients no longer hospitalized - William will say which. Nothing voided, bypassed or edited.",
  "Exclusions: AET12 carrier master CPID (chart 24750, $315)",
  "Humana PI-197 authorizations x4 ($564) - board row humana-pi197-precert-1031",
  "Chartless admits parked on the board until the feed creates the charts",
  "A fresh Drive state bundle (9/18 set corrupt)"],
 "errors":[]}
json.dump(rep,open(REPO+"/reports/button/%s.json"%STAMP,"w"),indent=1)
json.dump(rep,open(REPO+"/reports/button/latest.json","w"),indent=1)
print("written",STAMP)
