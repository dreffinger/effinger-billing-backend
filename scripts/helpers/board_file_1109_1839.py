# PLAIN ENGLISH (board inbox file for the 1:39 PM ET 11/9 columns run, fired 18:39Z): writes ONE board_updates_<stamp>.json for
#   William's Drive 'board inbox' (the page applies it; no write_db, no approval). Decides nothing in AMD.
#   Ops: (1) Pam's four Brynwood admit emails of 17:39-17:47Z 11/9 - addison-danika-17477827 gets a checks/notes append (Ambetter
#   ACTIVE on AMD's 271, Medicaid 77027 Inactive at Stedi - nothing to change); [name]-21772 is a NEW card (chart found by
#   DOB, UHC MA plan ACTIVE and already first in the chart order - nothing to change); edgerton-micah-admit-1108 and
#   fortescue-lorelei-admit-1107 are NEW 'watching for a chart' cards (no AMD chart yet - a chart is never created from an email).
#   (2) standing append-only checks on availity-remits-backlog and aet12-carrier-cpid with this run's column/ERA numbers read from
#   the engine report reports/button/<stamp>-engine.json. Built through board_ops (plan_new_row, clean_file): no `updated`, no
#   status/need/why on rows William already owns. Never touches: AMD, the board DB, Drive (the upload is the connector's).
# Usage: python3 board_file_1109_1839.py  -> outbox/board_updates_2026-11-09T1839Z.json
import json, os, datetime
from board_ops import clean_file, plan_new_row
IDS = json.load(open("secrets/run_1839_ids.json"))   # PHI identifiers live here, never in the script
def fill(x):
    if isinstance(x, str):
        for k, v in IDS.items(): x = x.replace("{{%s}}" % k, v)
        return x
    if isinstance(x, list): return [fill(i) for i in x]
    if isinstance(x, dict): return {k: fill(v) for k, v in x.items()}
    return x
STAMP = "2026-11-09T1839Z"; NOW = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"); WHEN = "11/9"
SRC = "1:39pm ET 11/9 columns run (ehpa cloud, six-hourly slot) - run %s" % STAMP
rep = {}
p = "/home/claude/effinger-billing-backend/reports/button/%s-engine.json" % STAMP
if os.path.exists(p): rep = json.load(open(p))
s = rep.get("summary", {}); cb = s.get("columns", {}).get("before", {}); ca = s.get("columns", {}).get("after", {}); eb = s.get("era", {}).get("before", {}); ea = s.get("era", {}).get("after", {})
cols = "Columns %s/%s/%s/%s -> %s/%s/%s/%s" % tuple([cb.get(k, "?") for k in ("charge_review","claim_inspector","unbilled","exclusions")] + [ca.get(k, "?") for k in ("charge_review","claim_inspector","unbilled","exclusions")])
era = "ERA Center %s checks $%.2f -> %s checks $%.2f" % (eb.get("checks", "?"), float(eb.get("unposted", 0) or 0), ea.get("checks", "?"), float(ea.get("unposted", 0) or 0))
ops = []
# (1a) Addison - existing card, same work item (insurance on this chart): append only
ops.append({"op": "upsert", "collection": "items", "id": "addison-danika-17477827", "set": {}, "append": {
    "checks": [{"ok": "ok", "src": "Pam admit email 11/9 17:39Z (Brynwood admission record, admitted 11/05/2026 from home) + AMD 271 + Stedi 77027", "when": WHEN,
                "result": "Facesheet: Primary Payer Managed Care, Ins. Company Ambetter, policy {{ADDISON_POL}} (= the chart's AMB03 plan), Medicaid # {{ADDISON_MCD}} printed, facility auth {{ADDISON_AUTH}}. AMD 271 on AMB03 ins9520537: ACTIVE. Stedi FL Medicaid (77027) with that Medicaid #: Inactive (record name DYSON-ADDISON) - no Medicaid plan to add. Chart order AMB03 seq 1 stands; nothing changed."}],
    "notes": [{"who": "Claude", "at": NOW, "text": "Pam's 11/9 admit record for the 11/5 Brynwood readmission matches the chart (Ambetter {{ADDISON_POL}}, ACTIVE). Medicaid # on the sheet is inactive at the state - not added. Nothing needed from you."}]}})
