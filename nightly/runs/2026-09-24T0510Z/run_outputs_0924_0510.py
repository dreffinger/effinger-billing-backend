# PLAIN ENGLISH (run outputs for the 1am ET 9/24/2026 slot - ehpa cloud run 2026-09-24T0510Z)
# Decides: nothing. Reads this run's registers (scan_0912 before/after, era_checks before, unbilled/cascade/insp registers) and writes:
#   "_run report 9-24 0110.csv", board_updates_2026-09-24T0510Z.json (checks on rows worked, new rows), a needs_facesheet_list.md section,
#   captured_calls_additions_*.md, the chat-history digest (--final adds the mirror result from mirror_result.txt), and PHI-scrubbed copies
#   of the registers for the repo (outbox/repo/). Never touches: AMD, the board databases.
import csv, json, os, re, datetime, sys, glob
S = "2026-09-24T0510Z"; SRC = "1am ET 9/24 columns run (ehpa cloud)"; W = "9/24"; SLOT = "1 AM ET 9/24"
NOW = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
def rd(p, d): return open(p).read().strip() if os.path.exists(p) else d
def load(p, d):
    try: return json.load(open(p))
    except Exception: return d
def f(x):
    try: return float(x or 0)
    except Exception: return 0.0
MIRROR = rd("mirror_result.txt", "pending")
sb = load("scan_0912/summary_before.json", {}); sa = load("scan_0912/summary_after.json", {})
inv = load("inv_0510.json", {}); u = load("registers/unbilled_%s.json" % S, {}); c = load("registers/cascade_%s.json" % S, {}); insp = load("registers/insp_%s.json" % S, {}); casc = load("cascade_0510.json", {})
eb = load("era_checks_before_%s.json" % S, [])
fee = {}; dos = {}; names = {}
for r in sb.get("unbilled", []):
    fee[r["id"]] = sum(f(x.get("fee")) for x in r["_chgs"]); dos[r["id"]] = ", ".join(sorted({x.get("dos", "").strip() for x in r["_chgs"]})); names[r["patientid"]] = r["patientname"]
import xml.etree.ElementTree as ET
ex = ET.fromstring(open("scan_0912/excl_1700236_before.xml").read())
for v in ex.iter("visit"):
    fee[v.get("id")] = sum(f(x.get("totalfee")) for x in v.iter("charge")); dos[v.get("id")] = ", ".join(sorted({x.get("dos", "").strip() for x in v.iter("charge")})); names[v.get("patientid")] = v.get("patientname")
insp_b = sum(len(v) for v in (sb.get("inspector") or {}).values()); insp_a = sum(len(v) for v in (sa.get("inspector") or {}).values())
ub_b = sb.get("unbilled_totalcount"); ub_a = sa.get("unbilled_totalcount"); ex_b = sum(len(r) for r in (sb.get("exclusions") or {}).values()); ex_a = sum(len(r) for r in (sa.get("exclusions") or {}).values())
fx = u.get("fixed", []); rb = u.get("released_b", []); exf = u.get("excl_fixed", []); held = u.get("held", []) + c.get("held", [])
cdone = c.get("done", []); cvis = [v for r in cdone for v in r["visits"]]
sum_fx = round(sum(fee.get(r["vid"], 0) for r in fx), 2); sum_rb = round(sum(fee.get(r["vid"], 0) for r in rb), 2); sum_ex = round(sum(fee.get(r["vid"], 0) for r in exf), 2); sum_c = round(sum(fee.get(v, 0) for v in cvis), 2)
rebilled_b = [r for r in rb if any("204" in s for s in r.get("steps", []))]
rebilled_c = [v for r in cdone for v in r["visits"] if any("204" in s for s in r.get("steps", []))]
resent = round(sum_fx + sum_ex + sum(fee.get(r["vid"], 0) for r in rebilled_b) + sum(fee.get(v, 0) for v in rebilled_c), 2)
n_rebills = len(fx) + len(exf) + len(rebilled_b) + len(rebilled_c)
queued_new = [v for r in cdone for v in r["visits"] if v not in rebilled_c]
byp = insp.get("bypassed", [])
def pat(pid): return "pat%s" % pid
# ---------------- run report CSV
rows = []
def add(col, status, **k):
    r = {"column": col, "status": status, "patient": "", "dos": "", "carrier": "", "error": "", "action": "", "amount": "", "checkid": "", "visit": ""}; r.update(k); rows.append(r)
