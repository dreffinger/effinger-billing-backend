"""Claimocity SFTP -> Google Drive copy job (claimocity-pull), v3 2026-10-29.
PLAIN ENGLISH: every 30 minutes, list /download on sftp.claimocity.io (the root AND its subfolders) and upload every non-empty
file not yet in the Drive folder 'Claimocity drop' (name = SFTP path with '/' turned into '__', e.g. download__20261029...hl7).
COPY ONLY: nothing on Claimocity is ever deleted, moved or renamed - the files pile up there and that is fine (William 10/28/2026).
Auth: the job's own service account through google.auth.default (the Drive folder is shared with it as Editor, 9/18/2026 fix);
no user refresh token, no OAuth client secret. The v1/v2 jobs skipped the /download ROOT, where Claimocity actually drops the
daily DFT file - that is why 'done: 0 copied, N skipped' said nothing about the 10/16-10/27 backlog.
"""
import io, os, stat
import paramiko, google.auth
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

SFTP_HOST = "sftp.claimocity.io"; SFTP_PORT = 22; SFTP_USER = "kykzfgie"
REMOTE_ROOT = os.environ.get("REMOTE_ROOT", "/download")
FOLDER_ID = os.environ["DRIVE_FOLDER_ID"]          # 'Claimocity drop'
SFTP_PASS = os.environ["SFTP_PASS"]                # Secret Manager claimocity-sftp-pass

def drive_client():
    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/drive"])
    return build("drive", "v3", credentials=creds, cache_discovery=False)

def existing_names(drive):
    names, token = set(), None
    while True:
        resp = drive.files().list(q=f"'{FOLDER_ID}' in parents and trashed=false", fields="nextPageToken,files(name)",
                                  pageToken=token, pageSize=1000, supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
        names |= {f["name"] for f in resp.get("files", [])}
        token = resp.get("nextPageToken")
        if not token:
            return names

def main():
    drive = drive_client()
    have = existing_names(drive)
    print(f"drive folder ok: {len(have)} files already there")
    transport = paramiko.Transport((SFTP_HOST, SFTP_PORT))
    transport.connect(username=SFTP_USER, password=SFTP_PASS)
    sftp = paramiko.SFTPClient.from_transport(transport)
    copied = skipped = seen = 0
    def walk(path):
        nonlocal copied, skipped, seen
        for entry in sftp.listdir_attr(path):
            full = path.rstrip("/") + "/" + entry.filename
            if entry.filename.startswith("."):
                continue
            if stat.S_ISDIR(entry.st_mode):
                walk(full); continue
            seen += 1
            name = full.lstrip("/").replace("/", "__")
            if entry.st_size == 0 or name in have:
                skipped += 1; continue
            try:
                buf = io.BytesIO(); sftp.getfo(full, buf); buf.seek(0)
                drive.files().create(body={"name": name, "parents": [FOLDER_ID]},
                                     media_body=MediaIoBaseUpload(buf, mimetype="text/plain"), fields="id", supportsAllDrives=True).execute()
                have.add(name); copied += 1; print(f"copied {full} ({entry.st_size} bytes)")
            except Exception as e:
                print(f"UPLOAD FAILED {full}: {str(e)[:200]}")
    walk(REMOTE_ROOT)
    print(f"done: {seen} files on sftp under {REMOTE_ROOT}, {copied} copied, {skipped} skipped (empty or already in Drive)")
    transport.close()

if __name__ == "__main__":
    main()
