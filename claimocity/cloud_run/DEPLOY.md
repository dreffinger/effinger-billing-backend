# claimocity-pull v3 — redeploy from Cloud Shell (William pastes; ~2 minutes)

Copies every new Claimocity DFT file from the SFTP /download ROOT (and subfolders) into Drive "Claimocity drop" every 30 minutes.
Copy-only. No user token, no OAuth client secret: the job's service account uploads into the folder it was given Editor rights on (9/18/2026).

```
PROJECT=[name]-50717; REGION=us-east1; SA=claimocity-pull@$PROJECT.iam.gserviceaccount.com
gcloud config set project $PROJECT
mkdir -p ~/claimocity-pipeline && cd ~/claimocity-pipeline
# main.py + requirements.txt = the two files beside this note (repo claimocity/cloud_run/, or Drive 'Claimocity drop' claimocity_v3_paste.txt)
gcloud run jobs deploy claimocity-pull --source . --region $REGION --quiet --service-account $SA \
  --set-env-vars DRIVE_FOLDER_ID=1XskJ8BJAC-YQRLRFBZ9lWuyEJiU1-htI,REMOTE_ROOT=/download \
  --set-secrets SFTP_PASS=claimocity-sftp-pass:latest
gcloud run jobs execute claimocity-pull --region $REGION --wait
# read THAT run's output in order (execution id from the line above):
gcloud logging read 'resource.type="cloud_run_job" AND labels."run.googleapis.com/execution_name"="claimocity-pull-<id>"' --order=asc --project $PROJECT --format="value(textPayload)"
```

Expected on the first run: `copied /download/20261016...hl7` ... for every file that is not yet in Drive (12 backlog files + anything newer),
then `done: N files on sftp under /download, M copied, K skipped`. From then on each 30-minute run copies the day's new file.
If the upload line says `UPLOAD FAILED ... 403` the folder is not shared with the service account: share
https://drive.google.com/drive/folders/1XskJ8BJAC-YQRLRFBZ9lWuyEJiU1-htI with claimocity-pull@[name]-50717.iam.gserviceaccount.com as Editor.
`Authentication failed` = the SFTP password changed: `gcloud secrets versions add claimocity-sftp-pass --data-file=-` with the new one.
Cloud Scheduler already fires the job every 30 minutes (unchanged by this redeploy).
