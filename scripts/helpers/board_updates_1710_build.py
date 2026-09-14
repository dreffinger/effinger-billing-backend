# PLAIN ENGLISH (board update file builder, 1 PM ET 9/14/2026 slot - ehpa cloud run 2026-09-14T1710Z)
# Decides: nothing on AMD. Writes board_updates_2026-09-14T1710Z.json (Insurance Refresh Board inbox ops):
#   - cruver-joyce-ann-denials: records the 5/14/2024 99308 line cleared this run (Sunshine 'MBR NOT VALID AT DOS'
#     payer rejection on run 1700186 was a contractual residual - Humana MA paid the allowed in full 6/2024; $45.66 WOINS, exclusion completed).
#   - bull-thomas-17477723 / aet12-carrier-cpid / era-manual-post-0912: this slot's check lines (idempotent by src+when).
# Never touches: the board directly (no write_db) - the board applies this file when William opens it.
import json, sys, time
stamp = "2026-09-14T1710Z"; now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
era_line = sys.argv[1] if len(sys.argv) > 1 else "ERA step ran - see run report"
src = "1pm ET 9/14 columns run (ehpa cloud)"
ops = [
 {"op": "upsert", "collection": "items", "id": "cruver-joyce-ann-denials",
  "append": {"checks": [{"ok": "ok", "result": "Exclusion run 1700186 visit 19383306 (99308 5/14/2024, $107): Sunshine answered 'PA 09 - MBR NOT VALID AT DOS' on the 9/11/2026 secondary send. Live charge: Humana MA (HUM01, her PPO 2/2023-2/2025 per the CMS record) paid the full allowed $61.34 on 6/20/2024 (check 133765496240601); the $45.66 left was the unadjusted contractual difference, not a secondary balance. WOINS $45.66 posted with a dated note, balance $0, exclusion completed. Nothing owed by Sunshine or the patient (QMB).", "src": src, "when": "9/14"}],
             "notes": [{"who": "Claude", "at": now, "text": "1pm ET 9/14 run: one Sunshine payer rejection on her 5/14/2024 99308 was a contractual leftover from Humana's 2024 payment - written off WOINS ($45.66) and the exclusion completed. The April 2026 denials on this row are unchanged."}]}},
 {"op": "upsert", "collection": "items", "id": "bull-thomas-17477723",
  "append": {"checks": [{"ok": "no", "result": "chart still has zero insurance plans (getdemographic 17:14 UTC); no facesheet in hca/tmh/PCC/Claimocity folders or the parent since 9/14 15:27 UTC, Pam Gmail sweep newer_than:2d = 0, no board drop; visits 19454443/19454465 ($421) stay in Unbilled", "src": src, "when": "9/14"}]}},
 {"op": "upsert", "collection": "items", "id": "aet12-carrier-cpid",
  "append": {"checks": [{"ok": "na", "result": "Exclusions column 1 -> 0 (the one row was Cruver/Sunshine, not AET12); still no claim run since 1700188 (9/12 21:09 UTC, 88 runs) - the 59 AET12 claims re-sent 04:20 UTC under the Standard Professional profile are decided by the next claim run", "src": src, "when": "9/14"}]}},
 {"op": "upsert", "collection": "items", "id": "era-manual-post-0912",
  "append": {"checks": [{"ok": "na", "result": era_line, "src": src + " - ERA step 5", "when": "9/14"}]}},
]
doc = {"schema": "irb-board-updates/1", "source": "backend billing run %s" % stamp, "created": now, "ops": ops}
json.dump(doc, open("board_updates_%s.json" % stamp, "w"), indent=1)
print("wrote board_updates_%s.json with %d ops" % (stamp, len(ops)))