add("Charge Review", "0 -> 0", action="nothing to review")
add("Claim Inspector", "%d -> 35 -> %d" % (insp_b, insp_a), action="15 advisories raised by this run's resaves cleared: modifier 25 (mcode7) on 10 CCM 99489 add-ons + Pattern 35790 bypassed x10; Pattern 11256 bypassed + logged x5; 20 standing holds unchanged")
for b in byp: add("Claim Inspector", "cleared", patient=pat(b["pid"]), visit=b["vid"], error="; ".join(b["errs"])[:120], action="bypassed (advisory)")
for h in [("17472874", "15 April-2026 hospital visits", "Hospitalization From Date empty", "HELD - HCA admission date (row thackeray-kendrew-17472874)", "2403.00"), ("17473477", "19455625", "Pattern 35790 + deceased guard", "HELD for William", ""), ("45668", "19455691", "Pattern 20389 F02.80 + deceased guard", "HELD for William: void", ""), ("20863", "19455936", "Pattern 24078 CCI", "HELD for William", ""), ("17477208", "19455940", "duplicate 99487+99489 lines", "HELD for William", ""), ("17474541", "19430630", "Pattern 15775", "HELD for William", "109.00")]:
    add("Claim Inspector", "held", patient=pat(h[0]), visit=h[1], error=h[2], action=h[3], amount=h[4])
add("Unbilled", "%s -> %s" % (ub_b, ub_a), action="98 rows (September CCM batch 127783 + late Jan-Feb 2026 entries): %d visits re-ordered to the live plan and rebilled ($%.2f), %d released rule (b) ($%.2f), %d new/repaired charts insured from the cascade (%d visits, $%.2f), %d held" % (len(fx), sum_fx, len(rb), sum_rb, len(cdone), len(cvis), sum_c, len(held)))
for r in fx: add("Unbilled", "cleared", patient=pat(r["pid"]), visit=r["vid"], dos=dos.get(r["vid"], ""), carrier="insorder %s" % r["insorder"], error="Insurance order missing / DOS outside coverage / MSP code", action="insorder set + freq-1 original to seq %s + released: %s" % (r["seq"], r["note"][:110]), amount="%.2f" % fee.get(r["vid"], 0))
for r in rb: add("Unbilled", "released", patient=pat(r["pid"]), visit=r["vid"], dos=dos.get(r["vid"], ""), error="A payment from the prior payor is required", action=r["note"][:140], amount="%.2f" % fee.get(r["vid"], 0))
for r in cdone:
    for v in r["visits"]: add("Unbilled", "cleared", patient=pat(r["pid"]), visit=v, dos=dos.get(v, ""), carrier=r.get("carrier", ""), error="Insurance order is missing on visit (new chart)", action=("plan added (%s, begin %s, no group) - %s; AMD 271 %s" % (r.get("carrier"), r.get("begin"), r["note"][:90], (r.get("elig") or "")[:40])) if r.get("carrier") else r["note"][:160], amount="%.2f" % fee.get(v, 0))
for h in held:
    vids = h.get("vids") or [h.get("vid")]
    for v in vids: add("Unbilled", "held", patient=pat(h["pid"]), visit=v, dos=dos.get(v, ""), error="", action=h["why"][:220], amount="%.2f" % fee.get(v, 0))
