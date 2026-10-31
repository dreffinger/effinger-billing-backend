"""Claimocity SFTP -> Cloud Storage copy job (claimocity-pull), v5 2026-10-31.
PLAIN ENGLISH: every 30 minutes, list /download on sftp.claimocity.io (the root AND its subfolders) and copy every non-empty file
not yet in the private bucket BUCKET (object name = SFTP path with '/' turned into '__', e.g. download__20261029...hl7).
COPY ONLY: nothing on Claimocity is ever deleted, moved or renamed - the files pile up there and that is fine (William 10/28/2026).
WHY A BUCKET (10/30-10/31): Google no longer lets a service account create files in a personal Drive ("Service Accounts do not have
  storage quota"), and publishing an OAuth app for a user token now needs a verified domain with a privacy page. A bucket in the
  practice's own project has neither problem: the job's service account writes it, and the billing routines read it with the
  read-only key of claimocity-reader@ (fetched from the Gmail thread "claimocity gcs key", like the Stedi key).
"""
import io, os, stat
import paramiko
from google.cloud import storage

SFTP_HOST = "sftp.claimocity.io"; SFTP_PORT = 22; SFTP_USER = "kykzfgie"
REMOTE_ROOT = os.environ.get("REMOTE_ROOT", "/download")
BUCKET = os.environ["BUCKET"]                      # e.g. ehpa-claimocity-feed-50717
SFTP_PASS = os.environ["SFTP_PASS"]                # Secret Manager claimocity-sftp-pass

def main():
    bucket = storage.Client().bucket(BUCKET)
    have = {b.name for b in bucket.list_blobs()}
    print("bucket ok: gs://%s has %d files already" % (BUCKET, len(have)))
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
                bucket.blob(name).upload_from_file(buf, content_type="text/plain")
                have.add(name); copied += 1; print("copied %s (%d bytes)" % (full, entry.st_size))
            except Exception as e:
                print("UPLOAD FAILED %s: %s" % (full, str(e)[:200]))
    walk(REMOTE_ROOT)
    print("done: %d files on sftp under %s, %d copied, %d skipped (empty or already in the bucket)" % (seen, REMOTE_ROOT, copied, skipped))
    transport.close()

if __name__ == "__main__":
    main()