# (1b) Wrexham - chart 21772 found by DOB; no card exists on that chart (board query amdid==21772 empty)
ops += plan_new_row([], {"id": "[name]-21772", "patient": "WREXHAM,MARCELLA (Pam's sheet: Marcella)", "dob": "{{WREXHAM_DOB}}", "facility": "BRYNWOOD (Monticello) - readmitted 11/05/2026 from TMH (orig adm 10/14/2024)",
    "amdid": "21772", "mbi": "{{WREXHAM_MBI}}", "amount": 0, "status": "claude",
    "inscarrier": "UNI20 UnitedHealthcare (Medicare Advantage)", "insid": "{{WREXHAM_POL}}",
    "insplans": "1st FLO02 Medicare {{WREXHAM_HICN}} (old HICN, 271 REJECTED 72) · 2nd MCAD Medicaid {{WREXHAM_MCD}} (271 REJECTED 72) · 3rd UNI20 UHC MA {{WREXHAM_POL}} (ACTIVE, lists MBI {{WREXHAM_MBI}}); chart order 3,2",
    "need": "None - chart already right. Pam's 11/9 Brynwood admission record (readmit 11/05/2026 from Tallahassee Memorial): Primary Payer Managed Care, United Healthcare policy {{WREXHAM_POL}}, MBI {{WREXHAM_MBI}}, facility auth {{WREXHAM_AUTH}}. AMD 271 on the chart's UNI20 plan: ACTIVE and it names the same MBI; the chart's default payer order is already UHC first (3,2). Note for the record: the chart's Medicare plan still carries the retired HICN {{WREXHAM_HICN}} (not billed - UHC MA is primary) and the chart spells the first name MARCELLA while the facility prints Marcella; UHC answered ACTIVE on the chart spelling, so nothing to change.",
    "why": "Pam admit email 11/9 17:47Z - Brynwood readmission 11/05/2026; chart verified by DOB (lookuppatient WREXHAM,M% -> 5 charts, one with DOB {{WREXHAM_DOB}}).",
    "checks": [{"ok": "ok", "src": "AMD eligibility (free 271) - elig_amd 21772 --all", "when": WHEN, "result": "FLO02 {{WREXHAM_HICN}} REJECTED AAA 72; MCAD {{WREXHAM_MCD}} REJECTED AAA 72; UNI20 {{WREXHAM_POL}} ACTIVE (others: F6 MBI {{WREXHAM_MBI}}, DBP dental, OptumRx)"},
               {"ok": "ok", "src": "AMD getdemographic 21772", "when": WHEN, "result": "patient insorder 3,2 (UHC MA first, Medicaid second) - matches the facesheet; no write needed"}],
    "notes": [{"who": "Claude", "at": NOW, "text": "Created by the 1:39 PM ET 11/9 run from Pam's admit email. Chart verified against the record - nothing for you here."}]}, now=NOW)
# (1c) Edgerton + Fortescue - no AMD chart yet (a chart is never created from an email; the feed creates it when the visits arrive)
ops += plan_new_row([], {"id": "edgerton-micah-admit-1108", "patient": "EDGERTON,MICAH G", "dob": "{{EDGERTON_DOB}}", "facility": "BRYNWOOD (Monticello) - admitted 11/08/2026 from Capital Regional Medical Center",
    "amdid": "", "mbi": "", "amount": 0, "status": "claude", "inscarrier": "CHP Capital Health Plan (HMO, Managed Care)", "insid": "{{EDGERTON_POL}}", "insplans": "facesheet: Primary Payer Managed Care with Levels - Capital Health Plan (HMO), policy {{EDGERTON_POL}}; facility auth {{EDGERTON_AUTH}}",
    "need": "Watching for the AMD chart. Pam's 11/9 Brynwood admission record: Capital Health Plan (HMO) policy {{EDGERTON_POL}}, DOB {{EDGERTON_DOB}}, age 68 (CHP Medicare Advantage expected). lookuppatient EDGERTON,M% found two charts with other DOBs (1951, 1954) - no chart for this patient, and a chart is never created from an email. When the Claimocity feed creates the chart (or the first visit lands in Unbilled), add CHP car41826 with policy {{EDGERTON_POL}} (no group), AMD 271, visit insorder, release.",
    "why": "Pam admit email 11/9 17:43Z - new Brynwood admit 11/08/2026, no AMD chart yet.",
    "checks": [{"ok": "no", "src": "AMD lookuppatient EDGERTON,MICAH% / EDGERTON,M%", "when": WHEN, "result": "no chart with DOB {{EDGERTON_DOB}} (two other EDGERTON charts: DOB {{EDW_OTHER_DOB1}}, {{EDW_OTHER_DOB2}})"}],
    "notes": [{"who": "Claude", "at": NOW, "text": "Created by the 1:39 PM ET 11/9 run from Pam's admit email. No chart yet; the next runs re-check and insure it the moment it exists."}]}, now=NOW)
