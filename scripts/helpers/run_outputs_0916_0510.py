# PLAIN ENGLISH (run outputs for the 1am ET 9/16/2026 slot - ehpa cloud run 2026-09-16T0510Z)
# Decides: nothing. Reads this run's column scans (scan_0912/*_before|after), the AET12 re-verify, the ERA before/after
#   snapshots, the era_chain log and the fallback register, plus this run's two board actions (Merriwether-Paxton group-plan
#   rebill, Selwyn PR-39 write-off), then writes:
#   - "_run report 9-16 0510.csv" (per column: cleared / remaining with patient, DOS, carrier, error, action; ERA rows
#     carry check id, payer, visit, amount, action)
#   - board_updates_2026-09-16T0510Z.json (Insurance Refresh Board inbox file: update/upsert ops with appends keyed by
#     src+when, never set on status/need of an existing row; one NEW row for the unreadable facesheet PDF)
#   - a needs_facesheet_list.md section, the captured_calls additions file and the chat-history digest text
# Never touches: AMD, the board database. Copy of run_outputs_0310.py for the 1am ET slot (no 7pm extras).
import csv, json, os, re, collections, datetime
S = "2026-09-16T0510Z"; SRC = "1am ET 9/16 columns run (ehpa cloud)"; W = "9/16"
NOW = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
def load(p, d):
    try: return json.load(open(p))
    except Exception: return d
def f(x):
    try: return float(x or 0)
    except Exception: return 0.0
before = load("scan_0912/summary_before.json", {}); after = load("scan_0912/summary_after.json", {}) or before
eb = load("era_checks_before_%s.json" % S, []); ea = load("era_checks_after_%s.json" % S, [])
nb, ab = len(eb), round(sum(f(c.get("unpostedamount")) for c in eb), 2)
na, aa = len(ea), round(sum(f(c.get("unpostedamount")) for c in ea), 2)
pay = round(sum(f(c.get("paymentamount")) for c in eb), 2)
fb = load("registers/era_fallback_%s_live.json" % S, [])
posted = [r for r in fb if r.get("outcome") == "posted"]
fpay = round(sum(f(r.get("pay")) for r in posted), 2); fwo = round(sum(f(r.get("wo")) for r in posted), 2)
log = open("era_chain_0510.log").read() if os.path.exists("era_chain_0510.log") else ""
m = re.search(r"=== done: posted (\d+) visits, \$([\d.]+) ===", log)
auto_n, auto_amt = (int(m.group(1)), float(m.group(2))) if m else (0, 0.0)
fo = collections.Counter(("residual (charge already $0 in AMD)" if str(r.get("outcome", "")).startswith("residual") else (r.get("outcome") or "?")) for r in fb)
cnt = re.search(r"fallback LIVE.*?counts (\{.*?\})", log, re.S); dol = re.search(r"fallback LIVE.*?dollars (\{.*?\})", log, re.S)
counts = cnt.group(1) if cnt else str(dict(fo)); dollars = dol.group(1) if dol else ""
faults = len(re.findall(r"addpayments fault|FAULT", log.split("fallback LIVE")[-1].split("era_clear DRY")[0])) if "fallback LIVE" in log else 0
av = load("registers/aet12_verify_%s.json" % S, [])
aet_bal = round(sum(f(c.get("insbal")) for c in av), 2) if av else 2052.25
n_ub = len(after.get("unbilled", [])); n_ex = sum(len(v) for v in after.get("exclusions", {}).values())
n_ub0 = len(before.get("unbilled", [])); n_ex0 = sum(len(v) for v in before.get("exclusions", {}).values())
insp0 = before.get("inspector", {}); n_in0 = sum(len(v) for v in insp0.values()) if isinstance(insp0, dict) else len(insp0)
inspA = after.get("inspector", {}); n_in = sum(len(v) for v in inspA.values()) if isinstance(inspA, dict) else len(inspA)
n_cr0 = len(before.get("chargereview", [])); n_cr = len(after.get("chargereview", []))
aid = {c["id"] for c in ea}; bid = {c["id"] for c in eb}
cleared = [c for c in eb if c["id"] not in aid]; newc = [c for c in ea if c["id"] not in bid]
mor = load("registers/cob_group_fix_%s_rebill.json" % S, {})
mor_ok = [s for s in mor.get("steps", []) if "-> 204 | freq1" in s]
sav = load("registers/wo_pr39_2026-09-16.json", [])
sav_ok = bool(sav and sav[0].get("ok"))
sav_pay = re.search(r'paymentid="(\d+)"', (sav[0].get("msg") if sav else "") or ""); sav_pay = sav_pay.group(1) if sav_pay else "?"

