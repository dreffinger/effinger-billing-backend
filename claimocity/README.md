# Claimocity hospital charge feed — how it works, how it broke, how it was fixed (2026-09-18)

## Two separate paths, do not confuse them
1. **Charges into AdvancedMD.** Encounters William enters in Claimocity become HL7 DFT^P03 files on Claimocity's SFTP
   site (sftp.claimocity.io, account `kykzfgie`, folder `/download`). The pickup that feeds AdvancedMD (the 2022
   Hendrickson Group integration) takes each file and clears it. This path never stopped: the 3 PM ET run on 9/17 found
   56 new HCA hospital visits dated 9/14–9/16 in Claim Inspector, all from the feed. Posting lags 1–3 days and arrives in
   daytime batches. Visits land on the patient's MAIN referral plan (VA stays need a resave onto the stay's plan).
2. **Our copy of the files.** Cloud Run Job `claimocity-pull` (GCP project `[name]-50717`, region `us-east1`,
   service account `claimocity-pull@[name]-50717.iam.gserviceaccount.com`) runs every 30 minutes, lists the whole
   SFTP account and copies every non-empty file it has not seen into the Drive folder **Claimocity drop**
   (`1XskJ8BJAC-YQRLRFBZ9lWuyEJiU1-htI`, under billing agent project files). File names flatten the SFTP path:
   `/download/2026MMDD<hash>.hl7` -> `download__2026MMDD<hash>.hl7`. One file per day arrives about **07:30 UTC
   (3:30 AM ET)**, 5–65 KB. The job catches a file only if it runs before the AMD pickup clears it, which it does at
   that hour. The copies exist for `claimocity_in1.py` (insurance IN1 vs AMD diff, read-only) and for reading; no
   routine consumes them automatically yet, and no run digest has ever logged pulling one.

## The 9/10–9/17 outage (root cause, proven from the job log)
- Symptom: no new file in the Drive folder after `download__20260909...` (07:30Z 9/9). Every execution from 9/10 on
  failed with `google.auth.exceptions.RefreshError: invalid_grant: Token has been expired or revoked` and
  `Container called exit(1)`.
- Cause: the deployed script logged in to Drive with a copy of William's personal Google refresh token, stored in the
  Secret Manager secret `drive-user-creds` (env var `DRIVE_USER_CREDS`). That token was revoked around 9/10.
- NOT the cause: the Claimocity "Password reset" email of 9/9 10:47 PM ET (admin@claimocity.com) was a coincidence —
  it is the portal/app login for William Effinger, not the SFTP account, and the SFTP login still works.
- Fix (9/18, execution `claimocity-pull-j2hvb` succeeded): redeployed `cloud_run/main.py` here, which uses the job's own
  service account (`google.auth.default(scopes=[drive])`), after sharing the Drive folder with that service account as
  **Editor**. Env: `DRIVE_FOLDER_ID` + secret `SFTP_PASS=claimocity-sftp-pass:latest`. The old `DRIVE_USER_CREDS`
  binding is unused and harmless. The old code is `~/claimocity-pipeline/main.py.bak-user-creds` in William's Cloud Shell.
- First run after the fix: `drive folder ok: 12 files already there` / `done: 0 copied, 4 skipped` — the SFTP site had
  nothing newer than 9/9 because the AMD pickup had already cleared those days. The 9/10–9/17 copies are not
  recoverable from SFTP (Claimocity can resend, as they did in June 2023, but AMD already has the charges).
- Never run the 9/2 redeploy paste (`claimocity_redeploy_paste.txt` in the Drive folder) again: it restores the
  expired personal-token version. `claimocity_gcs_paste.txt` is the alternative that writes to the bucket
  `ehpa-claimocity-drop` with the service account (unused; the read-only key `claimocity-reader-key.json` in the Drive
  folder was made for reading that bucket).

## Cloud Shell one-liners (William pastes; the Claude sessions cannot reach GCP)
```
# what is deployed (env vars, secrets, service account)
gcloud run jobs describe claimocity-pull --region us-east1 --project [name]-50717 --format="yaml(spec.template.spec.template.spec.containers[0].env,spec.template.spec.template.spec.serviceAccountName)"
# run it now and read THAT run's output in order (gcloud logging read lists newest first unless --order=asc)
gcloud run jobs execute claimocity-pull --region us-east1 --project [name]-50717 --wait
gcloud logging read 'resource.type="cloud_run_job" AND labels."run.googleapis.com/execution_name"="claimocity-pull-<id>"' --order=asc --project [name]-50717 --format="value(textPayload)"
# redeploy from this folder's code (cd ~/claimocity-pipeline first, with main.py / requirements.txt / Procfile in place)
gcloud run jobs deploy claimocity-pull --source . --region us-east1 --project [name]-50717 --quiet --set-env-vars DRIVE_FOLDER_ID=1XskJ8BJAC-YQRLRFBZ9lWuyEJiU1-htI --set-secrets SFTP_PASS=claimocity-sftp-pass:latest
```
Reading a run's log: `done: 0 copied, N skipped` = both logins fine, nothing new at Claimocity. `copied ...` lines =
files landed. `UPLOAD FAILED ... 403` = Drive refused the service account (switch to the bucket paste).
`Authentication failed` (paramiko) = SFTP password changed -> new version of secret `claimocity-sftp-pass`.
The audit entry "Execution ... has failed to complete, 0/1 tasks were a success" carries no reason; the reason is in
the stderr lines of that execution.

## Health check (what "is the feed working" means)
- Drive folder has a `download__<today or yesterday>...hl7` file dated ~07:30Z -> copy job healthy.
- Claim Inspector shows new hospital visits "Hospitalization From Date empty" within 1–3 days of DOS -> AMD path healthy.
- Both can be true while the other is false; check both. Proposed for prompt v8: the 9 AM ET run reports "Claimocity
  drop: newest file <date>" and flags when the newest file is older than 2 days.
