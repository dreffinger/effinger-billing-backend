# PLAIN ENGLISH (run outputs, 9am ET 9/30/2026 run 2026-09-30T1310Z): builds this run's report files from the two column scans and the
#   run registers - the needs_facesheet_list.md section (chart ids only), the run report CSV (patient names - SendUserFile / Drive only),
#   the board update file for the Drive 'board inbox', the captured_calls additions file and the Drive digest. Decides nothing; writes
#   only local files under /home/claude/unbilled. Never touches AMD.
import json, csv, datetime, os
STAMP = "2026-09-30T1310Z"; SLOT = "9 AM ET 9/30 slot (ehpa cloud)"
b = json.load(open("scan_1310/summary_before.json")); a = json.load(open("scan_1310/summary_after.json"))
def cnt(s):
    insp = sum(len(v) for v in s["inspector"].values()); ub = int(s.get("unbilled_totalcount") or len(s["unbilled"]))
    ex = sum(len(r) for r in s["exclusions"].values()); cr = len(s["chargereview"])
    return cr, insp, ub, ex
cb, ca = cnt(b), cnt(a)
rel = json.load(open("registers/unbilled_release_%s.json" % STAMP))["rows"]
insp_dry = json.load(open("registers/insp_%s_dry.json" % STAMP))["visits"]
now = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
REFUSED_INSP = "`python3 insp_0930_1310.py --live` -> refused by the auto-mode classifier: 'Real-World Transactions' (dry run registers/insp_2026-09-30T1310Z_dry.json verified: gate ok on all three, 99489 carries mcode7)"
REFUSED_REPAIR = "writing William's unbilled_repair.py (Drive 'bht PCC Facesheets', 08:19Z) into the workspace -> refused: 'Modify Shared Resources' (7th consecutive run)"

# 1. needs list section (chart ids only)
sec = """
## %s - backend billing run, %s
- Columns: Charge Review %d -> %d | Claim Inspector %d -> %d (25 standing holds + 3 NEW rows, none bypassed - write refused) | Unbilled %d -> %d (7 'prior payor' rows released, rule b; 6 reason-code rows + 31 standing holds + 1 duplicate chart remain) | Exclusions %d -> %d (pat20863 v19445850 FLO99 PDTP0303 hold) | ERA 0 checks $0 -> 0 checks $0.
- NEW INSPECTOR ROWS (3): pat17477638 v19455623 (batch 127783) Pattern 35790 CCM add-on advisory - the 99489 already carries modifier 25 (mcode7); the visit is at SODALIS ALF (fac65) and its diagnosis list LEADS with I63.9 (acute stroke), so William's outpatient rule applies (I63.9 -> I69.30 dcode1034545425, never deleted) BEFORE the bypass; pat17476681 v19455801 (127783) + v19456218 (127793) Pattern 11256 (M25.559 + S70.00XA unspecified laterality) - primary-dx gate clear (G12.21 leads), advisory bypass + laterality log. All three planned in insp_0930_1310.py (dry run clean); %s. Nothing written to these visits. UI steps for William: Claim Inspector > batch 127783 > v19455623: change I63.9 to I69.30 on both CCM lines, save, then Bypass the 35790 advisory; batch 127783 v19455801 and batch 127793 v19456218: Bypass the 11256 advisory (or recode M25.559 / S70.00XA with the documented side).
- CLAIM INSPECTOR holds unchanged (25): pat17472874 x15 + pat17477640 x2 + pat17472703 x2 HCA admission dates (no 99223 anchor - William); pat17474541 v19430630 + pat17476036 v19456171 99489 without 99487 (coding - William); pat17473477 v19455625 + pat45668 v19455691 deceased guard (CCM after death - William void); pat17477208 v19455940 duplicate CCM lines; pat20863 v19455936 CCI 24078.
- UNBILLED released (7, rule b - primary claim out and unanswered, live charges re-read first): %s. Register registers/unbilled_release_%s.json (hideunbillablevisits success=1).
- UNBILLED reason-code rows held (6, payreasons --list = no-era-line x6: pat17470697 v19392264/v19392365/v19392381/v19392525 TRI05, pat17476020 v19454642 MCAD, pat17473245 v19454667 BCBS - each carries one $0 code-less payment + a WOINS): %s; `python3 payreasons.py --unbilled --live` not attempted this run (refused 5 runs in a row, and the cache has no line for these checks). UI steps: Unbilled > each visit > void the $0 code-less payment (checks 815876983 / 815906990 / 819872046), then Complete.
- UNBILLED holds unchanged (31): pat17472874 x15 + pat17474541 (inspector holds); pat17477183 x2 Medicaid PENDING per the Aviata census; pat17473232 + pat17471681 CCM after death (William void); pat17477639 facesheet; pat17477842 + pat17477870 duplicate charts; pat17477850 x4 + pat17477898 x2 CHP member ids; pat17477892 x2 facesheet; pat17477933 duplicate chart (William).
- ERA: 0 unposted checks before and after (era_post --all-unposted --dry: 0 checks); nothing uploaded, posted or cleared. Availity 5(g): no new PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments'.
- SOURCES: Working Denials queue 0; board drops 0; 0 board rows changed since 06:00Z; Pam Gmail: the 8 admit emails of 9/28-9/29 all worked by earlier runs (newest 03:21Z 9/29 Pruitt admit, worked 0510Z 9/29); Drive: no new remit / facesheet / census / 835 / Availity / treasury file after 08:00Z outside William's own uploads (columns_task_prompt_ehpa_cloud_v9.txt, unbilled_repair.py, two Git installers in 'bht PCC Facesheets'); GitHub inbox: no unapplied PACKAGE manifest; both board inbox registries list none of the current inbox files - nothing trashed.
- Bootstrap: repo attached (origin/main bf971f1), layout 713 helpers, registers 402 from practices/ehpa/registers, pseudonyms 322 (9/29 Drive copy); AMD password from the AMD_PSW environment credential, ONE login 13:15Z, no lock; STEDI_CRED_OK; state bundle: none restored (Drive newest 2026-09-18, older than main; patient_db/ + era_details/ start empty). Missing helpers (not rewritten): era_details_pull.py, columns_inspector2_0908.py, working_denials.py; unbilled_repair.py install refused.
- Prompt: the scheduled text is v7 (2-hourly); William's v9 (Drive 08:20Z 9/30, nightly 1:07 AM ET + auto-mode rules) honoured where it applies - named helpers with --dry then --live, no inline heredoc writes, no permission-setting edits, refusals recorded verbatim.
- Calls learned: none new (registered calls only).
""" % (STAMP, SLOT, cb[0], ca[0], cb[1], ca[1], cb[2], ca[2], cb[3], ca[3], REFUSED_INSP,
       "; ".join("v%s pat%s" % (r["vid"], r["pid"]) for r in rel), STAMP, REFUSED_REPAIR)
