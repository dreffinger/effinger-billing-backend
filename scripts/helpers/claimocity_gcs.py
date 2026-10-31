# PLAIN ENGLISH (Claimocity feed files: list the practice's private bucket and download the ones not yet ingested - the routine's
#   step (a)+(b) since 10/31/2026, when the copy job moved from Drive to Cloud Storage because a service account may no longer write
#   into a personal Drive and an OAuth user token would need a published app with a verified domain).
# Decides: nothing. Reads the read-only key, lists gs://<bucket>, compares every object name (download__<sftp name>) with
#   registers/claimocity_ingest.json (keyed by the SFTP name) and downloads the unknown non-empty ones into <dest> (default
#   inbox/claimocity) for claimocity_ingest.py. Never deletes or moves anything in the bucket. Prints one summary line:
#   "gcs: N objects, K new downloaded, newest <yyyymmdd>" and, when the newest object is older than 2 days, "copy job stale".
# The key: secrets/claimocity_gcs_key.json (chmod 600) - the bootstrap writes it from the Gmail thread with subject
#   "claimocity gcs key" (the service account claimocity-reader@ehpa-project-50717, roles/storage.objectViewer only). Never printed.
# Network: needs oauth2.googleapis.com and storage.googleapis.com - exit 3 with a plain message when they are blocked.
# Exit 0 ok (also when nothing is new), 3 network blocked, 4 key missing, 5 gcloud/auth failure.
# Usage: python3 claimocity_gcs.py [--bucket ehpa-claimocity-feed-50717] [--key secrets/claimocity_gcs_key.json] [--dest inbox/claimocity] [--list-only]
import os, sys, re, json, subprocess, datetime

def opt(name, default=None):
    a = sys.argv[1:]
    return a[a.index(name) + 1] if name in a else default

WS = "/home/claude/unbilled"
BUCKET = opt("--bucket", os.environ.get("CLAIMOCITY_BUCKET", "ehpa-claimocity-feed-50717"))
KEY = opt("--key", os.path.join(WS, "secrets", "claimocity_gcs_key.json"))
DEST = opt("--dest", os.path.join(WS, "inbox", "claimocity"))
LIST_ONLY = "--list-only" in sys.argv
REG = os.path.join(WS, "registers", "claimocity_ingest.json")

def run(cmd, timeout=180):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

if not os.path.exists(KEY):
    print("gcs: key missing - write the JSON from the Gmail thread 'claimocity gcs key' to %s (chmod 600)" % KEY); sys.exit(4)
try:
    acct = json.load(open(KEY)).get("client_email", "")
except Exception as e:
    print("gcs: key file unreadable:", str(e)[:120]); sys.exit(4)
r = run(["gcloud", "auth", "activate-service-account", acct, "--key-file", KEY, "--quiet"])
if r.returncode:
    msg = (r.stderr or r.stdout).strip()
    if re.search(r"oauth2.googleapis.com|Could not resolve|Connection refused|403|proxy|network", msg, re.I):
        print("gcs: BLOCKED - the environment must allow oauth2.googleapis.com and storage.googleapis.com (Network access = Custom: add both, or Full):", msg[-200:]); sys.exit(3)
    print("gcs: auth failed:", msg[-300:]); sys.exit(5)
r = run(["gcloud", "storage", "ls", "--long", "gs://%s/" % BUCKET], timeout=240)
if r.returncode:
    msg = (r.stderr or r.stdout).strip()
    if re.search(r"storage.googleapis.com|Could not resolve|Connection refused|proxy|network", msg, re.I):
        print("gcs: BLOCKED - the environment must allow storage.googleapis.com (and oauth2.googleapis.com):", msg[-200:]); sys.exit(3)
    print("gcs: list failed:", msg[-300:]); sys.exit(5)
objects = []
for line in r.stdout.splitlines():
    m = re.match(r"\s*(\d+)\s+(\S+)\s+gs://[^/]+/(.+)$", line)
    if m: objects.append((m.group(3), int(m.group(1)), m.group(2)))
reg = json.load(open(REG)) if os.path.exists(REG) else {"files": {}, "runs": []}
known = set(reg.get("files", {}))
def sftp_name(n): return re.sub(r"^(download__)+", "", n)
dates = sorted({d.group(0) for n, _, _ in objects for d in [re.search(r"20\d{6}", sftp_name(n))] if d})
new = [(n, size) for n, size, _ in objects if size > 0 and sftp_name(n) not in known and n.endswith(".hl7")]
os.makedirs(DEST, exist_ok=True)
got = 0
if not LIST_ONLY:
    for n, size in new:
        target = os.path.join(DEST, n)
        if os.path.exists(target) and os.path.getsize(target) == size:
            got += 1; continue
        c = run(["gcloud", "storage", "cp", "gs://%s/%s" % (BUCKET, n), target], timeout=300)
        if c.returncode or not os.path.exists(target) or os.path.getsize(target) != size:
            print("gcs: download failed", n, (c.stderr or "")[-160:]); continue
        got += 1
newest = dates[-1] if dates else None
stale = ""
if newest:
    age = (datetime.date.today() - datetime.date(int(newest[:4]), int(newest[4:6]), int(newest[6:8]))).days
    if age > 2: stale = " - copy job stale: newest file is %d days old (claimocity/cloud_run/DEPLOY.md)" % age
print("gcs: %d objects in gs://%s, %d new%s, newest %s%s" % (len(objects), BUCKET, len(new), "" if LIST_ONLY else " (%d downloaded to %s)" % (got, DEST), newest, stale))
for n, size in new: print("   new:", n, size, "bytes")
