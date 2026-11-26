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
2. Copy the printed JSON into an email to dreffinger@gmail.com with the subject exactly `claimocity gcs key` (the routines search that subject and take the newest message). The whole `{ ... }` is best; the 10/30 mail carried only the private key's base64 lines and `claimocity_gcs.py --install-key` accepts that too (client_email and project are fixed; Google takes the JWT without a private_key_id).
3. The routine environment's Network access must allow `oauth2.googleapis.com` and `storage.googleapis.com` (Custom list: add both; Full: nothing to do).
   A blocked run says so in its report ("gcs: BLOCKED ...") instead of failing.
4. The Billing Button (prompt v3, runbook step (a)) and the daily routine (prompt v3) then read the bucket; the first run ingests 10/28 onward
   (10/16–10/27 and the September files are already registered by content and skipped).

Expected log: `bucket ok: gs://... has 0 files already`, `copied /download/2026...hl7` × 18, `done: 18 files on sftp under /download, 18 copied, 0 skipped`.
`Authentication failed` = the SFTP password changed: `gcloud secrets versions add claimocity-sftp-pass --data-file=-`.
Cloud Scheduler still fires the job every 30 minutes (unchanged). Drive 'Claimocity drop' keeps the ADT facesheets and the September copies; nothing moves.

THE COPY JOB NEVER REPLACES A FILE THE BUCKET HOLDS (found 11/25/2026): main.py skips every SFTP name the bucket already has, whatever its size. A file that was copied while Claimocity was still writing it, or that Claimocity sends again under its own name, therefore reaches the bucket only after a person deletes the object download__<file name>. The feed's download step reads a registered file again when the bucket's copy has another size than the one that was read, and the ingest keeps a file unregistered while a message of it could not be read - both wait for the bucket's copy to change. To let the job replace such a file by itself, three lines of main.py - and the same three in the copy of main.py inside claimocity_v5_paste.txt, which is the code the paste deploys - would compare sizes instead of names: `have = {b.name: b.size for b in bucket.list_blobs()}`; `if entry.st_size == 0 or have.get(name) == entry.st_size:` (skip); and after the upload `have[name] = entry.st_size`. This change is NOT made and was not tried; it is written down for the person who decides to make it.