open("needs_facesheet_list.md", "a").write(sec)
open("needs_facesheet_list_section_%s.md" % STAMP, "w").write(sec)

# 2. run report CSV (names OK - William only)
name = {}
for r in b["unbilled"]: name[r.get("patientid")] = r.get("patientname")
for vs in b["inspector"].values():
    for v in vs: name[v["pid"]] = v["name"]
rows = [["column", "status", "patient", "amdid", "visit", "dos", "carrier", "error", "action"]]
for vs in b["inspector"].values():
    for v in vs:
        vid = v["vid"]; err = v["errs"][0][1][:90] if v["errs"] else ""
        if vid in ("19455623", "19455801", "19456218"):
            act = "NEW - bypass planned (dry ok) but the live helper was refused by the auto-mode classifier; " + ("I63.9 -> I69.30 swap needed first (Sodalis ALF)" if vid == "19455623" else "laterality advisory, gate clear")
        else:
            act = "standing hold (William)"
        rows.append(["Claim Inspector", "remaining", v["name"], v["pid"], vid, "", "", err, act])
seen = set()
for r in b["unbilled"]:
    vid = r.get("id")
    if vid in seen: continue
    seen.add(vid)
    err = (r["_errs"][0] if r["_errs"] else "")[:80]
    if any(x["vid"] == vid for x in rel): st, act = "cleared", "released (rule b: primary claim out and unanswered)"
    elif "Payment reason" in err: st, act = "remaining", "held - $0 code-less payment to void (unbilled_repair.py install refused; payreasons no-era-line)"
    elif "Insurance order" in err: st, act = "remaining", "standing hold (facesheet / member id / duplicate chart / Medicaid pending / deceased - William)"
    else: st, act = "remaining", "inspector hold"
    dos = r["_chgs"][0].get("begindate") or r["_chgs"][0].get("dos") if r["_chgs"] else ""
    rows.append(["Unbilled", st, r.get("patientname"), r.get("patientid"), vid, dos or "", r.get("carriercode") or "", err, act])
for rid, rs in b["exclusions"].items():
    for r in rs:
        e = r["_errs"][0] if r["_errs"] else {}
        rows.append(["Exclusions", "remaining", r.get("patientname"), r.get("patientid"), r.get("id"), "", r.get("carriercode"), (e.get("name") or e.get("text") or "")[:80], "standing hold: PDTP0303 admission date on the FCC claim (William)"])
rows.append(["ERA", "n/a", "", "", "", "", "", "0 unposted checks before and after", "nothing to post"])
with open("_run report 9-30 0910.csv", "w", newline="") as f: csv.writer(f).writerows(rows)

