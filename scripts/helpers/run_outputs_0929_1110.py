# PLAIN ENGLISH (run outputs for the 7am ET 9/29/2026 slot - ehpa cloud run 2026-09-29T1110Z)
# Decides: nothing. Reads this run's registers (scan_0929_1110 before/after, era_details, era_co45_fix register) and writes:
#   "_run report 9-29 0700.csv" (names allowed - SendUserFile only), board_updates_2026-09-29T1110Z.json (trail appends, one decision row on
#   William's turn), a needs_facesheet_list.md section (pat ids only), captured_calls_additions_*.md, the chat-history digest
#   (--final adds the mirror result), and appends this run's outcomes to registers/era_manual_register.json.
# Never touches: AMD, the board databases. Patient names come from the scan/ERA data at run time - none are written in this file.
import json, csv, os, sys, time, datetime
S = "2026-09-29T1110Z"; NOW = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"); SLOT = "7am ET 9/29 columns run (ehpa cloud)"
sc_b = json.load(open("scan_0929_1110/summary_before.json")); sc_a = json.load(open("scan_0929_1110/summary_after.json"))
fix = json.load(open("registers/era_co45_fix_%s.json" % S))
det = {c: json.load(open("era_details/%d.json" % c))["eracheckdetails"] for c in (1052872, 1052873, 1052874)}
names = {}
for vs in sc_b["inspector"].values():
    for v in vs: names[v["pid"]] = v["name"]
for r in sc_b["unbilled"]: names[r["patientid"]] = r["patientname"]
for c in det.values():
    for v in c: names[str(v["patientid"])] = v["patientname"]
for rows in sc_b["exclusions"].values():
    for r in rows: names[r["patientid"]] = r["patientname"]
def nm(pid): return names.get(str(pid), "pat%s" % pid)
rows = []
def R(col, status, pid, dos, carrier, err, action, vid="", amt=""):
    rows.append({"column": col, "status": status, "patient": nm(pid), "patientid": pid, "visit": vid, "dos": dos, "carrier": carrier, "error": err, "amount": amt, "action": action})
# ---- ERA
wo = {r["cid"]: r for r in fix["A"]}
posted = 0.0; wo_a = 0.0
for v in det[1052872]:
    for ch in v["charges"]:
        f = wo.get(str(ch["chargedetailid"]), {})
        posted += float(ch["paymentamount"] or 0); wo_a += f.get("wo", 0) if f.get("result") == "posted" else 0
        R("ERA 1052872 MEDICARE 819872046", "posted", v["patientid"], ch["dos"][:10], "FLO02", "paid %.2f CO %.2f PR %.2f" % (ch["paymentamount"], f.get("co", 0), f.get("pr", 0)),
          "Post button posted the payment; CO-45/CO-253 %.2f written off WOINS (trace 819872046, %s); PR-2 %.2f left for the secondary/patient%s" % (f.get("wo", 0), f.get("result"), f.get("pr", 0), " (balance moved back from the patient first)" if f.get("move") not in (False, None, "") else ""), v["visitid"], "%.2f" % ch["paymentamount"])
wo_b = sum(r.get("wo", 0) for r in fix["B"] if r.get("result") == "posted")
for r in fix["B"]:
    R("ERA 1052873 MEDICARE 350011571 ($0)", "settled", r["pid"], "", "FLO02", "CO-29 on the 9/22 frequency-1 resubmission of a visit Medicare PAID 9/9/2026 (check %s)" % r["check"],
      "not untimely - already adjudicated; original remit's contractual %.2f written off WOINS with check %s (%s); PR-2 %.2f stays; nothing rebilled" % (r.get("wo", 0), r["check"], r.get("result"), r.get("pr2", 0)), r["vid"], "0.00")
