# PLAIN ENGLISH (board update file builder, 11 AM ET 9/14/2026 slot - ehpa cloud run 2026-09-14T1510Z)
# Decides: nothing on AMD. Writes board_updates_2026-09-14T1510Z.json (Insurance Refresh Board inbox ops):
#   - coalson-yvonne-17474210: answers William's 9/14 03:58Z note ("put the numbers here to paste into availity")
#     with the Availity claim-status block for the 6 open Humana charges (read live from gettxhistory this run).
#   - bull-thomas-17477723 / aet12-carrier-cpid / era-manual-post-0912: this slot's check lines (idempotent by src+when).
# Never touches: the board directly (no write_db) - the board applies this file when William opens it.
import json, sys, time
stamp = "2026-09-14T1510Z"; now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
era_line = sys.argv[1] if len(sys.argv) > 1 else "ERA step ran - see run report"
src = "11am ET 9/14 columns run (ehpa cloud)"
availity = ("AVAILITY CLAIM STATUS - COALSON, YVONNE (DOB 06/29/1949), payer HUMANA (HumanaChoice MA, AMD carrier HUM01, Payor ID 2449), member id H67022459, "
            "billing provider EFFINGER HEALTH PA NPI 1629515325 TIN 81-4723941, rendering William L. Effinger DO NPI 1225327380, place of service 21 HCA Florida Capital Hospital. "
            "Open lines (all last billed 09/10/2026 freq-1, paid $0, insurance balance = billed): "
            "09/29/2025 99223 $310.00 (visit 19418455); 09/30/2025 99232 $111.00 (19418452); 10/01/2025 99232 $111.00 (19418568); "
            "10/02/2025 99232 $111.00 (19418654); 10/03/2025 99232 $111.00 (19418727); 10/04/2025 99233 $160.00 (19418746). Total $914.00. "
            "The Sunday 277 sweep saw 9/29 and 10/4 FINALIZED $0 ($470); the other four returned no status. Stedi HUM01 eligibility was ACTIVE on every DOS, "
            "so the $0 is a claim-content decision - look for the remit reason (timely filing on the 9/10/2026 resubmission of Sept-2025 dates is the likely one; duplicate or auth next).")
ops = [
 {"op": "upsert", "collection": "items", "id": "coalson-yvonne-17474210",
  "set": {"need": "WILLIAM: Availity block posted below (9/14 11am ET run) - paste it into Availity claim status for HUM01 and put the denial reason on this row; "
                  "Stedi says eligibility was ACTIVE on every DOS, so the $0 finalizations are claim-content (timely filing on the 9/10/2026 resubmission of Sept-Oct 2025 dates is the likely reason). "
                  "Nothing is rebilled until the reason is known."},
  "append": {"api": [{"src": "AMD gettxhistory - open HUM01 lines for the Availity lookup", "at": now, "text": availity}],
             "notes": [{"who": "Claude", "at": now, "text": "Per your 03:58Z note: the Availity numbers are in the blue box (member id, NPIs, TIN, every DOS/CPT/$ and visit id). All six Sept-Oct 2025 hospital lines are open at the billed amount, last sent 9/10/2026 freq-1. Post the Humana reason here and the next run acts (appeal, correct, or documented write-off)."}],
             "checks": [{"ok": "ok", "result": "6 open HUM01 charges $914 (9/29-10/4/2025), all billed 9/10/2026, paid $0; Availity block written to the row", "src": src, "when": "9/14"}]}},
 {"op": "upsert", "collection": "items", "id": "bull-thomas-17477723",
  "append": {"checks": [{"ok": "no", "result": "chart still has zero insurance plans (getdemographic 15:15 UTC); no facesheet in hca/tmh/PCC/Claimocity folders or the parent since 9/14 04:49 UTC, Pam Gmail sweep newer_than:2d = 0, no board drop; visits 19454443/19454465 ($421) stay in Unbilled", "src": src, "when": "9/14"}]}},
 {"op": "upsert", "collection": "items", "id": "aet12-carrier-cpid",
  "append": {"checks": [{"ok": "na", "result": "Exclusions 0 rows; still no claim run since 1700188 (9/12 21:09 UTC) - the 59 AET12 claims re-sent 04:20 UTC under the Standard Professional profile are decided by the next claim run", "src": src, "when": "9/14"}]}},
 {"op": "upsert", "collection": "items", "id": "era-manual-post-0912",
  "append": {"checks": [{"ok": "na", "result": era_line, "src": src + " - ERA step 5", "when": "9/14"}]}},
]
doc = {"schema": "irb-board-updates/1", "source": "backend billing run %s" % stamp, "created": now, "ops": ops}
json.dump(doc, open("board_updates_%s.json" % stamp, "w"), indent=1)
print("wrote board_updates_%s.json with %d ops" % (stamp, len(ops)))