# 3. board update file
ops = [
 {"op": "upsert", "collection": "items", "id": "availity-remits-backlog", "set": {},
  "append": {"checks": [{"ok": "na", "result": "9 AM ET 9/30: no new Availity PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments'; ERA Center 0 checks before and after; Working Denials queue 0; board drops 0; 0 rows changed since 06:00Z; Pam Gmail: nothing newer than the 03:21Z 9/29 Pruitt admit (worked). Columns 0/28/45/1 -> 0/%d/%d/%d: seven Unbilled 'prior payor' rows released (rule b); the three new inspector advisories (pat17477638 v19455623 35790 + I63.9->I69.30; pat17476681 v19455801, v19456218 11256) were planned and dry-run clean but the live bypass helper was refused by the auto-mode classifier ('Real-World Transactions') - left for the next run / William's UI.", "src": "9am ET 9/30 columns run (ehpa cloud)", "when": "9/30"}]}},
 {"op": "upsert", "collection": "items", "id": "gantry-davin", "set": {},
  "append": {"checks": [{"ok": "na", "result": "9 AM ET 9/30: two new SNF visits (v19455801 99487+99489 9/20/2026 $315, v19456218 99309 9/24/2026 $141) sit in the Claim Inspector on Pattern 11256 only (M25.559 + S70.00XA unspecified laterality; G12.21 leads, primary-dx gate clear). Bypass planned (insp_0930_1310.py, dry run clean) but the live write was refused by the auto-mode classifier. Visit order 2,5 (Medicare first). UI: Claim Inspector batches 127783 / 127793 > Bypass the 11256 advisory on both, or recode with the documented side.", "src": "9am ET 9/30 columns run (ehpa cloud)", "when": "9/30"}]}},
]
json.dump({"schema": "irb-board-updates/1", "source": "backend billing run %s" % STAMP, "created": now, "ops": ops}, open("board_updates_%s.json" % STAMP, "w"), indent=1)

# 4. additions file
add = """## 2026-09-30 1310 UTC - 9am ET backend billing run (ehpa cloud copy) - no new call shapes
- Calls used (all captured earlier): getclaimcenteroverview, getreviewcharges, getclaiminspectorbatches/charges, getclaimunbillablecharges, getclaimrunstatus/getclaimexclusioncharges (columns_scan.py before + after), GET /api/era/checks (era_post.py --all-unposted --dry: 0 checks), getchargedetaildataicd10 by charge id (resave.detail, read-only gate), gettxhistory visitid= (txh.fetch_visit, read-only), hideunbillablevisits hide=-1 (unbilled_release_1310.py --live, 7 visits, success=1).
- Permission lesson (auto mode, v9 rules followed): the named-helper form passed for hideunbillablevisits (`python3 unbilled_release_1310.py --live`) but `python3 insp_0930_1310.py --live` (updvisitwithcharges dx swap + bypassclaimedits) was refused 'Real-World Transactions', and writing William's unbilled_repair.py from Drive into the workspace was refused 'Modify Shared Resources' (7th run). Nothing retried, split or re-encoded; the report carries the UI steps.
"""
open("captured_calls_additions_2026-09-30_1310UTC-9amET-ehpa-cloud.md", "w").write(add)
open("captured_calls.md", "a").write("\n" + add)

# 5. digest
os.makedirs("chat_history", exist_ok=True)
dig = """# %s run digest - backend billing run, %s

- Bootstrap: repo ATTACHED (origin/main bf971f1 at start; session branch claude/pensive-einstein-rcxqub, work on main); net AMD_OK / STEDI_CRED_OK / GitHub reachable; AMD password from the AMD_PSW environment credential - ONE login 13:15Z, no lock; START marker 13:12Z (guard clear: newest START 09:13Z, digest 0910Z RUN COMPLETE). Layout from main (713 helpers); pseudonyms (322 names, 9/29 copy); registers from practices/ehpa/registers (402). Missing helpers (not rewritten): columns_inspector2_0908.py, era_details_pull.py, working_denials.py; unbilled_repair.py (William's 08:19Z Drive upload) could not be installed - classifier refusal. State bundle restored: none (Drive newest 2026-09-18 older than main). GITHUB INBOX: no unapplied PACKAGE manifest. Scheduled prompt is v7; William's v9 (08:20Z) honoured where it applies.
- Columns: Charge Review %d -> %d | Claim Inspector %d -> %d (25 standing holds + 3 new advisory rows; live bypass refused) | Unbilled %d -> %d (7 'prior payor' rows released, rule b) | Exclusions %d -> %d (pat20863 v19445850 FLO99 PDTP0303 hold) | ERA 0 checks $0 -> 0 checks $0.
- AMD WRITES: DONE - hideunbillablevisits x7 (v19392347, v19441047, v19442414, v19453094, v19453102, v19453106, v19453209). REFUSED (verbatim): %s; %s. Not retried.
- NEW inspector rows left for the next run / William: pat17477638 v19455623 (35790; I63.9 leads on a Sodalis ALF CCM visit -> I69.30 swap first), pat17476681 v19455801 + v19456218 (11256 laterality, gate clear).
- Sources: Working Denials queue 0; board drops 0; 0 board rows changed since 06:00Z; Pam Gmail nothing new; Drive nothing new outside William's uploads; Availity 5(g) nothing new; board inbox: nothing trashed (registries list none of the current files).
- Calls captured: none new. Vocabulary entries added: 0.
- Mirror: see the finalize line below.
""" % (STAMP, SLOT, cb[0], ca[0], cb[1], ca[1], cb[2], ca[2], cb[3], ca[3], REFUSED_INSP, REFUSED_REPAIR)
open("chat_history/%s run digest.md" % STAMP, "w").write(dig)
print("before", cb, "after", ca, "released", len(rel))