for v in det[1052873]:
    if str(v["visitid"]) in [r["vid"] for r in fix["B"]]: continue
    ch = v["charges"][0]; codes = ";".join(c["reasoncode"] for c in ch.get("carc", [])); rarc = ";".join(x.get("remarkcode") for x in ch.get("rarc", []) if x.get("remarkcode") != "#AM")
    if str(v["visitid"]) in ("19392574", "19392671", "19392755", "19392843", "19392844"):
        act = "already adjudicated (Medicare paid 9/9, contractual written off 9/9-9/20, PR-2 residual stays); the 9/22 resubmission drew CO-29 - nothing to do"
    elif str(v["patientid"]) == "17473199":
        act = "CO-109/N418 misrouted: Medicare 271 + Stedi MBI at DOS + Florida Blue 271 all name BCBS of Michigan Medicare Advantage PPO H9572 (UAW retirees, via Florida Blue, member XYL842788829) active from 1/1/2026 - BCBS plan re-opened, patient order set BCBS first, visit set to seq 1 and freq-1 rebilled (204)"
    else:
        act = "CO-109/N418 misrouted: Stedi UHC 87726 at DOS 3/2/2026 = UnitedHealthcare HMO ACTIVE (chart UNI20 911779256 begin 1/17/2026) - visit set to seq 3 (UNI20) and freq-1 rebilled (204)"
    R("ERA 1052873 MEDICARE 350011571 ($0)", "worked", v["patientid"], v["dos"][:10], "FLO02", "%s %s" % (codes, rarc), act, v["visitid"], "0.00")
for v in det[1052874]:
    ch = v["charges"][0]
    R("ERA 1052874 UHC W0524004 ($0)", "already handled", v["patientid"], v["dos"][:10], "UNI20", "PR-27 coverage terminated", "wrong-payer denial already re-routed by the 9/23-9/24 runs (charge now at %s, billed 9/23-9/24) - nothing to do; check dismissed" % ("HUM01" if str(v["patientid"]) == "24853" else "FLO02"), v["visitid"], "0.00")
# ---- Exclusions
for rid, lst in sc_b["exclusions"].items():
    for r in lst:
        err = (r["_errs"][0].get("name") or "")[:90]
        if r["carriercodeshort"] == "HUM01":
            R("Exclusions", "completed", r["patientid"], r["_chgs"][0]["dos"].strip(), "HUM01", err, "duplicate-claim rejection on run %s: Humana already holds the claim PENDING since 9/26 (Stedi 277 ICN %s) - completed, not rebilled" % (rid, "820262680340223" if r["id"] == "19427585" else "820262680341548"), r["id"], "315.00")
        else:
            R("Exclusions", "hold", r["patientid"], r["_chgs"][0]["dos"].strip(), "FLO99", err, "standing hold - FCC PDTP0303 needs the related admission date (William)", r["id"], r["_chgs"][0]["totalfee"])
# ---- Inspector / Unbilled holds (unchanged)
HOLD = {"17472874": "HCA admission date - no 99223 anchor on the chart (William)", "17477640": "HCA admission date - no 99223 anchor (William)", "17472703": "HCA admission date - no 99223 anchor (William)",
        "17474541": "99489 without 99487 - coding (William)", "17476036": "99489 without 99487 + unspecified-laterality S91.309D - coding (William)", "17473477": "deceased guard - CCM after death (William void)",
        "45668": "deceased guard - CCM after death (William void)", "17477208": "duplicate CCM lines (William)", "20863": "CCI 24078 history procedure (William)"}
for bid, vs in sc_a["inspector"].items():
    for v in vs: R("Claim Inspector", "hold", v["pid"], "", "", "; ".join(e[1][:60] for e in v["errs"][:2]), HOLD.get(v["pid"], "standing hold"), v["vid"])
UHOLD = {"17477183": "Medicaid PENDING per the Aviata census - facesheet/Medicaid number (William)", "17473232": "CCM after death (William void)", "17471681": "CCM after death (William void)", "17477639": "facesheet needed (William)",
         "17477842": "duplicate charts - merge (William)", "17477870": "duplicate charts - merge (William)", "17477850": "CHP member id needed (William)", "17477898": "CHP member id needed (William)", "17477892": "facesheet needed (William)"}
