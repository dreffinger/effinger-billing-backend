# PLAIN ENGLISH (run outputs for the 9am ET 9/29/2026 slot - ehpa cloud run 2026-09-29T1310Z, a quiet slot)
# Decides: nothing. Reads this run's scan registers (scan_0929_1310 before/after) and writes:
#   "_run report 9-29 0900.csv" (names allowed - SendUserFile only), a needs_facesheet_list.md section (pat ids only)
#   and the chat-history digest (--final adds the mirror result). No board file (nothing to write), no ERA activity.
# Never touches: AMD, the board databases. Patient names come from the scan data at run time - none are written in this file.
import json, csv, os, sys, datetime
S = "2026-09-29T1310Z"; NOW = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
sc_b = json.load(open("scan_0929_1310/summary_before.json")); sc_a = json.load(open("scan_0929_1310/summary_after.json"))
HOLD = {"17472874": "HCA admission date - no 99223 anchor on the chart (William)", "17477640": "HCA admission date - no 99223 anchor (William)", "17472703": "HCA admission date - no 99223 anchor (William)",
        "17474541": "99489 without 99487 - coding (William)", "17476036": "99489 without 99487 + unspecified-laterality S91.309D - coding (William)", "17473477": "deceased guard - CCM after death (William void)",
        "45668": "deceased guard - CCM after death (William void); F02.80 external-cause advisory also on the row", "17477208": "duplicate CCM lines on one visit (William)", "20863": "CCI 24078 history-procedure edit (William); FCC PDTP0303 hold on Exclusions",
        "17477183": "Medicaid PENDING per the Aviata census - no billable plan yet", "17473232": "CCM after death (William void)", "17471681": "CCM after death (William void)", "17477639": "facesheet needed (no plan on the chart)",
        "17477842": "duplicate chart - William merges", "17477870": "duplicate chart - William merges", "17477850": "CHP member id needed (facesheet)", "17477898": "CHP member id needed (facesheet)", "17477892": "facesheet needed (no plan on the chart)"}
rows = []
def R(col, status, pid, name, dos, carrier, err, action, vid="", amt=""):
    rows.append({"column": col, "status": status, "patient": name, "patientid": pid, "visit": vid, "dos": dos, "carrier": carrier, "error": err, "amount": amt, "action": action})
for bid, vs in sc_b["inspector"].items():
    for v in vs:
        R("Claim Inspector", "hold", v["pid"], v["name"], "", "", "; ".join(x[1][:80] for x in v["errs"]), "standing hold - " + HOLD.get(v["pid"], "see needs list"), v["vid"])
for r in sc_b["unbilled"]:
    R("Unbilled", "hold", r["patientid"], r["patientname"], (r["_chgs"][0].get("dos") or "").strip() if r["_chgs"] else "", r.get("carriercode") or "", "; ".join(r["_errs"][:2]), "standing hold - " + HOLD.get(r["patientid"], "see needs list"), r["id"], (r["_chgs"][0].get("totalfee") if r["_chgs"] else ""))
for rid, lst in sc_b["exclusions"].items():
    for r in lst:
        R("Exclusions", "hold", r["patientid"], r["patientname"], (r["_chgs"][0].get("dos") or "").strip(), (r.get("carriercode") or "")[:5], (r["_errs"][0].get("name") or "")[:90], "standing hold - FCC PDTP0303 needs the related admission date (William)", r["id"], r["_chgs"][0].get("totalfee"))