ops += plan_new_row([], {"id": "fortescue-lorelei-admit-1107", "patient": "FORTESCUE,LORELEI", "dob": "{{FORTESCUE_DOB}}", "facility": "BRYNWOOD (Monticello) - admitted 11/07/2026 from Capital Regional Medical Center",
    "amdid": "", "mbi": "{{FORTESCUE_MBI}}", "amount": 0, "status": "claude", "inscarrier": "UNI20 UnitedHealthcare (Medicare Advantage)", "insid": "{{FORTESCUE_POL}}", "insplans": "facesheet: Primary Payer Managed Care with Levels - United Healthcare policy {{FORTESCUE_POL}}; Medicare Beneficiary ID {{FORTESCUE_MBI}}",
    "need": "Watching for the AMD chart. Pam's 11/9 Brynwood admission record: United Healthcare (Managed Care = Medicare Advantage) policy {{FORTESCUE_POL}}, MBI {{FORTESCUE_MBI}}, DOB {{FORTESCUE_DOB}}, address Monticello FL 32344. lookuppatient FORTESCUE,LORELEI% / FORTESCUE,L% -> no chart; a chart is never created from an email. When the feed creates the chart (or the first visit lands in Unbilled): add UNI20 car6404 policy {{FORTESCUE_POL}} (no group) as the only plan / first in order (the 9-digit UHC id = AARP Medicare Advantage), AMD 271, visit insorder, release.",
    "why": "Pam admit email 11/9 17:45Z - new Brynwood admit 11/07/2026, no AMD chart yet.",
    "checks": [{"ok": "no", "src": "AMD lookuppatient FORTESCUE,LORELEI% / FORTESCUE,L%", "when": WHEN, "result": "no chart"}],
    "notes": [{"who": "Claude", "at": NOW, "text": "Created by the 1:39 PM ET 11/9 run from Pam's admit email. No chart yet; the next runs re-check and insure it the moment it exists."}]}, now=NOW)
