# PLAIN ENGLISH: records this run's ERA denial handling in registers/era_manual_register.json, appends the run section to
# needs_facesheet_list.md, writes the run report CSV, the captured_calls additions file, the digest and the board update file.
import json, csv, datetime, os
S = "2026-10-31T0040Z"; NOW = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
reg = json.load(open("registers/era_manual_register.json"))
lines = [
 ("1053349",15447995,"19458983","23371293","posted",0.0,206.0,"WONCS","CO147 CCM on Humana Medicaid MMA chart - CCM-on-Medicaid rule"),
 ("1053349",15447995,"19458983","23371294","posted",0.0,109.0,"WONCS","CO147 CCM on Humana Medicaid MMA chart - CCM-on-Medicaid rule"),
 ("1053349",15447998,"19459295","23371738","posted",0.0,206.0,"WONCS","CO147 CCM on Humana Medicaid MMA chart - CCM-on-Medicaid rule"),
 ("1053349",15447998,"19459295","23371739","posted",0.0,109.0,"WONCS","CO147 CCM on Humana Medicaid MMA chart - CCM-on-Medicaid rule"),
 ("1053349",15448001,"19459296","23371740","posted",0.0,206.0,"WONCS","CO147 CCM on Humana Medicaid MMA chart (Stedi MBI 72 - not Medicare) - CCM-on-Medicaid rule"),
 ("1053349",15448001,"19459296","23371741","posted",0.0,109.0,"WONCS","CO147 CCM on Humana Medicaid MMA chart (Stedi MBI 72 - not Medicare) - CCM-on-Medicaid rule"),
 ("1053349",15447997,"19459066","23371445","posted",0.0,206.0,"WONCS","CO147 CCM on Humana Medicaid LTC/MMA chart (Stedi 77027 Full Medicaid + SMMC LTC; MBI 72) - CCM-on-Medicaid rule"),
 ("1053349",15448003,"19457356","23369216","posted",0.0,74.64,"WOINS","CO185/N767 coinsurance residual after Medicare paid - 9/20 rule"),
 ("1053349",15448002,"19457333","23369190","denial-handled",0.0,0.0,"","CO185/N767 Humana crossover answer on a chart with NO Humana plan; live carrier UNI01 (United American Medigap) billed for the 74.64 coinsurance - no action, waiting on UNI01"),
 ("1053349",15447996,"19458764","23370984","denial-handled",0.0,0.0,"","PI16/MA63 invalid principal dx Z87.828 -> dx_primary_fix delete, freq1 rebill seq 2 (Humana MMA) 204"),
 ("1053351",15448006,"19458948","23371225","denial-handled",0.0,0.0,"","CO16/M76 primary dx F01.50 -> dx_primary_fix delete, freq1 rebill seq 1 (Humana) 204"),
 ("1053351",15448006,"19458948","23371226","denial-handled",0.0,0.0,"","CO16/M76 primary dx F01.50 -> dx_primary_fix delete (same visit)"),
 ("1053349",15447992,"19459299","23371744","denial-handled",0.0,0.0,"","PI252/N4 Humana MMA wants the primary EOB: chart Medicare ACTIVE (271) - visit order 2,4 + ONE freq1 to Medicare 204; patient order 2,4"),
 ("1053349",15447993,"19459179","23371587","denial-open",0.0,0.0,"","PI197 precert absent (Humana H-plan, 271 AAA 42) - Working Denials board / board row humana-pi197-precert-1031 (William: auth)"),
 ("1053349",15447994,"19458868","23371100","denial-open",0.0,0.0,"","PI197 precert absent (Humana Medicaid MMA) - board row humana-pi197-precert-1031"),
 ("1053349",15447999,"19458751","23370971","denial-open",0.0,0.0,"","PI197 precert absent (Humana Medicaid MMA) - board row humana-pi197-precert-1031"),
 ("1053349",15448000,"19458752","23370972","denial-open",0.0,0.0,"","PI197 precert absent (Humana Medicaid MMA) - board row humana-pi197-precert-1031"),
 ("1053350",15448004,"19459095","23371484","denial-open",0.0,0.0,"","CO234/N20 CCM not paid separately (Humana MA H-plan, 271 AAA 42) - Working Denials board (no standing rule)"),
]
for ck,ccl,vid,cid,out,pay,wo,code,note in lines:
    reg.append({"checkid":ck,"checkclaimid":ccl,"visitid":vid,"chargedetailid":cid,"outcome":out,"pay":pay,"wo":wo,"wocode":code,"note":note,"when":S})
json.dump(reg, open("registers/era_manual_register.json","w"), indent=1)
print("era_manual_register", len(reg))
# ---- report CSV
rows = [["column","status","patient","dos","carrier","error","action"],
 ["charge review","cleared","-","-","-","-","0 -> 0"],
 ["claim inspector","cleared","-","-","-","-","0 -> 0 (no batches)"],
 ["unbilled","remaining","chart 25994 v19458784 v19458785; chart 17477225 v19458864; chart 17469426 v19459136","10/2026","FLO02","Facility is missing NPI information (fac67 HCA REHAB)","William: facility NPI in Master Files ($871)"],
 ["exclusions","remaining","chart 24750 v19455937 run 1700294","-","AET12","CH FH PREF0288 INVALID PAYER ID/CPID 814723941 + PREF0264","William: carrier master ($315) - standing hold"],
 ["era","posted (Post button)","check 1053351 Humana 204863822261030","10/22/2026","HUM01","-","$156.51 posted on 1 visit by era_post; check dismissed"],
 ["era","dismissed","check 1053349 Humana NO-PAY-202610290006066 (12 $0 claims)","10/04-10/23/2026","HUM01","denial-only lines","see rows below; check dismissed by era_clear"],
 ["era","dismissed","check 1053350 Humana NO-PAY-202610290006067 (1 $0 claim)","10/22/2026","HUM01","CO234/N20 CCM","Working Denials board; check dismissed"],
]
for ck,ccl,vid,cid,out,pay,wo,code,note in lines:
    rows.append(["era", out, "visit %s charge %s" % (vid,cid), "", "HUM01", note.split(" - ")[0][:80], ("%s %.2f" % (code, wo)) if wo else note])
rows += [["board input","-","Insurance Refresh Board rows changed since 10/30 12:00Z: 0; drops: 0; Working Denials queue: 0; approvals: 0","-","-","-","nothing requested"],
 ["feed","-","Claimocity drop: nothing new (newest download__ 2026-09-09; register through 10-27)","-","-","copy job stale","William: Cloud Shell paste (claimocity/cloud_run/DEPLOY.md)"],
 ["availity/treasury","-","no new Remittance Viewer PDF, 835 or Check/EFT export since 10/21","-","-","-","nothing to parse"],
]
with open("_run report 10-30 2040.csv","w",newline="") as f: csv.writer(f).writerows(rows)
print("csv rows", len(rows))