for r in sc_a["unbilled"]:
    R("Unbilled", "hold", r["patientid"], "", r.get("carriercode") or "", "; ".join(r["_errs"][:2]), UHOLD.get(r["patientid"], HOLD.get(r["patientid"], "inspector hold")), r["id"])
with open("_run report 9-29 0700.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["column", "status", "patient", "patientid", "visit", "dos", "carrier", "error", "amount", "action"]); w.writeheader(); w.writerows(rows)
# ---- era_manual_register.json append
reg = json.load(open("registers/era_manual_register.json"))
seen = {(str(r.get("checkid")), str(r.get("chargeid") or r.get("visitid"))) for r in reg}
def add(**k):
    if (str(k.get("checkid")), str(k.get("chargeid") or k.get("visitid"))) in seen: return
    reg.append(k)
for v in det[1052872]:
    for ch in v["charges"]:
        f = wo.get(str(ch["chargedetailid"]), {})
        add(checkid="1052872", checkclaimid=v["checkclaimid"], visitid=v["visitid"], pid=v["patientid"], cpt=ch.get("chargecode"), dos=ch["dos"][:10], era_paid=ch["paymentamount"], carrier="FLO02", checkno="819872046", when=S, chargeid=str(ch["chargedetailid"]), outcome="posted", co45_correction=f.get("wo", 0), co45_result=f.get("result"))
for r in fix["B"]:
    add(checkid="1052873", visitid=int(r["vid"]), pid=int(r["pid"]), cpt=r.get("cpt"), carrier="FLO02", checkno=r["check"], when=S, chargeid=r["cid"], outcome="already-adjudicated (CO-29 on a resubmission); contractual corrected", co45_correction=r.get("wo", 0), co45_result=r.get("result"))
for v in det[1052873]:
    if str(v["visitid"]) in [r["vid"] for r in fix["B"]]: continue
    add(checkid="1052873", checkclaimid=v["checkclaimid"], visitid=v["visitid"], pid=v["patientid"], carrier="FLO02", checkno="350011571", when=S, chargeid=str(v["charges"][0]["chargedetailid"]), outcome="denial-handled: " + ("already adjudicated" if str(v["visitid"]) in ("19392574", "19392671", "19392755", "19392843", "19392844") else "wrong payer re-routed + freq-1 rebilled"))
for v in det[1052874]:
    add(checkid="1052874", checkclaimid=v["checkclaimid"], visitid=v["visitid"], pid=v["patientid"], carrier="UNI20", checkno="W0524004", when=S, chargeid=str(v["charges"][0]["chargedetailid"]), outcome="denial-handled: PR-27 wrong payer already re-routed 9/23-9/24")
json.dump(reg, open("registers/era_manual_register.json", "w"), indent=1)
# ---- needs section
needs = """## %s - backend billing run, 7 AM ET 9/29 slot (ehpa cloud)
- Columns: Charge Review 0 -> 0 | Claim Inspector 25 -> 25 (every row a standing hold, same visit ids as 0910Z) | Unbilled 31 -> 31 (no new rows; every row a standing hold) | Exclusions 3 -> 1 (two HUM01 duplicate-claim rejections on run 1700243 completed - pat17473383 v19427585 + v19430729, Humana holds both PENDING since 9/26; pat20863 v19445850 FLO99 PDTP0303 hold stays; overview says 11/$2,194 but the list calls return one row) | ERA 3 checks $2,797.47 -> 0.
- CLAIM INSPECTOR holds unchanged (25): pat17472874 x15 + pat17477640 x2 + pat17472703 x2 HCA admission dates (no 99223 anchor - William); pat17474541 v19430630 + pat17476036 v19456171 99489 without 99487 (coding - William); pat17473477 v19455625 + pat45668 v19455691 deceased guard (CCM after death - William void); pat17477208 v19455940 duplicate CCM lines; pat20863 v19455936 CCI 24078. Nothing bypassed, nothing resaved.
- UNBILLED holds unchanged (31): pat17472874 x15 + pat17474541 (inspector holds); pat17477183 x2 Medicaid PENDING per the Aviata census; pat17473232 + pat17471681 CCM after death (William void); pat17477639 facesheet; pat17477842 + pat17477870 duplicate charts; pat17477850 x4 + pat17477898 x2 CHP member ids; pat17477892 x2 facesheet. No new 'prior payor' rows this slot.
- ERA: Medicare ACH 819872046 (ERA 1052872, $2,797.47, 32 claims / 39 lines) posted with the Post button ($2,797.29 auto-posted, $0.18 provider-level L6 adjustment disregarded) - the button left every CO-45/CO-253 contractual on the balance (the 9/23 defect, now on Medicare): 39 lines corrected WOINS $%.2f with the trace number (3 charts with no secondary moved back from the patient first; PR-2 left). Medicare NON 350011571 (ERA 1052873, $0, 14 lines): 11 CO-29 lines were frequency-1 resubmissions (9/22) of visits Medicare paid 9/9/2026 - already adjudicated, NOT untimely write-offs; 6 of them still carried the original remit's contractual -> WOINS $%.2f with the 9/9 check numbers, PR-2 stays; 3 CO-109/N418 misrouted lines re-routed (pat17473199 v19455653 -> BCBS Medicare Advantage seq 1; pat17472874 v19455322 + v19455323 -> UNI20 seq 3) and freq-1 rebilled (204 x3). UHC W0524004 (ERA 1052874, $0, 5 PR-27 lines): all five visits were already re-routed 9/23-9/24 (pat24853 x2 at HUM01, pat17476042 x2 + pat17470802 at FLO02). Both $0 checks dismissed; ERA Center empty after. Residuals disregarded: $0.18 (L6). Availity 5(g): no new PDF or Check/EFT export.
- SOURCES: Working Denials queue 0; board drops 0; 0 board rows changed since 08:30Z; Pam Gmail: the 8 admit emails of 9/28-9/29 were all worked by earlier runs, nothing newer than 03:21Z; Drive: no new remit / facesheet / census / 835 / Availity file since 09:00Z outside the routine's own files; GitHub inbox: no unapplied PACKAGE manifest.
- FOR WILLIAM (board row berry-priscilla-denials): pat17473199's whole 2026 (16 charges, ~$2,785, 1/27-8/23/2026) sits at $0 after Florida Blue ($0, checks 213403769 9/9 and 213387714 9/2) and then Medicare ($0, check 349935856 9/11) both denied - both payers' 271s now say her plan is BCBS of Michigan Medicare Advantage PPO H9572 (UAW retirees, billed through Florida Blue as XYL842788829) since 1/1/2026; the 9/8 switch to Medicare-first was wrong. Needs the Florida Blue denial reasons (Availity) and a decision on voiding the write-offs and rebilling to BCBS.
- Calls learned: none new (lesson recorded: the Post button leaves CO-45 on the balance for Medicare too; Medicare PR-2 = 20%% of allowed and allowed = paid/0.784 reconstructs a missing remit exactly). Missing helpers (not rewritten): era_details_pull.py, columns_inspector2_0908.py.
""" % (S, wo_a, wo_b)
open("needs_section_%s.md" % S, "w").write(needs)
open("needs_facesheet_list.md", "a").write("\n" + needs)
# ---- board updates
ops = []
def app(rid, text, ok="na", src=SLOT, when="9/29"):
    ops.append({"op": "upsert", "collection": "items", "id": rid, "append": {"checks": [{"ok": ok, "src": src, "result": text, "when": when}]}})
app("availity-remits-backlog", "7 AM ET 9/29: no new Availity PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments'; no ScanSnap batch; Working Denials queue 0; board drops 0; 0 rows changed since 08:30Z; Pam Gmail: nothing newer than the 03:21Z Pruitt admit (worked 0510Z). ERA Center 3 checks $2,797.47 -> 0: Medicare ACH 819872046 posted (32 claims, $2,797.29) + 39 CO-45 corrections WOINS $%.2f; Medicare NON 350011571 and UHC W0524004 ($0 denial remits) worked and dismissed. Columns 0/25/31/3 -> 0/25/31/1." % wo_a)
app("bcbs-patient-balance-audit-0918", "7 AM ET 9/29: not worked this run (same blocker). The Post-button CO-45 defect hit the MEDICARE carrier tonight too: ERA 1052872 (ACH 819872046) posted 39 lines with the CO-45/CO-253 reasons on the payment and payreasonwoamount 0 - every contractual stayed on the insurance balance (or the patient balance on the 3 charts with no secondary); corrected WOINS $%.2f with the trace number. Carriers needing the correction pass after the Post button now include Florida Medicare." % wo_a)
app("aet12-carrier-cpid", "7 AM ET 9/29: HOLD per your 9/21 word - not rebilled, not re-verified this slot; Exclusions 3 -> 1 (two HUM01 duplicates completed, the FLO99 PDTP0303 hold), none AET12; newest claim run 1700243.")
app("dunstan-josiah", "7 AM ET 9/29: Humana rejected the 9/27 resubmissions of the 12/28/2025 and 1/27/2026 CCM claims ($315 each, v19427585 / v19430729) as duplicates of previously processed claims - Stedi 277 shows Humana holds both PENDING 'awaiting benefit determination' since 9/26 (ICNs 820262680340223 / 820262680341548). Exclusions completed, nothing rebilled; the answer comes on Humana's remit.", ok="ok")
app("thackeray-kendrew-17472874", "7 AM ET 9/29: Medicare answered CO-109/N418 'misrouted' on the 3/2 and 3/4/2026 SNF visits (v19455323 99309 $141, v19455322 99316 $160) sent to FLO02 9/24 - Stedi UHC 87726 at DOS 3/2/2026 says UnitedHealthcare HMO ACTIVE (the chart's UNI20 911779256, begin 1/17/2026), so both visits were set to the UNI20 sequence and freq-1 rebilled (204 x2). The 15 April-2026 HCA visits are still held for the admission date (your turn).", ok="ok")
ops.append({"op": "upsert", "collection": "items", "id": "berry-priscilla-denials",
            "set": {"status": "william", "need": "WILLIAM: her whole 2026 (16 charges, ~$2,785: CCM 1/27, 2/26, 5/17, 6/25, 7/17, 8/23; 99349 2/18, 4/29, 7/22; G0439 7/12) sits at $0 after Florida Blue denied ($0 on checks 213403769 9/9 + 213387714 9/2) and then Medicare denied ($0 on 349935856 9/11; and CO-109/N418 'misrouted' on the 9/20 CCM tonight). Medicare's own 271, Stedi's MBI lookup at DOS 9/20 and Florida Blue's 271 all say she is on BCBS OF MICHIGAN MEDICARE ADVANTAGE PPO H9572 (UAW Retirees Medical Benefits, billed through Florida Blue as XYL842788829) since 1/1/2026 - the 9/8 switch to Medicare-first was wrong (AARP M62983818 answers AAA 72 and is her Part D, not a Medigap). Tonight: BCBS plan re-opened (end date cleared), patient order set BCBS first, the 9/20 CCM ($206, v19455653) sent to BCBS as an original. Decide: (1) pull the Florida Blue denial reasons for the 9/2 and 9/9 remits (Availity) - if they are COB/'Medicare primary' the claims need the MA member id BCBS expects (the 8/23 CCM billed to BCBS with XYL842788829 also came back $0); (2) say 'void and rebill' and the run voids the 2026 $0 write-offs and re-sends all 16 charges to BCBS."},
            "append": {"checks": [{"ok": "no", "src": SLOT, "result": "Medicare ERA 350011571 (9/29): CO-109/N418 on the 9/20/2026 99487 ($206, v19455653) billed FLO02 9/24. AMD 271: Florida Blue XYL842788829 ACTIVE 'PR MED ADV'; Medicare ACTIVE A/B with PR H9572 BCBS OF MICHIGAN + OT S8841 OPTUM OHIO (Part D); AARP M62983818 REJECTED AAA 72. Stedi MBI at DOS 9/20: BCBS of Michigan PPO COB 1/1/2026. Stedi BCBSF elig at DOS 9/20: Active PR, plan 710, UAW RETIREES MEDICAL BENEFITS.", "when": "9/29"},
                                  {"ok": "ok", "src": SLOT, "result": "BCBS plan ins9512818 end date cleared; patient insorder 2,3 -> 1; visit 19455653 set to seq 1 and freq-1 rebilled (204). The 2026 $0 balances were NOT touched - your decision.", "when": "9/29"}],
                       "notes": [{"who": "Claude", "text": "Both payers say BCBS Michigan Medicare Advantage is her 2026 plan. The 9/20 CCM is re-sent to BCBS; the rest of 2026 (~$2,785 at $0) needs your word - see the need text.", "at": NOW}]}})
board = {"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": ops}
json.dump(board, open("board_updates_%s.json" % S, "w"), indent=1)
# ---- captured calls additions
add_md = """# captured_calls additions - 2026-09-29 1110 UTC (7 AM ET) ehpa cloud run

No new call shapes this run. Lessons recorded against existing calls:

- **posterapayments (the ERA Center Post button) leaves CO-45 on the balance for FLORIDA MEDICARE too** (9/29/2026, ERA 1052872, ACH 819872046, 32 claims / 39 lines): every line carried the CO45 + CO253 reasons on the payment with `payreasonwoamount 0`, so after the post each charge showed insurance balance = CO + PR (patient balance on the 3 charts with no secondary). Correction = the 9/23 pass: `move_to_ins.move(cid)` where the balance sits on the patient, then `manual_post.post(cid, "FLO02", 0.0, CO45+CO253, "WOINS", checknumber=<trace>, depositdate=<check date>)`; PR-2 is left for the crossover. Script `era_co45_fix_1110.py` (reads the check details, refuses any line whose live balance != CO + PR). Carriers now known to need the pass: Florida Blue, VA CCN, CAP07/UHC, Ambetter, Humana, Medicaid FFS, Florida Medicare.
- **A $0 CO-29 (N211) line on a Medicare remit can be a frequency-1 resubmission of a claim Medicare already PAID** - read the live charge before treating it as untimely: pat17470697 x9, pat17468923, pat17470939 (ERA 1052873) all carried a 9/9/2026 Medicare payment; the 9/22 resend drew CO-29. No WOLATE; what was missing was the original remit's contractual. When the original remit is not in the cache, Medicare Part B numbers reconstruct it exactly: allowed = paid / 0.784 (80% less the 2% sequestration), PR-2 = 20% of allowed, WOINS = charge - allowed + CO-253 (= live insurance balance - PR-2); verified against sibling lines that carried the 9/9 WOINS (33.76 on 99232 / 43.80 on 99233).
- **CO-109 + N418 on a Medicare remit = an MA enrollment the chart does not show**: AMD's free 271 on the Medicare plan lists the MA contract under the other-payer EB (e.g. `PR 18:H9572 BCBS OF MICHIGAN`), Stedi's MBI lookup at the DOS confirms the COB date, and the MA payer's own 271 (Stedi `BCBSF` / `87726` with the chart member id at that DOS) closes the cascade - then plan begin/end + patient insorder + visit insorder + freq-1.
- Stedi claim status v2 (`claim_status_sweep.status(payer, first, last, dob, member, dos, amount)` returns `(http, json)`) answered Humana 61101 with P0/45 'pending, awaiting benefit determination' + the payer claim number for both duplicate-rejected CCM claims - the fastest way to prove a PA 'duplicate of a previously processed claim' rejection needs no rebill.
"""
open("captured_calls_additions_2026-09-29_1110UTC-7amET-ehpa-cloud.md", "w").write(add_md)
open("captured_calls.md", "a").write("\n\n" + add_md)
# ---- digest
mirror = sys.argv[sys.argv.index("--final") + 1] if "--final" in sys.argv else "(mirror pending)"
digest = """# %s run digest - backend billing run, 7 AM ET 9/29 slot (ehpa cloud)

- Bootstrap: repo ATTACHED (origin/main bfa681b at start; session branch claude/pensive-einstein-nm30ul, work on main, clone symlinked as /home/claude/effinger-billing-backend); net AMD_OK / STEDI_CRED_OK / GitHub reachable; AMD password from Gregg's Gmail thread -> .amd_cred.json, ONE login 11:18Z, no lock; START marker 11:18Z (guard clear: the 0910Z digest ends RUN COMPLETE). Layout from main (676 helpers); pseudonyms (318 names) from 'workspace mirror'; registers (387) from practices/ehpa/registers; needs_facesheet_list rebuilt from nightly/runs needs sections. Missing helpers: era_details_pull.py, columns_inspector2_0908.py (not rewritten; check details pulled with the captured GET directly). State bundle restored: none (Drive newest 2026-09-18_1123UTC older than main). GITHUB INBOX: no unapplied PACKAGE (every manifest APPLIED_/SUPERSEDED_).
- Sources: Working Denials queue 0; Insurance board 0 new drops, 0 rows changed since 08:30Z; both inbox registries list none of the current inbox files - nothing trashed. Pam Gmail: 8 admit emails 9/28-9/29 all worked by earlier runs, nothing newer than 03:21Z. Drive: no new remit / facesheet / census / 835 / Availity file since 09:00Z outside the routine's own files.
- Columns: Charge Review 0 -> 0 | Claim Inspector 25 -> 25 (standing holds, same rows as 0910Z) | Unbilled 31 -> 31 (standing holds, no new 'prior payor' rows) | Exclusions 3 -> 1 (two HUM01 duplicate-claim rejections completed - Humana holds both claims pending since 9/26; FLO99 PDTP0303 hold) | ERA 3 checks $2,797.47 -> 0.
- ERA: Medicare ACH 819872046 auto-posted $2,797.29 (32 claims / 39 lines; $0.18 L6 residual disregarded) then 39 CO-45 corrections WOINS $%.2f (Post button left the contractual on the balance); Medicare NON 350011571: 11 CO-29 lines = resubmissions of paid visits (6 contractual corrections WOINS $%.2f with the 9/9 check numbers, no untimely write-off), 3 CO-109 misrouted lines re-routed (pat17473199 -> BCBS MA; pat17472874 x2 -> UNI20) and freq-1 rebilled 204 x3; UHC W0524004: 5 PR-27 lines already re-routed 9/23-9/24. Both $0 checks dismissed. Manual-posted payments: none. Insurance entered: none (one plan re-opened). Dollars re-sent: $507 (v19455653 $206, v19455322 $160, v19455323 $141). Write-offs: WOINS contractual only, $%.2f. Waiting on William: Berry 2026 $0 balances (board row), the standing inspector/unbilled holds.
- Board: board_updates_%s.json (6 ops: 5 trail appends + berry-priscilla-denials to William's turn) -> board inbox. Denials inbox: nothing queued, no file.
- Calls learned: none new (4 lessons in captured_calls_additions_2026-09-29_1110UTC-7amET-ehpa-cloud.md). Vocabulary entries added: 0.
- Mirror: %s
- Script errors: none.

RUN COMPLETE
""" % (S, wo_a, wo_b, wo_a + wo_b, S, mirror)
os.makedirs("chat_history", exist_ok=True); open("chat_history/%s run digest.md" % S, "w").write(digest)
print("rows", len(rows), "WOINS A %.2f B %.2f; ops %d; register %d" % (wo_a, wo_b, len(ops), len(reg)))