# (1d) Grantham - feed chart 17478318 (11/5): Cigna medical rejected 'not eligible' on run 1700365; the chart's only plan is a DENTAL Cigna hit
ops += plan_new_row([], {"id": "grantham-carlotta-17478318", "patient": "GRANTHAM,CARLOTTA A", "dob": "{{GRANTHAM_DOB}}", "facility": "HCA FLORIDA CAPITAL HOSPITAL (feed chart F261105-04, admitted ~11/03/2026)",
    "amdid": "17478318", "mbi": "", "amount": 754, "status": "william", "inscarrier": "CIG09 Cigna (DENTAL HMO - wrong payer)", "insid": "{{GRANTHAM_POL}}",
    "insplans": "1st CIG09 Cigna {{GRANTHAM_POL}} (begin 11/05/2025) - AMD 271 ACTIVE but the only benefit line is EB*1 HM 'Dental HMO' (Cigna Dental Health); no medical plan on the chart",
    "need": "WILLIAM: HCA admission facesheet (or card) for GRANTHAM, CARLOTTA A, DOB {{GRANTHAM_DOB}}, HCA Florida Capital Hospital, admitted ~11/03/2026 - five hospital visits 11/03-11/07/2026 ($754: 99223 + 99232 x4). The 11/5 feed run insured the new chart from a Stedi discovery hit 'CIGNA ... Active Coverage' that was CIGNA DENTAL HEALTH (plan 'Dental HMO'); Cigna medical rejected the 11/7 claim on run 1700365 'ENTITY NOT ELIGIBLE FOR BENEFITS FOR SUBMITTED DATES OF SERVICE' (the 11/5 and 11/6 claims are out and will bounce the same way; 11/3 + 11/4 not yet billed). Cascade exhausted: Stedi Medicare lookup ERR 72 (no Medicare record at 68), discovery = Cigna Dental + METLIFE 'CITY OF TALLAHASSEE' (a City retiree/employee benefit - Capital Health Plan is the usual medical plan for City of Tallahassee members, but no member id anywhere). Exclusion row held open (balance $111, not re-sent, not completed). Once the sheet is in: end-date the dental Cigna plan, add the real plan (no group), re-point the five visits and send as originals.",
    "why": "Exclusions 11/9 (run 1700365): CIG09 'entity not eligible for benefits for submitted dates of service' on v19460525 (99232 11/07/2026, $111) - the plan on the chart is a dental HMO",
    "checks": [{"ok": "no", "src": "Change Health / Cigna payer rejection - claim run 1700365", "when": WHEN, "result": "v19460525 99232 11/07/2026 $111: ENTITY NOT ELIGIBLE FOR BENEFITS FOR SUBMITTED DATES OF SERVICE (patient)"},
               {"ok": "no", "src": "AMD eligibility (free 271) - CIG09 ins9521148", "when": WHEN, "result": "ACTIVE, but EB*1*30 HM 'Dental HMO' + EB*1*35 (dental) only - Cigna Dental Health, not a medical plan"},
               {"ok": "no", "src": "Stedi MBI lookup (MBILUNOSSN, FL, DOS 11/07/2026)", "when": WHEN, "result": "ERR 72 Invalid/Missing Subscriber/Insured ID - no Medicare record"},
               {"ok": "no", "src": "Stedi insurance discovery (FL, DOS 11/07/2026)", "when": WHEN, "result": "2 items: CIGNA Dental Health, Inc. member {{GRANTHAM_POL}} Active Coverage 'Dental HMO' (eligibility begin 01/01/2026); METLIFE member {{GRANTHAM_MET}} 'CITY OF TALLAHASSEE' Active Coverage (plan dates garbage = the DOB) - no medical payer"},
               {"ok": "human", "src": "William", "when": WHEN, "result": "HCA facesheet / card for the ~11/03/2026 admission (City of Tallahassee member - CHP?)"}],
    "api": [{"src": "Stedi API - MBI lookup + insurance discovery", "at": NOW, "text": "MBI lookup GRANTHAM CARLOTTA {{GRANTHAM_DOB8}} FL DOS 20261107: AAA 72 (no Medicare record). Discovery: CIGNA Dental Health, Inc. member {{GRANTHAM_POL}} Active Coverage plan Dental HMO eligibilityBegin 20260101 (REVIEW_NEEDED); METLIFE member {{GRANTHAM_MET}} Active Coverage plan CITY OF TALLAHASSEE (REVIEW_NEEDED). AMD 271 on CIG09 {{GRANTHAM_POL}} (11/9 10:56 AM): ACTIVE; EB*1*30 HM Dental HMO; EB*1*35; subscriber GRANTHAM, CARLOTTA A, {{GRANTHAM_ADDR}}."}],
    "notes": [{"who": "Claude", "at": NOW, "text": "Created by the 1:39 PM ET 11/9 run. The feed's 11/5 discovery hit for this chart was Cigna DENTAL, so the hospital claims went to a dental plan. Every automated source is exhausted - your turn: the HCA facesheet (or card) for the 11/3 admission. Listed in the needs-facesheet list; the verify helper now skips dental/vision/life discovery hits."}]}, now=NOW)
# (2) standing watch rows - append-only
wait = "; ".join(rep.get("waiting", [])[:4]) or "none listed"
ops.append({"op": "upsert", "collection": "items", "id": "availity-remits-backlog", "set": {}, "append": {"checks": [{"ok": "na", "src": SRC, "when": WHEN,
    "result": "1:39 PM ET 11/9: no new Availity PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments' (Drive-wide nothing new after 12:30Z outside the routines' own files); no new 835 or facesheet file; Claimocity feed 22 objects, 0 new (newest 20261109); Working Denials queue 0; board drops 0; 0 rows changed since 12:30Z; Pam Gmail: four new Brynwood admit emails 17:39-17:47Z worked (see rows addison-danika-17477827, [name]-21772, edgerton-micah-admit-1108, fortescue-lorelei-admit-1107). %s. %s (engine pass). Waiting: %s." % (era, cols, wait)}]}})
ops.append({"op": "upsert", "collection": "items", "id": "aet12-carrier-cpid", "set": {}, "append": {"checks": [{"ok": "na", "src": SRC, "when": WHEN,
    "result": "1:39 PM ET 11/9: HOLD - the one AET12 PREF0288 + PREF0264 exclusion row (chart 24750, v19455937, run 1700294, $315) stays on the list, not rebilled; carrier master still unchanged."}]}})
doc = {"schema": "irb-board-updates/1", "source": "backend billing run %s" % STAMP, "created": NOW, "ops": ops}
doc = clean_file(fill(doc))
os.makedirs("outbox", exist_ok=True); out = "outbox/board_updates_%s.json" % STAMP
json.dump(doc, open(out, "w"), indent=1); print("wrote", out, len(ops), "ops;", "engine report" if rep else "NO engine report yet")
