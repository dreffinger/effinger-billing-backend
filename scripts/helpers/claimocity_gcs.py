# PLAIN ENGLISH (Claimocity feed files: list the practice's private bucket and download the ones not yet ingested - the routine's
#   step (a)+(b) since 10/31/2026, when the copy job moved from Drive to Cloud Storage because a service account may no longer write
#   into a personal Drive and an OAuth user token would need a published app with a verified domain).
# Decides: nothing. Reads the read-only key, lists gs://<bucket>, compares every object name (download__<sftp name>) with
#   registers/claimocity_ingest.json (keyed by the SFTP name) and downloads the unknown non-empty ones into <dest> (default
#   inbox/claimocity) for claimocity_ingest.py. Never deletes or moves anything in the bucket. Prints one summary line:
#   "gcs: N objects, K new downloaded, newest <yyyymmdd>" and, when the newest object is older than 2 days, "copy job stale".
# The key: secrets/claimocity_gcs_key.json (chmod 600), the read-only service account claimocity-reader@ehpa-project-50717
#   (roles/storage.objectViewer only). The routine installs it once per container with `--install-key <file>`: the file is the
#   plaintext body of the newest message in the Gmail thread "claimocity gcs key", written as returned - either the whole key JSON
#   or just the private key's base64 lines (William 10/30 pasted only those; the client_email and project are fixed, and Google
#   accepts the JWT without a private_key_id). Nothing from the key is ever printed.
# Network: needs oauth2.googleapis.com and storage.googleapis.com - exit 3 with a plain message when they are blocked.
# Exit 0 ok (also when nothing is new), 3 network blocked, 4 key missing / unusable key mail, 5 gcloud/auth failure.
# Usage: python3 claimocity_gcs.py [--bucket ehpa-claimocity-feed-50717] [--key secrets/claimocity_gcs_key.json] [--dest inbox/claimocity] [--list-only]
#        python3 claimocity_gcs.py --install-key secrets/gcs_key_mail.txt   (writes --key and exits; run again without it)
import os, sys, re, json, base64, subprocess, datetime

def opt(name, default=None):
    a = sys.argv[1:]
    return a[a.index(name) + 1] if name in a else default

WS = "/home/claude/unbilled"
PROJECT = "ehpa-project-50717"
READER = "claimocity-reader@%s.iam.gserviceaccount.com" % PROJECT
BUCKET = opt("--bucket", os.environ.get("CLAIMOCITY_BUCKET", "ehpa-claimocity-feed-50717"))
KEY = opt("--key", os.path.join(WS, "secrets", "claimocity_gcs_key.json"))
DEST = opt("--dest", os.path.join(WS, "inbox", "claimocity"))
LIST_ONLY = "--list-only" in sys.argv
INSTALL = opt("--install-key")
REG = os.path.join(WS, "registers", "claimocity_ingest.json")

def run(cmd, timeout=180):
    # The cloud containers preset CLOUDSDK_AUTH_ACCESS_TOKEN (a placeholder the proxy fills for a Google Cloud connector that the
    # billing routines do not have); it overrides the activated service account and yields "401 Invalid Credentials", so drop it.
    env = {k: v for k, v in os.environ.items() if k != "CLOUDSDK_AUTH_ACCESS_TOKEN"}
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)

def pem_from_text(txt):
    """The private key's base64 lines out of free text: real newlines, literal \\n (as the JSON value carries them) or
    doubled backslashes all count as line breaks; the block starts at the first MII... line and ends at the first non-base64 line."""
    body = txt.replace("\\\\n", "\n").replace("\\n", "\n").replace("\r", "\n")
    lines = [l.strip().rstrip("\\").strip() for l in body.split("\n")]
    out, started = [], False
    for l in lines:
        if not started:
            if l.startswith("MII") and re.fullmatch(r"[A-Za-z0-9+/=]{20,}", l): started = True; out.append(l)
            continue
        if re.fullmatch(r"[A-Za-z0-9+/=]{1,}", l): out.append(l)
        elif l.startswith("-----END") or l == "" and out: break
        else: break
    if not out: return None
    return "-----BEGIN PRIVATE KEY-----\n" + "\n".join(out) + "\n-----END PRIVATE KEY-----\n"

def install_key(path):
    txt = open(path, errors="replace").read()
    info = None
    for cand in (txt, txt.replace("\r", "").replace("\n", "")):      # second try: the mail client wrapped the JSON's long line
        for m in re.finditer(r"\{", cand):
            try: obj, _ = json.JSONDecoder().raw_decode(cand[m.start():])
            except Exception: continue
            if isinstance(obj, dict) and obj.get("private_key"): info = obj; break
        if info: break
    if info is None:
        pem = pem_from_text(txt)
        if not pem:
            print("gcs: key mail unusable - no key JSON and no private-key lines found; William re-sends the whole JSON that Cloud Shell printed (subject 'claimocity gcs key')"); sys.exit(4)
        info = {"type": "service_account", "project_id": PROJECT, "private_key": pem, "client_email": READER}
    pem = info["private_key"].replace("\\n", "\n")
    body = "".join(l for l in pem.splitlines() if l and not l.startswith("-----"))
    try:
        der = base64.b64decode(body, validate=True)
        from cryptography.hazmat.primitives import serialization
        serialization.load_pem_private_key(pem.encode(), password=None)
    except ImportError:
        der = base64.b64decode(body, validate=True)
    except Exception as e:
        print("gcs: key mail unusable - the private key does not parse (%s); William re-sends the whole JSON that Cloud Shell printed" % type(e).__name__); sys.exit(4)
    info["private_key"] = pem
    info.setdefault("type", "service_account"); info.setdefault("project_id", PROJECT); info.setdefault("client_email", READER)
    info.setdefault("token_uri", "https://oauth2.googleapis.com/token"); info.setdefault("auth_uri", "https://accounts.google.com/o/oauth2/auth")
    info.setdefault("auth_provider_x509_cert_url", "https://www.googleapis.com/oauth2/v1/certs"); info.setdefault("universe_domain", "googleapis.com")
    os.makedirs(os.path.dirname(KEY), exist_ok=True)
    with open(KEY, "w") as f: json.dump(info, f, indent=1)
    os.chmod(KEY, 0o600)
    print("gcs: key installed - %s (%d key bytes) -> %s" % (info["client_email"], len(der), KEY))

if INSTALL:
    install_key(INSTALL); sys.exit(0)
if not os.path.exists(KEY):
    print("gcs: key missing - Write the newest 'claimocity gcs key' mail body to %s/secrets/gcs_key_mail.txt and run claimocity_gcs.py --install-key secrets/gcs_key_mail.txt" % WS); sys.exit(4)
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