add("Exclusions", "%d -> %d" % (ex_b, ex_a), action="claim run 1700236: 10 Florida Medicaid PRIMARY claims rejected PSBR0111 'INVALID PAYER RESP SEQ NUM CODE P' -> the Medicaid 271 names each member's SMMC MMA plan (FCC / Humana / Simply): visit insorder -> that plan, freq-1 original to it (204 x10), exclusions completed; patient default order set to the MMA plan")
for r in exf: add("Exclusions", "cleared", patient=pat(r["pid"]), visit=r["vid"], dos=dos.get(r["vid"], ""), carrier="MCAD -> seq %s" % r["seq"], error="CH FI PSBR0111 INVALID PAYER RESP SEQ NUM CODE P", action=r["note"][:120], amount="%.2f" % fee.get(r["vid"], 0))
add("Exclusions", "held", patient="pat17472517", visit="19423193", carrier="HUM01", error="PDTP0303 missing admission date", action="HELD - no 99223 anchor within 45 days (standing)", amount="70.17")
add("Exclusions", "held", patient="pat20863", visit="19445850", carrier="FLO99", error="PDTP0303 missing admission date", action="HELD - no 99223 anchor within 45 days (standing)", amount="14.38")
add("ERA", "%d checks / $%.2f -> 0 / $0.00" % (len(eb), sum(f(x.get("unpostedamount")) for x in eb)), action="no unposted check; locks released; no new 835 in 'bht Optum era downloads'; nothing to post, no fallback, nothing to clear")
add("ERA", "Availity 5(g)", action="no new Remittance Viewer PDF or Check/EFT export; the two ScanSnap PDFs dropped 03:39Z 9/24 are the Optum/TRICARE East ERA enrollment form and the PGBA EDI Trading Partner Agreement (signed 9/22/2026) - correspondence, not remits; recorded on the board")
csvname = "_run report 9-24 0110.csv"
with open(csvname, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); [w.writerow(r) for r in rows]
# ---------------- board updates
ops = []
def chk(rid, result, ok="ok"): ops.append({"op": "upsert", "collection": "items", "id": rid, "set": {}, "append": {"checks": [{"ok": ok, "src": SRC, "result": result, "when": W}]}})
def newrow(rid, patient, dob, facility, amdid, need, why, amount, status, note, mbi="", inscarrier="", insid="", insplans="", checks=None):
    ops.append({"op": "upsert", "collection": "items", "id": rid, "set": {"patient": patient, "dob": dob, "facility": facility, "amdid": amdid, "mbi": mbi, "inscarrier": inscarrier, "insid": insid, "insplans": insplans, "need": need, "why": why, "amount": amount, "status": status, "created": NOW, "updated": NOW},
                "append": {"notes": [{"who": "Claude", "text": note, "at": NOW}], "checks": checks or [{"ok": "ok" if status == "claude" else "human", "src": SRC, "result": need[:300], "when": W}]}})