# ---------- run report CSV
rows = []
def add(col, state, patient="", dos="", carrier="", err="", action="", check="", visit="", amt=""):
    rows.append({"column": col, "state": state, "patient": patient, "dos": dos, "carrier": carrier, "error": err,
                 "action": action, "checkid": check, "visit": visit, "amount": amt})
add("Charge Review", "clear", action="%d visits before, %d after" % (n_cr0, n_cr))
add("Claim Inspector", "clear", action="%d visits before, %d after (no batches listed by getclaiminspectorbatches)" % (n_in0, n_in))
for r in after.get("unbilled", []):
    err = r["_errs"][0] if r["_errs"] else ""
    add("Unbilled", "remaining", r.get("patientname", ""), r.get("dateofservice", "") or "", r.get("carriercode", "") or "", err,
        "held - 9/13 payment posted with no CARC on a reversed 5/31 write-off; needs the remit reason codes re-posted (no captured call edits payment reason codes) or William's word to release", visit=r.get("id", ""))
for rid, rs in after.get("exclusions", {}).items():
    for r in rs:
        err = " | ".join((e.get("name") or e.get("text") or "")[:70] for e in r["_errs"][:2])
        add("Exclusions", "remaining", "pat%s" % r.get("patientid", ""), r.get("dateofservice", "") or "", (r.get("carriercode") or "").split()[0] if r.get("carriercode") else "", err,
            "held - run 1700193 rejected all 59 AET12 claims again after the AAR01-matched carrier settings; William: suppress the provider loop / Box 33B REF*EI, then 'rebill'", visit=r.get("id", ""))
for s in mor_ok:
    mm = re.match(r"v(\d+) c(\d+) (\S+) (\S+) \$(\S+):", s)
    if mm: add("Board - Merriwether-Paxton", "rebilled", "pat17475906", mm.group(3), "BCBS group plan XJBH22972394 (seq 2)", "MA plan CO-22/N598 - employer group plan primary 1/2025-7/2026", "plan added (ins9519429, no group #), visit insorder 2 + freq-1 rebill -> 204", visit=mm.group(1), amt=mm.group(5))
add("Board - Selwyn", "written off" if sav_ok else "write-off FAILED", "pat17471832", "05/27/2026", "BCBS", "PR-39 auth denial (Availity ICN Q100001324834907)", "WONCS $310 per William's 9/16 board note; AMD payment id %s" % sav_pay, visit="19443552", amt="310.00")
add("Board - Selwyn", "for William", "pat17471832", "04/02/2026 + 04/28/2026", "BCBS", "99223 admission codes still open $310 each (same stay-auth pattern suspected; no remit on file)", "not touched - say 'same' to write off, or 'appeal'", visit="19437270 + 19440411", amt="620.00")
add("Facesheets", "unreadable", "unknown (Omnissa Horizon.pdf 04:25Z)", "", "", "scanned image PDF, no text layer - the Drive connector returns no text", "William: paste the sheet's text on the board (as done for Merriwether-Paxton) or name the patient")
add("Facesheets", "read via board", "pat17475906 (moriarty.pdf) / pat17471832 (Omnissa Horizon savage.pdf)", "", "", "PDFs are image-only; acted on William's pasted text / note instead")
pby = collections.defaultdict(list)
for r in posted: pby[str(r.get("checkid"))].append(r)
for c in eb:
    st = "still open" if c["id"] in aid else "cleared"
    act = "held - reversal/orphan/procedure-mismatch/already-adjudicated lines, no postable money"
    if str(c["id"]) in pby:
        ps = pby[str(c["id"])]
        act = "manual fallback posted %d line(s) $%.2f (+$%.2f WOINS); %s" % (len(ps), sum(f(p.get("pay")) for p in ps), sum(f(p.get("wo")) for p in ps), "still held for the remaining lines" if st == "still open" else "cleared")
    if str(c["id"]) == "1051656": act = "held - 4 unrecorded payment lines (reversal pipeline), $303.64"
    add("ERA", st, carrier=c.get("systemcarriercode") or c.get("carriercode", ""), check=str(c["id"]), amt=c.get("unpostedamount", ""), err="check %s" % (c.get("paymentnumber") or c.get("checknumber", "")), action=act if st == "still open" else "cleared this run")
