# PLAIN ENGLISH (Upload 835 files to ERA Center)
# Decides: Which downloaded 835 files are not already in ERA Center, and uploads those.
# Rules it uses: Skips checks already present. Dry-run with ERA_DRY=1.
# Never touches: Posting - upload only.
# ---
"""Upload 835 files into AMD ERA Center: POST /api/era/upload/835 (multipart field 'file').
Captured from William's UI import 9/2/2026. Skips checks already present in ERA Center.
Usage: python3 era_upload.py <file-or-dir> [...]   (dry run: ERA_DRY=1)"""
import amd, requests, json, os, sys, glob, time, re
BASE = "https://pm-api-103.advancedmd.com/api"
def hdrs():
    web, tok = amd.login_cached()
    return {"Authorization": "Bearer " + tok, "Accept": "application/json, text/plain, */*",
            "origin": "https://static-100.advancedmd.com", "referer": "https://static-100.advancedmd.com/"}
def checks():
    r = requests.get(BASE + "/era/checks", headers=hdrs(), timeout=60); r.raise_for_status(); return r.json()
def trn(path):
    t = open(path, encoding="latin-1").read()
    m = re.search(r"TRN\*1\*([^*~]+)", t); b = re.search(r"BPR\*[^*]*\*([\d.]+)", t)
    return (m.group(1) if m else None), (float(b.group(1)) if b else None)
def upload(path):
    with open(path, "rb") as fh:
        r = requests.post(BASE + "/era/upload/835", headers=hdrs(), files={"file": (os.path.basename(path), fh, "text/plain")}, timeout=120)
    return r.status_code, r.text[:300]
if __name__ == "__main__":
    files = []
    for a in sys.argv[1:]:
        files += sorted(glob.glob(os.path.join(a, "*"))) if os.path.isdir(a) else [a]
    have = {c["paymentnumber"] for c in checks()}
    log = open("era_upload.log", "a"); done = set(); n_ok = n_skip = n_fail = 0
    for f in files:
        if not open(f, encoding="latin-1").read(3) == "ISA": continue
        t, amt = trn(f)
        if t in have or t in done:
            n_skip += 1; log.write("SKIP %s %s already in ERA Center/dup\n" % (f, t)); continue
        if os.environ.get("ERA_DRY"): print("would upload", os.path.basename(f), t, amt); continue
        code, txt = upload(f); done.add(t)
        line = "%s %s %s $%s -> %s %s" % (time.strftime("%H:%M:%S"), os.path.basename(f), t, amt, code, txt.replace("\n"," "))
        print(line); log.write(line + "\n"); log.flush()
        if code in (200, 201, 202, 204): n_ok += 1
        else: n_fail += 1
        time.sleep(1.5)
    print("uploaded=%d skipped=%d failed=%d" % (n_ok, n_skip, n_fail))