def nm(pid): return names.get(pid) or (inv.get(pid) or {}).get("name") or pid
def dob(pid): return (inv.get(pid) or {}).get("dob", "")
# William's turn
newrow("whitlow-shay-17477639", nm("17477639"), dob("17477639"), "SODALIS ALF", "17477639", "WILLIAM: facesheet or card for %s (DOB %s, Sodalis ALF, CCM 99487+99489 9/20/2026, $315). No plan on the chart; Stedi MBI lookup ERR 72 (not a Medicare beneficiary, age 45); insurance discovery coveragesFound 0; no facesheet in the HCA/TMH/PCC/Claimocity folders, no Pam email, no board drop; address empty. Visit 19455621 held in Unbilled." % (nm("17477639"), dob("17477639")), "Unbilled 9/24: new chart from the Claimocity CCM batch with no insurance plan", 315, "william", "Created by the 1 AM ET 9/24 run - every automated source is exhausted; your turn for the facesheet/card.")
newrow("jarvis-marisa-17477842", nm("17477842"), dob("17477842"), "OAKES SOUTHWOOD", "17477842", "WILLIAM: DUPLICATE CHART. The Claimocity CCM batch created a new JARVIS,MARISA chart 17477842 with the 1921 placeholder date of birth (the known Oakes pattern) and put the 9/20/2026 CCM 99487+99489 ($315, visit 19455665) on it. lookuppatient shows the real JARVIS,MARISA charts (born 1938: pat17472416, 17472482, 17472774, 17473041, 17473175, 17474586, 17475601, 17476457, 17476530, 17476771 ... 10+ duplicates). Per the identity rule nothing was attached to the mis-dated chart - please merge / move the charge to the chart that carries her insurance, then I bill it.", "Unbilled 9/24: placeholder-DOB duplicate chart from the feed", 315, "william", "Created by the 1 AM ET 9/24 run. No insurance attached (mis-dated duplicate); needs the merge decision.")
newrow("griffith-jace-17477850", nm("17477850"), dob("17477850"), "HCA FLORIDA CAPITAL HOSPITAL", "17477850", "WILLIAM: the Capital Health Plan MEMBER ID for %s (DOB %s, HCA admission 9/21/2026: 99223+99497 9/21 + 99233 9/22, $603). Medicare's 271 (Stedi MBI lookup, MBI on file in the workspace) names CAPITAL HEALTH PLAN as his Medicare Advantage HMO (COB 2/1/2026) - CHP is the only payer, but CHP eligibility by MBI answers AAA 72 and insurance discovery returned only CMS + FL Medicaid QI1 (Part B premium help, not billable). Need the CHP member id from the HCA facesheet/card; then CAP07 goes on the chart and both visits bill. Visits 19455898 + 19455868 held in Unbilled." % (nm("17477850"), dob("17477850")), "Unbilled 9/24: new HCA chart; Medicare names a CHP Advantage plan whose member id no lookup returns", 603, "william", "Created by the 1 AM ET 9/24 run. Medicare Part A/B since 9/1/2019 (disabled beneficiary), MA = Capital Health Plan from 2/1/2026 - the CHP id is the one missing piece.", mbi="on file (workspace)", inscarrier="CAP07 Capital Health Plan (MA) - id needed")
newrow("whitfield-rowan-17473232", nm("17473232"), dob("17473232"), "TAPESTRY LAKESHORE ALF", "17473232", "WILLIAM: CCM 99487+99489 dated 09/20/2026 ($315, visit 19455597) is AFTER the date of death [DOB] on Medicare's 271 (chart Medicare plan INACTIVE). The visit came in on the September CCM batch with no insurance order. Held - please void the charge (or correct the DOS if the service month is wrong).", "Unbilled 9/24: CCM visit after the Medicare date of death", 315, "william", "Created by the 1 AM ET 9/24 run. Deceased guard: DOS after date of death - nothing billed.")
newrow("[name]-17471681", nm("17471681"), dob("17471681"), "TAPESTRY LAKESHORE ALF", "17471681", "WILLIAM: CCM 99487 dated 09/20/2026 ($206, visit 19455606) is AFTER the date of death [DOB] on Medicare's 271 (chart Medicare plan INACTIVE). CCM in the month of death needs a DOS on/before 9/10/2026 to bill Medicare - please move the DOS to on/before 9/10 or void.", "Unbilled 9/24: CCM visit after the Medicare date of death", 206, "william", "Created by the 1 AM ET 9/24 run. Deceased guard: DOS after date of death - nothing billed.")
# informational rows (Claude's turn)
INFO = {"17477843": ("BRYNWOOD (Monticello)", "FLO02 Florida Medicare"), "17477844": ("BRYNWOOD (Monticello)", "UNI20 UHC AARP Medicare Advantage HMO-POS"), "17477845": ("HCA FLORIDA CAPITAL HOSPITAL", "UNI20 UHC AARP Medicare Advantage GA-5 HMO"), "17477846": ("HCA FLORIDA CAPITAL HOSPITAL", "UNI20 UHC AARP Medicare Advantage Patriot RPPO"),
        "17477847": ("HCA FLORIDA CAPITAL HOSPITAL", "UNI20 UHC Group Medicare Advantage LPPO"), "17477848": ("HCA FLORIDA CAPITAL HOSPITAL", "UNI20 UHC Group Medicare Advantage LPPO"), "17477849": ("HCA FLORIDA CAPITAL HOSPITAL", "FLO02 Florida Medicare"), "17477851": ("BRYNWOOD (Monticello)", "UHCMA UnitedHealthcare Dual Complete (QMB)")}
for r in cdone:
    pid = r["pid"]
    if pid in INFO:
        fac, car = INFO[pid]; amt = round(sum(fee.get(v, 0) for v in r["visits"]), 2)
        newrow("%s-%s" % (re.sub(r"[^a-z]", "-", nm(pid).lower().split(" ")[0].replace(",", "-")).strip("-"), pid), nm(pid), dob(pid), fac, pid,
               "None - billed. %s -> %s plan added (begin %s, no group), AMD 271 %s; %s released from Unbilled%s. Address line 1 filled from line 2." % (r["note"], car, r.get("begin"), (r.get("elig") or "")[:60], "visits %s" % ", ".join(r["visits"]), " with admission 09/21/2026 (own 99223), onhcfa 1" if fac.startswith("HCA") else ""),
               "Unbilled 9/24: new chart from the Claimocity feed with no insurance plan", amt, "claude", "Created by the 1 AM ET 9/24 run - insured from the Stedi cascade and billed; nothing for you.", inscarrier=car, insplans="1st %s" % car,
               checks=[{"ok": "ok", "src": "Stedi MBI lookup / insurance discovery (1am ET 9/24 run)", "result": r["note"][:250], "when": W}, {"ok": "ok", "src": "AMD eligibility (free 271) on the new plan", "result": (r.get("elig") or "")[:200], "when": W}])
    elif pid == "45049":
        newrow("birkett-davin-45049", nm(pid), dob(pid), "ASPIRE AT TALLAHASSEE", pid, "Watching: the chart's Medicare plan answered AAA 72 on AMD's 271; Stedi MBI lookup (name/DOB) finds him with MBI on file as straight Medicare (Part A/B 2/1/2014, WellCare PDP) - member id re-written in place (unchanged value), Medicaid + Humana plans INACTIVE so visit insorder = Medicare alone; the late-entered 01/05/2026 99308 ($107, v19455371) went out as an original claim (204) and was released. AMD's 271 still says AAA 72 after the write - Medicare's answer to the claim decides; if it rejects on the id, the chart name/DOB vs Medicare's record is next.", "Unbilled 9/24: 'prior payor' row on a chart whose Medicare 271 rejects the member id", 107, "claude", "Created by the 1 AM ET 9/24 run - watching the claim.")
