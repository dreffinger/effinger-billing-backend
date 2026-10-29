# CLAIMOCITY FEED INGEST — routine step `feed` (v2, 2026-10-29)

William 10/28/2026 23:05 ET: "let the claimocity feed just pile up the files there, leave them there and just pull the data we need,
import the charges and be done - no need for Gregg". The practice enters its own charges from the Claimocity DFT^P03 feed; Gregg's
AdvancedMD integration is off and stays off (if it ever re-posts a file, the later copy of each visit is voided - see the end).

Where this text runs:
- the ehpa Billing Button (scheduled task trig_01S771Si8VJ8DvcwgHMHGYB5, prompt nightly/billing_button_prompt_v2_2026-10-29.txt):
  its FEED paragraph POINTS HERE - the stored prompt sits 10 bytes under the server's 65,536-byte limit, so the step's text lives in
  this runbook (like docs/MIRROR.md and docs/APPROVALS_LOOP.md) and the prompt names only the file and the one command. The Button
  reads this file from main after its STEP 0 bootstrap (GitHub-less: the copy in Drive "billing agent project files"). Step `feed`
  runs on every firing, live or dry, before Charge Review.
- the daily task "Claimocity feed ingest (daily)" (nightly/claimocity_feed_daily_prompt_v1.txt, a cheaper model; William creates
  it in the scheduled-tasks UI - the agent's create call was refused by the environment 10/29): the same paragraph, inline, with
  its own cheap "anything new?" check first.
The paragraph between the --- lines is the step. Keep it and the daily prompt's (c)-(f) saying the same thing.

Stamps and chart numbers (10/29): claimocity_ingest.py accepts the routines' stamp form 2026-10-29T0121Z as well as 20261029T0121Z
(digits/T/Z are kept, so every feed_*_<stamp>.json is named 20261029T0121Z either way); new charts get the series F<yymmdd>-NN,
first FREE number (claimocity_newcharts probes lookuppatient code= before addpatient), so a Button press and the daily task on
one day never collide, and the 10/28 backlog's F1028-NN series stays untouched.

---
CLAIMOCITY FEED INGEST (step `feed`, part of `all`; William 10/28/2026: the practice imports its own charges from the Claimocity DFT feed - Gregg's AMD integration is OFF and stays off; the files pile up on Claimocity untouched; Cloud Run job claimocity-pull copies every new /download file into Drive 'Claimocity drop' every 30 min). Runs BEFORE Charge Review, every run, live or dry:
(a) List Drive 'Claimocity drop' (1XskJ8BJAC-YQRLRFBZ9lWuyEJiU1-htI) for `download__*.hl7` (search_files, parentId, title contains 'download__'; page through). Every file whose SFTP name (the Drive name with its leading `download__` removed - the register keys the SFTP names) is not in `files` of /home/claude/unbilled/registers/claimocity_ingest.json (restored from main practices/ehpa/registers/ at bootstrap) and that is not 0 bytes is NEW (the script also skips a file whose content is already registered under another name). Nothing new -> one line in the report 'Claimocity feed: nothing new (newest download__ <date>)' and, when that newest file is older than 2 days, the flag 'copy job stale - claimocity-pull (claimocity/cloud_run/DEPLOY.md)'. Then go on.
(b) Download each new file with the Google Drive connector (download_file_content -> base64 -> decode to /home/claude/unbilled/inbox/claimocity/<name>; a result above the tool limit lands in the tool-results file - decode its `content` field (tools/bootstrap/restore_from_transcript.py); check the byte count against the listing's fileSize before using a file).
(c) `cd /home/claude/unbilled && python3 claimocity_ingest.py --hl7-dir inbox/claimocity --stamp <run stamp> --live` (a dry run drops --live). It does, in order: parse (feed_parse_dft_1028.py - CR/LF-agnostic), dx cache (claimocity_dx.py: lookupdiagcode codeset=10, dx_cache_feed.json), chart match (registers/claimocity_patient_map.json first - Claimocity PID-3 -> chart - then claimocity_match.py / claimocity_resolve.py: lookuppatient by name+DOB, several same-DOB charts -> the one with the most recent charge), new charts (claimocity_newcharts.py: addpatient with the Claimocity id as additionalmrn and chart number F<yymmdd>-NN first free + updaterespparty + addinsurance for every IN1 payer in claimocity_in1_to_amd_carrier.txt's addinsurance rows, member id IN1-49, no group number), charge entry (claimocity_import.py: addvisit + updvisitwithnewcharges + updextrainsinfo admission date on hospital CPTs, modifier 25 on 99489/99497 add-ons; dedupe = every earlier batch register + the chart's live CPT+DOS charges; a DOS after the deceased cache's date of death is never entered), the cascade (claimocity_verify.py: AMD 271 per open plan, deceased guard, Stedi discovery only when nothing is active and never Part D, lead = traditional Medicare unless CMS names the MA plan, Medicaid/LTC never first, Medicaid 271's SMMC MMA plan = the payer, visit insorder), the inspector pass (claimocity_inspector.py) and the report (claimocity_report.py -> feed_digest_<stamp>.md + PHI-light registers/feed_verify_<stamp>.json). Exit 2 = a step failed: read logs/claimocity_<stamp>_<step>.log, put the failing step and its last lines in the report under 'Refused - for William' style, do not patch scripts mid-run; the file register is written only by a live run, so a failed batch is retried whole next run.
(d) Every chart the digest lists under Holds with 'no active plan' -> this run's section of needs_facesheet_list.md (William's facesheets; never invent a plan). A 'date of death' hold = the charge was not entered (or was voided) - say so, nothing else to do.
(e) Mirror with the rest of the run: registers/feed_import_<stamp>.json, feed_newcharts_<stamp>.json, feed_verify_<stamp>.json (PHI-light), feed_inspector_<stamp>.json, feed_fixholds_<stamp>.json, claimocity_ingest.json, claimocity_patient_map.json and dx_cache_feed.json -> practices/ehpa/registers/ on main; then `cd /home/claude/effinger-billing-backend && python3 tools/feed/feed_monitor.py` (reads those registers, writes reports/feed/feed_monitor.json - the data behind the Claimocity Feed Monitoring page https://claude.ai/artifact/QrLJpUcpFv3cFRB9xHfLyk; chart ids, dates, codes and dollars only) and commit that file with the registers; feed_digest_<stamp>.md -> Drive chat history with the run digest. feed_parsed_<stamp>.json and feed_match_<stamp>.json carry names and never leave the workspace (both reproducible).
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
The step is scripted end to end; the model's judgment is only needed for the listing, the download, reading the digest and routing
holds. It runs inside the Billing Button (any firing, any mode) and, once William creates that task, as its own daily scheduled
task on claude-sonnet-5-5 (prompt = nightly/claimocity_feed_daily_prompt_v1.txt, 8:34 PM ET daily, same environment as the Button): phase A costs a handful of tool calls and stops when Drive holds nothing new; phase B
(the bootstrap, the ingest, the mirror) runs only when a new download__ file exists. The 2-hourly backend run can carry the same
paragraph too if William pastes it into that task's prompt (the agent cannot edit that task); it is idempotent, so overlap is safe.
