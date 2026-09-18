# PLAIN ENGLISH (Claimocity SFTP -> Drive copy job)
# Decides: nothing. Copies every new file on Claimocity's SFTP site into the Drive folder "Claimocity drop".
# Rules it uses: skips empty files and files already in the folder; never deletes or moves anything at Claimocity.
# Never touches: AMD, the SFTP site (read-only), any existing Drive file.
# Deployed 2026-09-18 as the Cloud Run Job `claimocity-pull` (project [name]-50717, us-east1), every 30 min.
# Logs in to Drive as the job's own service account (the folder is shared with it as Editor) - nothing expires.
# The previous version logged in with a copy of William's personal Google token (secret drive-user-creds) and died
# on 2026-09-10 when that token was revoked ("invalid_grant: Token has been expired or revoked").
"""Claimocity SFTP -> Google Drive pull. Cloud Run Job, every 30 min. Copy-only.
Logs in to Drive as the job's own service account (folder shared with it), so nothing expires.
SFTP path /download/x.hl7 is stored in Drive as download__x.hl7; empty files and files already
in the folder are skipped."""
import io, os, stat
import paramiko
from google.auth import default
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

SFTP_HOST, SFTP_PORT, SFTP_USER, REMOTE_ROOT = "sftp.claimocity.io", 22, "kykzfgie", "/"
FOLDER_ID = os.environ["DRIVE_FOLDER_ID"]          # 1XskJ8BJAC-YQRLRFBZ9lWuyEJiU1-htI = "Claimocity drop"
SFTP_PASS = os.environ["SFTP_PASS"]                # Secret Manager: claimocity-sftp-pass

def drive_client():
    creds, _ = default(scopes=["https://www.googleapis.com/auth/drive"])
    return build("drive", "v3", credentials=creds, cache_discovery=False)

def existing_names(drive):
    names, token = set(), None
    while True:
        r = drive.files().list(q=f"'{FOLDER_ID}' in parents and trashed=false",
                               fields="nextPageToken,files(name)", pageToken=token, pageSize=1000).execute()
        names |= {f["name"] for f in r.get("files", [])}
        token = r.get("nextPageToken")
        if not token:
            return names

def main():
    drive = drive_client()
    have = existing_names(drive)
    print(f"drive folder ok: {len(have)} files already there")
    t = paramiko.Transport((SFTP_HOST, SFTP_PORT))
    t.connect(username=SFTP_USER, password=SFTP_PASS)
    sftp = paramiko.SFTPClient.from_transport(t)
    copied = skipped = 0
    def walk(path):
        nonlocal copied, skipped
        for e in sftp.listdir_attr(path):
            if e.filename.startswith("."):
                continue
            full = path.rstrip("/") + "/" + e.filename
            if stat.S_ISDIR(e.st_mode):
                walk(full); continue
            name = full.lstrip("/").replace("/", "__")
            if e.st_size == 0 or name in have:
                skipped += 1; continue
            try:
                buf = io.BytesIO(); sftp.getfo(full, buf); buf.seek(0)
                drive.files().create(body={"name": name, "parents": [FOLDER_ID]},
                                     media_body=MediaIoBaseUpload(buf, mimetype="text/plain"), fields="id").execute()
                copied += 1; print(f"copied {full} -> {name}")
            except Exception as ex:
                print(f"UPLOAD FAILED {full}: {str(ex)[:300]}")
    walk(REMOTE_ROOT)
    print(f"done: {copied} copied, {skipped} skipped (empty or already in Drive)")
    t.close()

if __name__ == "__main__":
    main()