# checks on existing rows
chk("alcott-alfie-17477183", "1 AM ET 9/24: a second visit arrived - CCM 99487+99489 9/20/2026 ($315, v19455759) - held with the 9/18 99309 ($141, v19455471) in Unbilled 'Insurance order is missing'; still no facesheet / Pam email / drop, Sunshine ended 8/31/2026. Your turn unchanged.", "human")
chk("thackeray-kendrew-17472874", "1 AM ET 9/24: UNI20 (seq 3) answered INACTIVE and Sunshine AAA 78 on AMD's 271; Stedi discovery found straight Medicare (MBI on file) ACTIVE 9/1-9/20/2026 -> FLO02 added (seq 4, AMD 271 ACTIVE, Part A/B since 8/1/2020, begin date set), the three NEW September visits (v19455321/22/23) routed to it, freq-1 originals 204 x3, released; patient default order -> 4; address line 1 filled (2423 Ramblewood Ct per the UHC 271; Medicare's 271 prints 4423 Ramble Wood Ct - check the street number). The 15 April-2026 hospital visits stay on your hold for the HCA admission date - note Medicare A/B has been in force since 2020, so they may belong to Medicare rather than WEL04/UNI20 once the admission date is in.")
chk("[name]-17476544", "1 AM ET 9/24: the 3 August visits (v19451019 8/7 $141, v19451191 8/3 $141, v19451353 8/11 $107) sat in Unbilled 'DOS outside coverage' because their insorder 2,1 still carried the end-dated Florida Blue plan - insorder -> 2 (Medicare only), freq-1 originals 204 x3, released. Real secondary still open (cascade).")
chk("pembroke-tobias-17470802", "1 AM ET 9/24: four more visits (CCM 8/22 $315, 99309 8/27 / 8/31 / 9/3 $141 each) sat in Unbilled 'DOS outside coverage' with insorder 2,1 (UNI20 ended 8/19) - insorder -> 2 (Medicare), freq-1 originals 204 x4, released.")
chk("[name]-17477128", "1 AM ET 9/24: two new visits (CCM 9/20 $315 v19455814, 99309 9/17 $141 v19455905) arrived with no insurance order - set to Medicare seq 2, originals 204, released; patient default order set to 2 so the next batch bills on its own.")
chk("berry-priscilla-denials", "1 AM ET 9/24: CCM 9/20/2026 ($206, v19455653) arrived with no insurance order - set to 2,3 (Medicare, AARP Medigap), original 204, released; patient default order set 2,3. AARP plan's 271 still AAA 72 (member id) - watch the crossover.")
chk("orme-cotterell-simply-npi", "1 AM ET 9/24: CCM 9/20/2026 ($206, v19455810, rendering Effinger) went to Florida Medicaid FFS as PRIMARY on claim run 1700236 and rejected PSBR0111 (invalid payer responsibility sequence) - the Medicaid 271 names Simply SMMC MMA: visit insorder -> Simply seq 2, freq-1 original to Simply 204, exclusion completed; patient default order -> 2.")
chk("farley-delia", "1 AM ET 9/24: CCM 9/20/2026 ($315, v19455667) arrived with no insurance order (UNI20 ended 5/6/2026) - set to Medicare seq 2, original 204, released; patient default order set to 2.")
chk("availity-remits-backlog", "1 AM ET 9/24: no new Availity PDF or Check/EFT export; ERA Center 0 unposted checks. The two ScanSnap PDFs in 'bht Optum era downloads' (03:39Z 9/24) are the Optum/TRICARE East ERA enrollment form (submitter 857005, CPID 2872, signed 9/22/2026, allow 4 weeks) and the PGBA EDI Provider Trading Partner Agreement (signed 9/22/2026) - correspondence, nothing to post; TRICARE 835s should start reaching the ERA Center ~mid/late October.", "na")
newrow("tricare-east-era-enrollment-0922", "TRICARE EAST (Humana Military / PGBA) - ERA enrollment", "", "", "", "Informational: William signed the Optum ERA enrollment form for TRICARE East (payer CPID 2872, submitter 857005, aggregation by TIN, clearinghouse Optum, requested effective 9/22/2026) and the PGBA EDI Provider Trading Partner Agreement on 9/22/2026; both scans landed in 'bht Optum era downloads' 9/24 03:39Z. PGBA says allow 4 weeks - TRICARE 835s should appear in the ERA Center from ~10/20/2026; until then TRICARE pays on paper/EFT with no ERA. Nothing to do now.", "ScanSnap correspondence read by the 1 AM ET 9/24 run", 0, "claude", "Created by the 1 AM ET 9/24 run so the enrollment date is on record.")
newrow("medicaid-primary-psbr0111-0924", "FLORIDA MEDICAID PRIMARY rejections (PSBR0111) - 5 charts", "", "", "20060, 17477134, 20514, 17475713, 17474046", "None - re-routed. Claim run 1700236 rejected 10 Florida Medicaid FFS claims sent as PRIMARY ('CH FI PSBR0111 INVALID PAYER RESP SEQ NUM CODE P') - every member is on an SMMC MMA plan per the Medicaid 271: pat20060 (6 visits 11/4/2025-9/20/2026, $843) and pat17477134 ($315) and pat20514 ($315) -> Florida Community Care; pat17475713 ($206) -> Humana Medicaid; pat17474046 ($206) -> Simply. Visit insorder set to the MMA plan, freq-1 originals 204 x10, exclusions completed, patient default order set to the MMA plan so future batches skip Medicaid FFS. Watch the MMA answers (FCC's 41-AAA eligibility answer does not stop claims).", "Exclusions 9/24: Medicaid FFS as primary on SMMC members", 1885, "claude", "Created by the 1 AM ET 9/24 run - informational; nothing for you unless an MMA plan denies.")
board = {"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": ops}
json.dump(board, open("board_updates_%s.json" % S, "w"), indent=1)
# ---------------- needs_facesheet section
held_lines = "\n".join("- pat%s v%s: %s" % (h["pid"], ",".join(h.get("vids") or [h.get("vid")]), h["why"]) for h in held)
sec = """
## %s columns run (ehpa cloud Code Routine, run %s) - %s
- Bootstrap: repo ATTACHED (origin/main 6e71d19 = the 0310Z finalize commit; session branch claude/pensive-einstein-me1cza, work on main); net AMD_OK, STEDI_CRED_OK; ONE amd.login_cached success 05:12Z; no login lock; START marker uploaded 05:11Z. Layout from main (610 helpers, 345 registers, needs list rebuilt from 54 run sections); pseudonyms (285), laterality log (50), precheck cache (28) from 'workspace mirror'. bootstrap check: columns_inspector2_0908.py + era_details_pull.py MISSING from main (not rewritten; not needed). Newest Drive state bundle still 2026-09-18_1123UTC (not unpacked). GITHUB INBOX: no unapplied PACKAGE_* manifest. Boards: Working Denials queue 0; Insurance board 0 new drops, no row changed since 03:00Z. Pam Gmail: nothing newer than the 02:41Z 9/24 Sodalis admit (worked 0310Z). Drive: two ScanSnap PDFs 03:39Z 9/24 = TRICARE East ERA enrollment form + PGBA trading partner agreement (signed 9/22) - correspondence, not remits.
- Columns: Charge Review 0 -> 0 | Claim Inspector %d -> 35 (advisories raised by this run's resaves) -> %d | Unbilled %s -> %s ($%s -> $%s) | Exclusions %d -> %d (new claim run 1700236, 10 rows).
- UNBILLED: 98 rows = the September CCM batch (127783, DOS 9/20/2026, 99487/99489 at every ALF/SNF chart) + a late Claimocity batch of Jan-Feb 2026 SNF visits + 7 new HCA admissions 9/21-9/22. 'Insurance order is missing' on ESTABLISHED charts = the PATIENT default order was empty (plans end-dated / never set), so the feed could not assign one. Fixed %d visits ($%.2f): visit insorder set to the live order from the plans + AMD's free 271 (Medicare first; an MA plan alone; Medicaid FFS never first; the SMMC MMA plan the Medicaid 271 names as the Medicaid payer), freq-1 original claim, released; the patient default order set to the same string on 26 charts so the October batch bills on its own. %d rows released under rule (b) ($%.2f; four late-entered Jan-2026 visits also got an original claim to Medicare). Cascade on %d charts (%d visits, $%.2f): %s.
- Held in Unbilled (%d):
%s
- CLAIM INSPECTOR: the resaves raised Pattern 35790 on 10 CCM visits (modifier 25 = mcode7 put on each 99489, never on 99487, then bypassed with fresh ids) and Pattern 11256 on 5 (bypassed + laterality_flag_log.md). Standing holds unchanged (20): pat17472874 x15 April stay, v19455625 + v19455691 deceased guard, v19455936 CCI, v19455940 duplicate CCM lines, v19430630 Pattern 15775.
- EXCLUSIONS: claim run 1700236 - 10 Florida Medicaid PRIMARY claims rejected 'CH FI PSBR0111 INVALID PAYER RESP SEQ NUM CODE P' (pat20060 x6 incl. 11/2025-5/2026 late entries, pat17477134, pat20514, pat17475713, pat17474046): all five charts are SMMC MMA members per the Medicaid 271 (FCC x3 charts, Humana, Simply) -> visit insorder to the MMA plan, freq-1 original 204 x10, completed ($%.2f). Standing PDTP0303 holds: pat17472517 v19423193 HUM01 $70.17, pat20863 v19445850 FLO99 $14.38.
- ERA step 5: 0 unposted checks / $0.00 -> 0 / $0.00 (locks released; no new 835; nothing to post, refuse, clear). Availity 5(g): no new PDF / Check-EFT export. TRICARE East ERA enrollment signed 9/22/2026 (allow 4 weeks) recorded on the board.
- Dollars re-sent as frequency-1 originals this run: $%.2f (%d rebills, every chargerebill 204); %d new-chart visits ($%.2f) released to bill on the next claim run. Write-offs: none. Insurance entered: 10 plans (see the cascade lines) - none with a group number.
- Calls learned: no new call shape. Behaviours in captured_calls_additions_2026-09-24_0510UTC-1amET-ehpa-cloud.md.
- Mirror: %s
""" % (SLOT, S, datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"), insp_b, insp_a, ub_b, ub_a, sb.get("unbilled_totalamount"), sa.get("unbilled_totalamount"), ex_b, ex_a, len(fx), sum_fx, len(rb), sum_rb, len(cdone), len(cvis), sum_c,
       "; ".join("pat%s -> %s" % (r["pid"], (r.get("carrier") or "fix") + " " + r["note"][:70]) for r in cdone), len(held), held_lines, sum_ex, resent, n_rebills, len(queued_new), round(sum(fee.get(v, 0) for v in queued_new), 2), MIRROR)
