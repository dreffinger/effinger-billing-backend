# CLAIMOCITY FEED INGEST — routine step `feed` (v1, 2026-10-29)

William 10/28/2026 23:05 ET: "let the claimocity feed just pile up the files there, leave them there and just pull the data we need,
import the charges and be done - no need for Gregg". The practice enters its own charges from the Claimocity DFT^P03 feed; Gregg's
AdvancedMD integration is off and stays off (if it ever re-posts a file, the later copy of each visit is voided - see the end).

The text between the lines is the paragraph that lives in the ehpa Billing Button prompt (steps vocabulary: `feed`, part of `all`,
runs FIRST in "WORK EVERY RUN"). Keep this file and the prompt identical.

---
CLAIMOCITY FEED INGEST (step `feed`, part of `all`; William 10/28/2026: the practice imports its own charges from the Claimocity DFT feed - Gregg's AMD integration is OFF and stays off; the files pile up on Claimocity untouched; Cloud Run job claimocity-pull copies every new /download file into Drive 'Claimocity drop' every 30 min). Runs BEFORE Charge Review, every run, live or dry:
(a) List Drive 'Claimocity drop' (1XskJ8BJAC-YQRLRFBZ9lWuyEJiU1-htI) for `download__*.hl7` (search_files, parentId, title contains 'download__'; page through). Every name that is not in `files` of /home/claude/unbilled/registers/claimocity_ingest.json (restored from main practices/ehpa/registers/ at bootstrap) and is not 0 bytes is NEW. Nothing new -> one line in the report 'Claimocity feed: nothing new (newest download__ <date>)' and, when that newest file is older than 2 days, the flag 'copy job stale - claimocity-pull (claimocity/cloud_run/DEPLOY.md)'. Then go on.
(b) Download each new file with the Google Drive connector (download_file_content -> base64 -> decode to /home/claude/unbilled/inbox/claimocity/<name>; a result above the tool limit lands in the tool-results file - decode its `content` field (tools/bootstrap/restore_from_transcript.py); check the byte count against the listing's fileSize before using a file).
(c) `cd /home/claude/unbilled && python3 claimocity_ingest.py --hl7-dir inbox/claimocity --stamp <run stamp> --live` (a dry run drops --live). It does, in order: parse (feed_parse_dft_1028.py - CR/LF-agnostic), dx cache (claimocity_dx.py: lookupdiagcode codeset=10, dx_cache_feed.json), chart match (registers/claimocity_patient_map.json first - Claimocity PID-3 -> chart - then claimocity_match.py / claimocity_resolve.py: lookuppatient by name+DOB, several same-DOB charts -> the one with the most recent charge), new charts (claimocity_newcharts.py: addpatient with the Claimocity id as additionalmrn + updaterespparty + addinsurance for every IN1 payer in claimocity_in1_to_amd_carrier.txt's addinsurance rows, member id [member id], no group number), charge entry (claimocity_import.py: addvisit + updvisitwithnewcharges + updextrainsinfo admission date on hospital CPTs, modifier 25 on 99489/99497 add-ons; dedupe = every earlier batch register + the chart's live CPT+DOS charges; a DOS after the deceased cache's date of death is never entered), the cascade (claimocity_verify.py: AMD 271 per open plan, deceased guard, Stedi discovery only when nothing is active and never Part D, lead = traditional Medicare unless CMS names the MA plan, Medicaid/LTC never first, Medicaid 271's SMMC MMA plan = the payer, visit insorder), the inspector pass (claimocity_inspector.py) and the report (claimocity_report.py -> feed_digest_<stamp>.md + PHI-light registers/feed_verify_<stamp>.json). Exit 2 = a step failed: read logs/claimocity_<stamp>_<step>.log, put the failing step and its last lines in the report under 'Refused - for William' style, do not patch scripts mid-run; the file register is written only by a live run, so a failed batch is retried whole next run.
(d) Every chart the digest lists under Holds with 'no active plan' -> this run's section of needs_facesheet_list.md (William's facesheets; never invent a plan). A 'date of death' hold = the charge was not entered (or was voided) - say so, nothing else to do.
(e) Mirror with the rest of the run: registers/feed_import_<stamp>.json, feed_newcharts_<stamp>.json, feed_verify_<stamp>.json (PHI-light), feed_inspector_<stamp>.json, feed_fixholds_<stamp>.json, claimocity_ingest.json, claimocity_patient_map.json and dx_cache_feed.json -> practices/ehpa/registers/ on main; feed_digest_<stamp>.md -> Drive chat history with the run digest. feed_parsed_<stamp>.json and feed_match_<stamp>.json carry names and never leave the workspace (both reproducible).
(f) Report line: 'Claimocity feed: N new file(s) (<dates>), M messages, V visits / $X entered, C new charts, H holds (facesheets), D already in AMD'. Charge Review / Claim Inspector then see the new charges like any others (they arrive approved + inspected).
Duplicates: should Gregg's pickup ever post the same files, `FEED_STAMP=<batch> python3 claimocity_dupe_void.py --live` voids the integration's later copy of every visit that batch created (skips anything paid) - William 10/28: accept duplicates and void them.
---

## Why it is safe to run every routine
- Idempotent at three levels: the file register (sha256), every earlier batch's import register (feed patient id + DOS + CPT set,
  including the feed DOS of a visit that was re-dated afterwards), and the chart's live charges (CPT + DOS).
- No new file = two Drive calls and one line. A normal day = one file (20-250 KB), 10-80 messages, 5-15 minutes of tool calls,
  of which the Claude model does only the listing, the download and reading the digest - the rest is the scripts.
- Writes are the same proven shapes as the 10/28 backlog import (569 visits, 0 faults): docs/api_vocabulary.json ids
  chargeentry/addvisit-empty-visit, chargeentry/updvisitwithnewcharges-new-charges, demographics/addpatient-create-chart,
  demographics/updaterespparty-name, demographics/addinsurance-add-a-plan-no-group-number.

## Cheaper model
The step is scripted end to end; the model's judgment is only needed for reading the digest and routing holds. It can run inside
the Billing Button (any firing, any mode) or as its own scheduled task on a smaller model with this prompt plus the Button's STEP 0
bootstrap (repo clone, helpers, AMD credential file, deceased cache). William picks the model when creating that task in the UI.