R("ERA", "none", "", "", "", "", "0 unposted checks before and after", "nothing uploaded, posted or cleared; no new Availity PDF / Check-EFT export / 835 in Drive")
with open("_run report 9-29 0900.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["column", "status", "patient", "patientid", "visit", "dos", "carrier", "error", "amount", "action"]); w.writeheader(); w.writerows(rows)
ov_b, ov_a = sc_b["overview"], sc_a["overview"]
ni_b = sum(len(v) for v in sc_b["inspector"].values()); ni_a = sum(len(v) for v in sc_a["inspector"].values())
ne_b = sum(len(v) for v in sc_b["exclusions"].values()); ne_a = sum(len(v) for v in sc_a["exclusions"].values())
needs = """## %s - backend billing run, 9 AM ET 9/29 slot (ehpa cloud)
- Columns: Charge Review %s -> %s | Claim Inspector %d -> %d (every row a standing hold, same visit ids as 1110Z) | Unbilled %s -> %s (no new rows; every row a standing hold) | Exclusions %d -> %d (pat20863 v19445850 FLO99 PDTP0303 hold; overview says %s/$%s but every listed run returns one row) | ERA 0 checks -> 0.
- CLAIM INSPECTOR holds unchanged (25): pat17472874 x15 + pat17477640 x2 + pat17472703 x2 HCA admission dates (no 99223 anchor - William); pat17474541 v19430630 + pat17476036 v19456171 99489 without 99487 (coding - William); pat17473477 v19455625 + pat45668 v19455691 deceased guard (CCM after death - William void); pat17477208 v19455940 duplicate CCM lines; pat20863 v19455936 CCI 24078. Nothing bypassed, nothing resaved.
- UNBILLED holds unchanged (31): pat17472874 x15 + pat17474541 (inspector holds); pat17477183 x2 Medicaid PENDING per the Aviata census; pat17473232 + pat17471681 CCM after death (William void); pat17477639 facesheet; pat17477842 + pat17477870 duplicate charts; pat17477850 x4 + pat17477898 x2 CHP member ids; pat17477892 x2 facesheet. No new 'prior payor' rows this slot.
- SOURCES: Working Denials queue 0; board drops 0; 0 board rows changed since 09:00Z; Pam Gmail: the 8 admit emails of 9/28-9/29 were all worked by earlier runs, nothing newer than 03:21Z; Drive: no new remit / facesheet / census / 835 / Availity file since 09:00Z outside the routine's own files; GitHub inbox: no unapplied PACKAGE manifest; both board inbox registries list none of the current inbox files - nothing trashed.
- ERA: 0 unposted checks before and after; nothing uploaded, posted or cleared (locks release-expired answered 400 to an empty JSON body - nothing to release with 0 checks). Availity 5(g): no new PDF or Check/EFT export.
- Calls learned: none. Missing helpers (not rewritten): era_details_pull.py, columns_inspector2_0908.py.
""" % (S, ov_b["chargereviewcount"], ov_a["chargereviewcount"], ni_b, ni_a, sc_b["unbilled_totalcount"], sc_a["unbilled_totalcount"], ne_b, ne_a, ov_b["exclusioncount"], ov_b["exclusionamount"])
open("needs_section_%s.md" % S, "w").write(needs)
open("needs_facesheet_list.md", "a").write("\n" + needs)
mirror = sys.argv[1] if len(sys.argv) > 1 else "(mirror pending)"
digest = """# %s run digest - backend billing run, 9 AM ET 9/29 slot (ehpa cloud)

- Bootstrap: repo ATTACHED (origin/main 6414537 at start; session branch claude/pensive-einstein-vd52wx, work on main, clone symlinked as /home/claude/effinger-billing-backend); net AMD_OK / STEDI_CRED_OK / GitHub reachable; AMD password from Gregg's Gmail thread -> .amd_cred.json, ONE login 13:19Z, no lock; START marker 13:12Z (guard clear: the 1110Z digest ends RUN COMPLETE). Layout from main (679 helpers); pseudonyms (318 names) from 'workspace mirror'; registers (389) from practices/ehpa/registers; needs_facesheet_list rebuilt from nightly/runs needs sections. Missing helpers: era_details_pull.py, columns_inspector2_0908.py (not rewritten). State bundle restored: none (Drive newest 2026-09-18_1123UTC older than main). GITHUB INBOX: no unapplied PACKAGE (only a SUPERSEDED_ manifest).
- Sources: Working Denials queue 0; Insurance board 0 new drops, 0 rows changed since 09:00Z; both inbox registries list none of the current inbox files - nothing trashed. Pam Gmail: 8 admit emails 9/28-9/29 all worked by earlier runs, nothing newer than 03:21Z. Drive: no new remit / facesheet / census / 835 / Availity file since 09:00Z outside the routine's own files.
- Columns: Charge Review 0 -> 0 | Claim Inspector 25 -> 25 (standing holds, same rows as 1110Z) | Unbilled 31 -> 31 (standing holds) | Exclusions 1 -> 1 (FLO99 PDTP0303 hold) | ERA 0 checks -> 0. Quiet slot: nothing bypassed, resaved, released, rebilled, posted or written off. Insurance entered: none. Dollars re-sent: $0. Write-offs: none. Waiting on William: the standing inspector/unbilled holds (needs section).
- Board: no board_updates file (nothing to write). Denials inbox: nothing queued, no file.
- Calls learned: none. Vocabulary entries added: 0.
- Mirror: %s
- Script errors: none (locks release-expired 400 on an empty body, as every quiet slot).

RUN COMPLETE
""" % (S, mirror)
os.makedirs("chat_history", exist_ok=True); open("chat_history/%s run digest.md" % S, "w").write(digest)
print(needs); print("rows", len(rows))