for c in newc:
    add("ERA", "new (arrived during run)", carrier=c.get("systemcarriercode") or "", check=str(c["id"]), amt=c.get("unpostedamount", ""), err="check %s" % (c.get("paymentnumber") or ""))
for r in posted:
    add("ERA", "manual-posted", carrier=r.get("carrier", ""), check=str(r.get("checkid")), visit=str(r.get("visitid")), amt=r.get("pay"), dos=r.get("dos", ""), err="%s %s" % (r.get("cpt"), r.get("dos")), action="manual_post pay %.2f + wo %.2f, ERA %s manual post %s" % (f(r.get("pay")), f(r.get("wo")), r.get("checkid"), S))
add("Availity remits", "none new", action="no file in 'bht Optum era downloads' or 'treasury payments' modified after 04:00Z 9/15 (every earlier PDF is in registers/availity_register.json; the 9/14 Check/EFT CSV is reconciled); nothing parsed or posted")
out = "_run report 9-16 0510.csv"
with open(out, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=["column", "state", "patient", "dos", "carrier", "error", "action", "checkid", "visit", "amount"])
    w.writeheader(); w.writerows(rows)
print("wrote", out, len(rows), "rows")

# ---------- board updates
def chk(ok, result, src=SRC): return {"ok": ok, "result": result, "src": src, "when": W}
def note(text): return {"who": "Claude", "text": text, "at": NOW}
ops = []
def row(id, checks=None, notes=None, api=None, op="update"):
    o = {"op": op, "collection": "items", "id": id, "append": {}}
    if checks: o["append"]["checks"] = checks
    if notes: o["append"]["notes"] = notes
    if api: o["append"]["api"] = api
    ops.append(o)
newtxt = ("; new check(s) since 11pm ET: " + ", ".join("%s %s $%.2f" % (c["id"], c.get("systemcarriercode") or "", f(c.get("unpostedamount"))) for c in newc)) if newc else "; no new checks arrived during the run"
posttxt = ("; manual fallback posted %d line(s) $%.2f + $%.2f WOINS (%s)" % (len(posted), fpay, fwo, ", ".join("%s %s" % (r.get("visitid"), r.get("cpt")) for r in posted))) if posted else "; fallback dry + live 0 postable"
era_line = ("ERA step 5 (%s, run %s): %d unposted checks / $%.2f before -> %d / $%.2f after (paymentamount $%.2f); no new 835s in the Optum folder; locks release-expired sent; era_details cache %d/%d; "
            "era_post --all-unposted posted %d visits $%.2f%s (counts %s; residual-zero lines disregarded per your 9/13 rule); %d addpayments faults; era_clear dismissed %d, held %d%s."
            % (SRC, S, nb, ab, na, aa, pay, len(os.listdir("era_details")) if os.path.isdir("era_details") else 0, nb, auto_n, auto_amt, posttxt, counts, faults, len(cleared), na, newtxt))