MBI_RE = re.compile(r"\b[1-9][AC-HJKMNP-RT-Y][AC-HJKMNP-RT-Y0-9]\d[AC-HJKMNP-RT-Y][AC-HJKMNP-RT-Y0-9]\d[AC-HJKMNP-RT-Y]{2}\d\d\b")
sec = MBI_RE.sub("<mbi>", sec).replace("5ET4T1", "<mbi>").replace("JARVIS,MARISA", "the same-name").replace("member [member id]", "member <id>")
open("needs_facesheet_list_section_%s.md" % S, "w").write(sec)
if "--final" in sys.argv:
    open("needs_facesheet_list.md", "a").write(sec)
# ---------------- additions
adds = """# captured_calls additions - 2026-09-24 0510 UTC (1 AM ET 9/24 slot, ehpa cloud Code Routine, run %s)

No new call shape this run. Behaviours learned (chart ids only):

- Change Healthcare / Florida Medicaid front-end edit `CH FI PSBR0111: INVALID PAYER RESP SEQ NUM CODE P` on getclaimexclusioncharges = a Florida Medicaid FFS (MCAD car6113) claim sent as PRIMARY for a member Medicaid knows is on an SMMC MMA plan. AMD's free 271 on the Medicaid plan names the plan ('SMMC MMA Capitated FLORIDA COMMUNITY CARE' / 'HUMANA MEDICAL PLAN' / 'SIMPLY HEALTHCARE PLANS'); fix = visit insorder -> that plan's sequence (full-visit updvisitwithcharges echo), freq1_visit.run to it (204), hideexclusions; ins_update.update(pid, insid, sequence="<seq>") sets the PATIENT default order so the next Claimocity batch does not repeat it (10 claims, 5 charts, run 1700236).
- Unbilled 'Insurance order is missing on visit' on an ESTABLISHED chart (September CCM batch 127783, 25 charts) = the PATIENT record's insorder is empty (the seq-1 plan end-dated, or the order never set after a payer switch) so the feed creates the visit with no order. getdemographic <patient insorder=""> shows it. Fix per visit = full-visit resave with insorder + onhcfa=1 and a freq-1 original; the durable fix = ins_update sequence= on the patient (26 charts this run). 'Date of service is outside insurance coverage effective dates' = the visit insorder still lists an end-dated plan (e.g. '2,1' with seq 1 ended) - drop it from the visit order. 'When billing Medicare as the non-primary carrier, the MSP Code ... is required' = Medicare sits behind a Medicare Advantage plan in the order - the MA plan stands alone (Medicare never secondary to its own MA plan).
- getclaiminspectorcharges: the error element's `name` attribute is a truncated label ('The primary procedure code on Claim ID...'); the pattern text ('Pattern 35790 ...') is the element BODY (e.text) - match advisories on the body, not the name. Every resave re-inspects and re-issues ids (bypass only from a fresh listing).
- Stedi UHC 87726 eligibility with the MBI as memberId returns the UHC Medicare Advantage member number (subscriber.memberId) and plan name - the way to get the MA id when the MBI lookup names a UHC entity (Care Improvement Plus = UHC) but no number. CHP 95112 with the MBI answers AAA 72 (CHP needs its own id); insurance discovery on a 45-year-old disabled beneficiary returned CMS + FL Medicaid QI1 but not the CHP MA member id.
- Stedi MBILUNOSSN by name/DOB answered ERR 72 for four HCA admits who ARE Medicare Advantage members (discovery then named the UHC MA plan and member id) - ERR 72 on the MBI lookup does not rule out an MA member; run discovery before calling a chart 'not Medicare'.
- addr_line1_fix.fix on the Claimocity HCA charts: line 1 filled (200) after the email-field phone is blanked (500 'Email is not a valid format' on the first try); the clear-line-2 PATCH still answers 500 (cosmetic, line 2 repeats the street).
- ScanSnap PDFs are not always remits: the 9/24 03:39Z pair in 'bht Optum era downloads' is the Optum/TRICARE East ERA enrollment form + PGBA EDI trading partner agreement (image-only; pdftoppm -r 110 + tesseract reads them) - correspondence -> board row, nothing posted.
""" % S
open("captured_calls_additions_2026-09-24_0510UTC-1amET-ehpa-cloud.md", "w").write(adds)
# ---------------- PHI-scrubbed register copies for the repo
os.makedirs("outbox/repo", exist_ok=True)
MBI = re.compile(r"\b[1-9][AC-HJKMNP-RT-Y][AC-HJKMNP-RT-Y0-9]\d[AC-HJKMNP-RT-Y][AC-HJKMNP-RT-Y0-9]\d[AC-HJKMNP-RT-Y]{2}\d\d\b"); NUM9 = re.compile(r"\b\d{9,11}\b")
def scrub(o):
    if isinstance(o, dict): return {k: scrub(v) for k, v in o.items() if k not in ("name", "dob", "address", "mbi", "disc", "lookup")}
    if isinstance(o, list): return [scrub(x) for x in o]
    if isinstance(o, str):
        s = MBI.sub("<mbi>", o); s = re.sub(r"(member|subscribernum)\s*[=:]?\s*\d{6,}", r"\1 <id>", s, flags=re.I); return NUM9.sub(lambda m: m.group(0) if m.group(0).startswith(("194", "233", "1747", "2336")) else "<id>", s)
    return o
for p in ("registers/unbilled_%s.json" % S, "registers/cascade_%s.json" % S, "registers/insp_%s.json" % S, "registers/mod25_fix_%s.json" % S):
    if os.path.exists(p): json.dump(scrub(load(p, {})), open("outbox/repo/" + os.path.basename(p), "w"), indent=1)
# ---------------- digest
dig = """# 2026-09-24_0510UTC run digest - backend billing run, 1 AM ET 9/24 slot (ehpa cloud)
%s
RUN COMPLETE
""" % sec.replace("## ", "## ", 1)
open("chat_history/2026-09-24_0510UTC run digest.md", "w").write(dig)
print("written: %s, board ops %d, section %d chars, additions, digest (mirror=%s)" % (csvname, len(ops), len(sec), MIRROR[:60]))
