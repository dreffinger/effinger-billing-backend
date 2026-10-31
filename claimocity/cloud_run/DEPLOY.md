# claimocity-pull v5 — SFTP to a private Cloud Storage bucket (William pastes once; ~3 minutes)

Copies every new Claimocity DFT file from the SFTP /download ROOT (and subfolders) into `gs://ehpa-claimocity-feed-50717` every 30 minutes. Copy-only.

## Why a bucket (2026-10-31)
- v3 (service account writing into a shared Drive folder) failed on every upload: `403 Service Accounts do not have storage quota` — Google no longer
  lets a service account create files in a personal Drive. The September copies had come through a user OAuth token minted while the OAuth app was in
  *Testing*, so that token died after 7 days (copies stopped 9/9).
- v4 (OAuth as William, scope drive.file) needs the OAuth app published, and publishing an external app now requires a homepage and privacy-policy URL on a
  verified domain. Not worth it for an internal job.
- A bucket in the practice's own project has neither problem. The job's service account writes it; the billing routines read it with the read-only key of
  `claimocity-reader@ehpa-project-50717.iam.gserviceaccount.com` (roles/storage.objectViewer on that bucket only), fetched at bootstrap from the Gmail
  thread **"claimocity gcs key"** the way the Stedi key is. Routine side: `scripts/helpers/claimocity_gcs.py` (lists, compares with the register, downloads).

## Steps
1. Cloud Shell (project ehpa-project-50717): paste the whole of `claimocity_v5_paste.txt` (beside this note; also Drive 'Claimocity drop'). It creates the
   bucket (private, uniform access), grants the writer and the reader, deploys the job, runs it once, prints the log and the bucket listing, then prints the
   reader key JSON ONCE and deletes the local copy.
2. Copy the printed JSON into an email to dreffinger@gmail.com with the subject exactly `claimocity gcs key` (the routines search that subject).
3. The routine environment's Network access must allow `oauth2.googleapis.com` and `storage.googleapis.com` (Custom list: add both; Full: nothing to do).
   A blocked run says so in its report ("gcs: BLOCKED ...") instead of failing.
4. The Billing Button (prompt v3, runbook step (a)) and the daily routine (prompt v3) then read the bucket; the first run ingests 10/28 onward
   (10/16–10/27 and the September files are already registered by content and skipped).

Expected log: `bucket ok: gs://... has 0 files already`, `copied /download/2026...hl7` × 18, `done: 18 files on sftp under /download, 18 copied, 0 skipped`.
`Authentication failed` = the SFTP password changed: `gcloud secrets versions add claimocity-sftp-pass --data-file=-`.
Cloud Scheduler still fires the job every 30 minutes (unchanged). Drive 'Claimocity drop' keeps the ADT facesheets and the September copies; nothing moves.