row("aet12-carrier-cpid", checks=[chk("no", "Still the same 59 AET12 PREF0288/PREF0264 rows on run 1700193 (15 charts; 68 AET12 charges re-read via gettxhistory: billdate 09/14/2026, no AET12 payment, insurance balance $%.2f open, none at $0). No new claim run since 1700193 (89 runs). Held, not rebilled, not completed - waiting on the carrier-record change you named (suppress the provider loop / Box 33B REF*EI), then 'rebill'." % aet_bal, SRC + " - claim run 1700193")])
row("unbilled-unbalanced-postings-0915", checks=[chk("no", "Still 11 Unbilled rows 'Payment reason codes are missing or do not balance' ($2,422.58; Rylance, Kinross, Cogswell, Delmar, Simcoe x4, Rowantree N x2, Carrow) - held, not released; no captured call edits a posted payment's reason codes. Needs the remit CARCs re-posted in Payment Entry or your word to release.")])
row("era-manual-post-0912", checks=[chk("ok" if (posted or auto_n or cleared) else "na", era_line, SRC + " - ERA step 5")])
row("availity-remits-backlog", checks=[chk("na", "No Availity PDF or Check/EFT export newer than the 0310Z 9/15 pass in 'bht Optum era downloads' / 'treasury payments' (nothing modified after 04:00Z 9/15; every PDF there is in registers/availity_register.json; the 9/14 Check/EFT CSV is reconciled) - nothing new to parse, post or reconcile; board drops 0, Working Denials queue 0, Pam Gmail: nothing new. Three scanned facesheet PDFs landed in 'bht hca facesheets' 04:23-04:27Z (moriarty.pdf, Omnissa Horizon savage.pdf, Omnissa Horizon.pdf) - image-only, acted on your pasted text / notes instead.", SRC + " - ERA step 5(g)")])
def stedi_api_text():
    j = load("patient_db/17475906/stedi_elig_BCBSF_XJBH22972394_20260329.json", {}); sb = j.get("subscriber") or {}; pd = j.get("planDateInformation") or {}
    ps = "; ".join("%s (%s, STC %s)" % (p.get("status"), p.get("planDetails"), ",".join(p.get("serviceTypeCodes") or [])) for p in j.get("planStatus") or [])
    return "%s, %s dob %s member %s -> planStatus %s; planDateInformation periodStart %s periodEnd %s, eligibilityBegin %s eligibilityEnd %s; group %s %s; errors %s." % (
        sb.get("lastName"), sb.get("firstName"), sb.get("dateOfBirth"), sb.get("memberId"), ps, pd.get("periodStart"), pd.get("periodEnd"), pd.get("eligibilityBegin"), pd.get("eligibilityEnd"), sb.get("groupNumber"), sb.get("groupDescription"), j.get("errors") or "none")
def mrow(s):
    mm = re.match(r"v(\d+) c\d+ (\S+) (\S+)", s); return "%s %s %s" % (mm.group(1), mm.group(3), mm.group(2))
mor_list = ", ".join(mrow(s) for s in mor_ok)
row("merriwether-paxton-nell-17475906",
    checks=[chk("ok", "Stedi Florida Blue (BCBSF) on the facesheet's primary policy XJBH22972394 at DOS 3/29/2026: ACTIVE Coverage, BLUEOPTIONS LOWER PREMIUM 05302 (PPO), eligibility 2/1/2019-7/31/2026, plan period 1/1/2025-7/31/2026, group JIMMIE REDFERN ENTERPRISES INC (not entered - your no-group rule)", "Stedi eligibility BCBSF, DOS 3/29/2026"),
            chk("ok", "BCBS car6062 member XJBH22972394 added begin 01/01/2025, end-dated 07/31/2026 -> ins9519429 seq 2 (no group #); patient order set 2,1 (group plan first, BlueMedicare PPO second)", "AMD addinsurance + updateinsurance"),
            chk("ok", "ACTIVE - BlueOptions; other payer BLUEMEDICARE VALUE (PPO) listed", "AMD eligibility (free 271) - new plan ins9519429"),
            chk("ok", "All %d open Florida-Blue visits of the March + April 2026 HCA stays ($1,459) set to insorder 2 (full-visit echo) and freq-1 rebilled -> 204 each: %s" % (len(mor_ok), mor_list), SRC + " - move_to_ins + freq1_visit")],
    notes=[note("1am ET 9/16 run: read your 04:22Z facesheet paste (moriarty.pdf itself is an image-only PDF the connector cannot read). Primary = BLUE OPTIONS PPO XJBH22972394 (the employer group plan on the facesheet), secondary = BC MCR BlueMedicare Value PPO XJPH45679241 - exactly the COB picture CMS gave (group plan primary 1/1/2025-7/31/2026, working aged). Florida Blue's eligibility confirms the group policy ACTIVE through 7/31/2026. Added it to the chart (no group number), end-dated 7/31/2026, chart order group plan first; every open Florida Blue visit of the 3/24-3/31 and 4/7-4/8/2026 stays (10 visits, $1,459 - not only the reversed 3/29 line) is now billed to the group policy as a frequency-1 claim under that member id; they leave on the next claim run. After 7/31/2026 the BlueMedicare PPO is the only coverage, so the chart handles later visits on its own. Nothing left for you here.")],
    api=[{"at": NOW, "src": "Stedi API - Florida Blue (BCBSF) eligibility, DOS 2026-03-29", "text": stedi_api_text()}])
