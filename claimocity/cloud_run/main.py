"""Claimocity SFTP -> Google Drive copy job (claimocity-pull), v4 2026-10-31.
PLAIN ENGLISH: every 30 minutes, list /download on sftp.claimocity.io (the root AND its subfolders) and upload every non-empty file
not yet in the Drive folder FOLDER_NAME (default 'Claimocity feed drop'; name = SFTP path with '/' turned into '__').
COPY ONLY: nothing on Claimocity is ever deleted, moved or renamed - the files pile up there and that is fine (William 10/28/2026).
AUTH (the 10/30 lesson): a service account cannot create files in a personal Drive any more - Google answers
  403 "Service Accounts do not have storage quota" - so the job uploads AS WILLIAM with his OAuth refresh token, scope drive.file
  (the narrow, non-sensitive scope: the app sees only files it created). Credentials come from Secret Manager secret
  drive-user-creds (authorized_user json: client_id, client_secret, refresh_token) mounted as the env var DRIVE_USER_CREDS.
  With drive.file the app cannot write into a folder it did not create, so it keeps its OWN folder: on first run it creates
  FOLDER_NAME in William's My Drive and prints the id; later runs find it again by name.
"""
import io, os, stat, json
import paramiko
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

SFTP_HOST = "sftp.claimocity.io"; SFTP_PORT = 22; SFTP_USER = "kykzfgie"
REMOTE_ROOT = os.environ.get("REMOTE_ROOT", "/download")
FOLDER_NAME = os.environ.get("FOLDER_NAME", "Claimocity feed drop")
SFTP_PASS = os.environ["SFTP_PASS"]                # Secret Manager claimocity-sftp-pass
SCOPES = ["https://www.googleapis.com/auth/drive.file"]

def drive_client():
    info = json.loads(os.environ["DRIVE_USER_CREDS"])
    creds = Credentials(None, refresh_token=info["refresh_token"], token_uri="https://oauth2.googleapis.com/token",
                        client_id=info["client_id"], client_secret=info["client_secret"], scopes=SCOPES)
    return build("drive", "v3", credentials=creds, cache_discovery=False)

def folder_id(drive):
    q = "mimeType='application/vnd.google-apps.folder' and name='%s' and trashed=false" % FOLDER_NAME.replace("'", "\\'")
    r = drive.files().list(q=q, fields="files(id,name)", pageSize=5).execute().get("files", [])
    if r:
        return r[0]["id"], False
    f = drive.files().create(body={"name": FOLDER_NAME, "mimeType": "application/vnd.google-apps.folder"}, fields="id").execute()
    return f["id"], True

def existing_names(drive, fid):
    names, token = set(), None
    while True:
        resp = drive.files().list(q="'%s' in parents and trashed=false" % fid, fields="nextPageToken,files(name)", pageToken=token, pageSize=1000).execute()
        names |= {f["name"] for f in resp.get("files", [])}
        token = resp.get("nextPageToken")
        if not token:
            return names

def main():
    drive = drive_client()
    fid, created = folder_id(drive)
    print("drive folder %s: %s (id %s) - https://drive.google.com/drive/folders/%s" % ("CREATED" if created else "ok", FOLDER_NAME, fid, fid))
    have = existing_names(drive, fid)
    print("drive folder ok: %d files already there" % len(have))
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
                drive.files().create(body={"name": name, "parents": [fid]}, media_body=MediaIoBaseUpload(buf, mimetype="text/plain"), fields="id").execute()
                have.add(name); copied += 1; print("copied %s (%d bytes)" % (full, entry.st_size))
            except Exception as e:
                print("UPLOAD FAILED %s: %s" % (full, str(e)[:200]))
    walk(REMOTE_ROOT)
    print("done: %d files on sftp under %s, %d copied, %d skipped (empty or already in Drive)" % (seen, REMOTE_ROOT, copied, skipped))
    transport.close()

if __name__ == "__main__":
    main()
