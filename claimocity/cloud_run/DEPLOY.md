# claimocity-pull v4 — redeploy from Cloud Shell (William pastes; two pastes, ~5 minutes)

Copies every new Claimocity DFT file from the SFTP /download ROOT (and subfolders) into Drive every 30 minutes. Copy-only.

## Why v4 (2026-10-31)
The v3 run (`claimocity-pull-6n4g5`, 10/30 22:12 ET) reached the SFTP (18 files) but every upload answered
`403 Service Accounts do not have storage quota` — Google no longer lets a service account create files in a personal Drive, shared folder or not.
So the job now uploads AS WILLIAM through his OAuth refresh token (Secret Manager `drive-user-creds`, scope **drive.file** — non-sensitive, the
app only sees files it created) into a folder the job creates itself: **"Claimocity feed drop"** in My Drive (drive.file cannot write into a folder
the app did not create). The September copies stopped on 9/9 for the same family of reasons: the first token was minted while the OAuth app was in
*Testing* status, and testing-mode refresh tokens expire after 7 days — publish the consent screen first.

## Steps
0. Console > APIs & Services > OAuth consent screen (ehpa-project-50717): if Publishing status says *Testing*, **Publish app**. One click, once.
1. Cloud Shell: paste **PASTE 1** of `claimocity_v4_paste.txt` (Drive 'Claimocity drop'). It writes main.py, requirements.txt, finish.sh and prints a consent link.
2. Open the link in a browser, choose dreffinger@gmail.com, Allow (Advanced > Go to … if Google warns the app is unverified). The browser lands on an
   error page `http://localhost:8765/?code=4/0A…&scope=…` — copy the `code=` value.
3. Cloud Shell: `bash ~/claimocity-pipeline/finish.sh '<the code>'` — exchanges the code for a refresh token, adds it as a new version of
   `drive-user-creds`, deploys the job with `FOLDER_NAME=Claimocity feed drop` + secrets SFTP_PASS / DRIVE_USER_CREDS, runs it once and prints the log.
4. Read the log: `drive folder CREATED: Claimocity feed drop (id <id>)`, `copied /download/2026…hl7` lines, `done: 18 files … 18 copied`.
   **Send Claude the folder id** — the feed step (runbook nightly/claimocity_feed_step.md (a), the daily routine A4) switches to that folder.
   The old 'Claimocity drop' folder keeps the ADT facesheets and the September copies; nothing moves.

Cloud Scheduler still fires the job every 30 minutes (unchanged). `Authentication failed` in a later log = the SFTP password changed:
`gcloud secrets versions add claimocity-sftp-pass --data-file=-`. `invalid_grant` = the refresh token was revoked/expired: repeat steps 1–3.