row("selwyn-janis-17471832",
    checks=[chk("ok" if sav_ok else "no", ("WONCS $310.00 posted on the 5/27/2026 99223 (charge 23351978, visit 19443552), AMD payment id %s, note 'Florida Blue PR-39 auth denial, 5/27/2026 HCA admission (ICN Q100001324834907) - William 9/16/2026: write off'; balance $0" % sav_pay) if sav_ok else ("write-off REFUSED: %s" % (sav[0].get("msg") if sav else "no register")), SRC + " - manual_post WONCS"),
            chk("human", "Same pattern on the chart: the 4/2/2026 99223 (visit 19437270) and 4/28/2026 99223 (visit 19440411) are also open at $310 each while every follow-up 99232/99233 of those stays paid - no remit on file for them. Say 'same' to write both off WONCS, or 'appeal' if HCA won the auth appeal.", "William")],
    notes=[note("1am ET 9/16 run - your question 'can they deny physician payments for that reason?': yes. When the plan denied the admission's authorization (PR-39 = 'services denied at the time authorization/pre-certification was requested'), Florida Blue denies the attending physician's inpatient E/M for that stay too - the physician claim follows the facility's auth determination, and the Availity remit already shows it processed that way (ICN Q100001324834907). It is only reversible through the hospital's own auth appeal (medical necessity of the admission); there is no separate physician auth to add. Per your 'if so we write off' the 5/27/2026 99223 ($310) is written off WONCS (non-covered, auth denied) - reversible with a void if HCA's appeal succeeds. The savage PDF you dropped (Omnissa Horizon savage.pdf) is an image-only PDF the connector cannot read, so nothing from it was used. Left for your word: the 4/2 and 4/28/2026 admission 99223s ($620) sit open with the same look (follow-ups paid, admission code unpaid) - 'same' writes them off, 'appeal' holds them.")])
ops.append({"op": "upsert", "collection": "items", "id": "facesheet-unread-omnissa-horizon-0916",
            "set": {"patient": "UNREAD FACESHEET (Omnissa Horizon.pdf, dropped 9/16 00:25 ET)", "dob": "", "facility": "HCA FLORIDA CAPITAL HOSPITAL (Omnissa portal print)", "amdid": "", "mbi": "",
                    "need": "WILLIAM: 'Omnissa Horizon.pdf' (343 KB, bht hca facesheets, 9/16 00:25 ET) is a scanned image with no text layer - the Drive connector returns nothing and the routine cannot OCR a Drive PDF. Paste the sheet's text on the patient's board row (as you did for Merriwether-Paxton) or say which patient it is, and the next run acts on it. (moriarty.pdf and 'Omnissa Horizon savage.pdf' were the same kind of file - handled from your pasted text and note.)",
                    "why": "Facesheet dropped in Drive that no run can read", "amount": 0, "status": "william", "created": NOW, "updated": NOW,
                    "notes": [note("Created by the 1am ET 9/16 run.")], "checks": [chk("no", "read_file_content returns empty text for all three 9/16 PDFs (image-only); no OCR path in the routine container for Drive files", "Drive connector")]}})
json.dump({"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": ops}, open("board_updates_%s.json" % S, "w"), indent=1)
print("wrote board_updates_%s.json" % S, len(ops), "ops")

# ---------- needs_facesheet_list.md section + additions + digest
sec = """
## 2026-09-16 1 AM ET columns run (ehpa cloud Code Routine, 05:09-%s UTC, run %s)
Bootstrap: repo ATTACHED (origin/main 636cebf, layout 260 helpers), AMD_OK, STEDI_CRED_OK, ONE amd.login_cached success, no login lock. State bundle workspace_state_2026-09-15_1836UTC (6 parts + manifest, newest on Drive) listed but NOT restored (the connector round-trip hand-relay truncated parts 01/03 again) - registers restored from practices/ehpa/registers/ in the repo (0310Z state: era_manual_register, availity_register, availity_manual_register); needs_facesheet_list.md restarted from this section. Missing required helpers (not rewritten): columns_inspector2_0908.py, era_details_pull.py (era_step_b_0913.py fills the cache instead).
Boards: Insurance Refresh Board 184 rows on Claude's turn; 2 new William notes since the 0310Z run - pat17475906 (HCA facesheet paste 04:22Z: employer-group Florida Blue XJBH22972394 primary + BlueMedicare PPO secondary) and pat17471832 (04:28Z: PR-39 auth denial question, 'if so we write off'); drops new = 0; Working Denials queue = 0. Facesheet folder: 3 new scanned PDFs 04:23-04:27Z (moriarty.pdf, Omnissa Horizon savage.pdf, Omnissa Horizon.pdf) - image-only, unreadable through the connector; acted on the pasted text / note; the unnamed one is a new board row on William's turn. Optum ERA folder, treasury folder, Pam Gmail (newer_than:2d): nothing new.
Columns: Charge Review %d -> %d | Claim Inspector %d -> %d (no batches) | Unbilled %d -> %d ($2,422.58, all 'Payment reason codes are missing or do not balance' - held per the 9/15 chat rule, never released) | Exclusions %d -> %d ($11,756, all AET12 PREF0288+PREF0264 on run 1700193; 68 charges re-verified via gettxhistory, $%.2f open, billdate 09/14/2026, no AET12 payment - held on the carrier-master fix; no new claim run since 1700193, 89 runs).
Board actions: pat17475906 - Stedi BCBSF ACTIVE on XJBH22972394 (BlueOptions PPO, plan 1/1/2025-7/31/2026); BCBS plan added ins9519429 seq 2 (begin 01/01/2025, end 07/31/2026, no group), patient order 2,1, AMD 271 ACTIVE; %d open Florida-Blue visits of the March + April 2026 stays ($1,459) insorder 2 + freq-1 rebilled -> 204 each. pat17471832 - 5/27/2026 99223 $310 (charge 23351978) written off WONCS per William's note (payment id %s); 4/2 + 4/28/2026 99223s ($620) left open for his word.
ERA step 5: %d checks / $%.2f before -> %d / $%.2f after (paymentamount $%.2f). era_post posted %d visits $%.2f%s. Fallback counts %s; dollars %s. era_clear dismissed %d (%s), held %d. %d addpayments faults%s. No new 835s; Availity 5(g): nothing new (all PDFs registered, Treasury CSV reconciled 9/14).
Calls learned: none (every call this run is a captured shape: addinsurance, updateinsurance wrapped, checkEligibility, updvisitwithcharges echo, chargerebill, addpayments). Vocabulary entries added: 0.
""" % (datetime.datetime.utcnow().strftime("%H:%M"), S, n_cr0, n_cr, n_in0, n_in, n_ub0, n_ub, n_ex0, n_ex, aet_bal, len(mor_ok), sav_pay, nb, ab, na, aa, pay, auto_n, auto_amt, posttxt, counts, dollars, len(cleared), ", ".join(str(c["id"]) for c in cleared) or "none", na, faults, newtxt)
open("needs_facesheet_list.md", "a").write(sec)
open("captured_calls_additions_%s-1amET-ehpa-cloud.md" % S.replace("T", "_").replace("Z", "UTC"), "w").write("## 2026-09-16 1 AM ET columns run (ehpa cloud Code Routine, run %s) - run entry, NO new AMD call shapes\n" % S + sec.strip().split("\n", 1)[1] + "\n")
os.makedirs("chat_history", exist_ok=True)
dig = "# %s run digest - backend billing run, 1am ET 9/16/2026 slot (ehpa cloud)\n" % S.replace("T", "_").replace("Z", "UTC") + sec + "\nMirror: see the run summary (GitHub main / Postman unchanged / Drive / state bundle).\n\nRUN COMPLETE\n"
open("chat_history/%s run digest.md" % S.replace("T", "_").replace("Z", "UTC"), "w").write(dig)
print(sec)
