#!/usr/bin/env python3
# PLAIN ENGLISH (The triple mirror - GitHub, Postman, Drive - local half)
# Decides: Nothing about billing. Runs the file-side of the mirror that ends every billing run:
#   1. registry  - workspace captured_calls.md (+ any captured_calls_additions_*.md pulled from Drive)
#                  -> merged, PHI-gated -> docs/captured_calls.md
#   2. helpers   - every *.py / carriers.json / facilities.json in the workspace that is newer than
#                  the repo copy -> PHI-gated -> scripts/helpers/  (so a fresh container can restore)
#   3. postman   - docs/api_vocabulary.json -> docs/postman_effinger_amd.json (generated)
#   4. git       - commit, push main AND the project's synced branch; if the proxy says 403
#                  ("not in this session's authorized repository set") write a bundle to
#                  /home/claude/unbilled/outbox/ for William and say so - never retry the push.
#   The Drive and Postman legs are done by the run itself with the connectors (see docs/MIRROR.md):
#   this script prints exactly which files to upload and to which Drive folder.
# Rules it uses: no PHI on GitHub (phi_gate on every file that crosses); Drive is the PHI-OK copy;
#   the vocabulary is the source of the Postman collection; one commit per run, dated message.
# Never touches: AMD, Stedi, Drive, Postman. Only files and git.
# ---
import os, re, sys, glob, json, shutil, subprocess, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WS = os.environ.get("BILLING_WORKSPACE", "/home/claude/unbilled")
GATE = os.path.join(ROOT, "tools", "mirror", "phi_gate.py")
PMB = os.path.join(ROOT, "tools", "mirror", "postman_build.py")
REPO = "dreffinger/effinger-billing-backend"
BRANCHES = ["main", "claude/effinger-billing-backend-mirror-w74pqv"]   # main = record; 2nd = project's synced source
DRIVE = {"project files": "1-AsLUHMaeqvHq-fqWKUVKKUU4Xkw6XTt", "workspace mirror": "135OCbRNCnFLyVm2GBXk1XsE3lt0vnsrn",
         "github mirror": "1yr8X30h01-tPa0swclvtBFdAisiHzgJ8", "chat history": "1VCZfjSmok1fNNnYwf2yBTXlZ-zMUnAWU"}
TODAY = datetime.date.today().isoformat()

def sh(cmd, check=True, **kw):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=ROOT, **kw)
    if check and r.returncode:
        raise SystemExit("FAILED: %s\n%s%s" % (cmd, r.stdout, r.stderr))
    return r

def gate(src, dst):
    r = subprocess.run([sys.executable, GATE, src, dst], capture_output=True, text=True)
    sys.stdout.write(r.stdout)
    if r.returncode:
        sys.stdout.write(r.stderr)
        raise SystemExit("phi_gate BLOCKED %s - fix the source (or add the name to secrets/pseudonyms.json) and rerun" % src)

# ---- 1. registry ---------------------------------------------------------------------------------
def merge_registry():
    base = os.path.join(WS, "captured_calls.md")
    if not os.path.exists(base):
        print("registry: no %s in the workspace - download it from Drive 'billing agent project files' first" % base)
        return False
    text = open(base).read()
    adds = sorted(glob.glob(os.path.join(WS, "captured_calls_additions_*.md")))
    merged = 0
    for a in adds:
        body = open(a).read().strip()
        if body and body[:200] not in text:
            text = text.rstrip() + "\n\n" + body + "\n"
            merged += 1
    if merged:
        open(base, "w").write(text)
        print("registry: merged %d additions file(s) into workspace captured_calls.md" % merged)
    dst = os.path.join(ROOT, "docs", "captured_calls.md")
    prior = open(dst).read() if os.path.exists(dst) else ""
    gate(base, dst)
    union_prior_record(dst, prior)
    return True

def _sections(text):
    """Split a registry into (header_line, body) blocks; header = any line starting with '#'."""
    out, cur, buf = [], None, []
    for line in text.splitlines():
        if line.startswith("#"):
            if cur is not None or buf:
                out.append((cur, "\n".join(buf)))
            cur, buf = line.strip(), [line]
        else:
            buf.append(line)
    if cur is not None or buf:
        out.append((cur, "\n".join(buf)))
    return out

def union_prior_record(dst, prior):
    """The gate re-derives docs/captured_calls.md from the workspace base, which may be an OLDER Drive copy
    than the repo record. Keep every prior-record section whose header is missing from the new copy
    (appended in their original order) so the record only ever grows. Lesson from the 9/12 runs."""
    if not prior.strip():
        return
    new = open(dst).read()
    have = {h for h, _ in _sections(new) if h}
    missing = [(h, b) for h, b in _sections(prior) if h and h not in have and b.strip()]
    if not missing:
        return
    text = new.rstrip() + "\n\n" + "\n\n".join(b.rstrip() for _, b in missing) + "\n"
    open(dst, "w").write(text)
    print("registry: union kept %d prior-record section(s) the Drive base did not carry" % len(missing))

# ---- 2. helpers ---------------------------------------------------------------------------------
HELPER_GLOBS = ["*.py", "*.sh", "carriers.json", "facilities.json"]
SKIP = {"vocab_seed.json"}
def sync_helpers():
    dst_dir = os.path.join(ROOT, "scripts", "helpers")
    os.makedirs(dst_dir, exist_ok=True)
    n = 0
    for g in HELPER_GLOBS:
        for src in glob.glob(os.path.join(WS, g)):
            name = os.path.basename(src)
            if name in SKIP or name.startswith("."):
                continue
            dst = os.path.join(dst_dir, name)
            if os.path.exists(dst) and os.path.getmtime(dst) >= os.path.getmtime(src):
                continue
            gate(src, dst); n += 1
    print("helpers: %d file(s) refreshed into scripts/helpers/" % n)

# ---- 3. postman ---------------------------------------------------------------------------------
def build_postman():
    r = subprocess.run([sys.executable, PMB], capture_output=True, text=True)
    sys.stdout.write(r.stdout + r.stderr)
    if r.returncode:
        raise SystemExit("postman build failed")

# ---- 4. git -------------------------------------------------------------------------------------
def token():
    for p in (os.path.join(ROOT, "secrets", "github_pat.key"), os.path.join(WS, "secrets", "github_pat.key")):
        if os.path.exists(p):
            return open(p).read().strip()
    return None

def commit_and_push(message):
    sh("git add -A")
    st = sh("git status --porcelain").stdout.strip()
    if not st:
        print("git: nothing changed since the last mirror")
    else:
        sh('git -c user.name="billing-mirror" -c user.email="mirror@effinger.local" commit -q -m %s' % json.dumps(message))
        print("git: committed -> %s" % sh("git rev-parse --short HEAD").stdout.strip())
    tok = token()
    if not tok:
        print("git: no secrets/github_pat.key - push skipped (fetch the PAT from Gmail 'github claude token' first)")
        return bundle()
    url = "https://x-access-token:%s@github.com/%s" % (tok, REPO)
    head = sh("git rev-parse --abbrev-ref HEAD").stdout.strip()
    for b in BRANCHES:
        r = sh("git push -q %s %s:refs/heads/%s" % (url, head, b), check=False)
        out = (r.stdout + r.stderr).replace(tok, "<PAT>")
        if r.returncode == 0:
            print("git: pushed -> %s" % b)
        elif "authorized repository set" in out or "403" in out:
            print("git: PUSH BLOCKED by the session proxy (repo not in this session's authorized sources) - not retrying")
            return bundle()
        else:
            print("git: push to %s failed:\n%s" % (b, out[-600:]))
            return bundle()
    return True

def bundle():
    """Fallback: a git bundle William can push from his own machine (small, one file)."""
    out = os.path.join(WS, "outbox"); os.makedirs(out, exist_ok=True)
    path = os.path.join(out, "effinger-billing-backend_%s.bundle" % TODAY)
    sh("git bundle create -q %s --all" % path)
    print("git: wrote %s - upload it to Drive 'github mirror' (%s); William: git pull <bundle> main && git push"
          % (path, DRIVE["github mirror"]))
    return False

# ---- driver -------------------------------------------------------------------------------------
def status():
    print("repo: %s  HEAD %s  branch %s" % (ROOT, sh("git rev-parse --short HEAD").stdout.strip(), sh("git rev-parse --abbrev-ref HEAD").stdout.strip()))
    print("unpushed vs origin/main: %s commit(s)" % sh("git rev-list --count origin/main..HEAD", check=False).stdout.strip())
    subprocess.run([sys.executable, PMB, "--check"])
    v = json.load(open(os.path.join(ROOT, "docs", "api_vocabulary.json")))
    print("vocabulary: %d calls in %d folders" % (len(v["calls"]), len({c["folder"] for c in v["calls"]})))
    print("pseudonym map: %s   PAT: %s" % ("present" if os.path.exists(os.path.join(ROOT, "secrets", "pseudonyms.json")) else "MISSING", "present" if token() else "missing"))

def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "status":
        return status()
    if cmd == "sync":
        msg = sys.argv[2] if len(sys.argv) > 2 else "mirror %s" % TODAY
        merge_registry()
        sync_helpers()
        build_postman()
        ok = commit_and_push(msg)
        print("\nNEXT (connector legs, in this order):")
        print(" Drive 'billing agent project files' (%s): rename the old captured_calls.md -> captured_calls_%s_pre-merge.md, upload the WORKSPACE copy %s/captured_calls.md (real names) as captured_calls.md; upload docs/postman_effinger_amd.json and trash the previous copy" % (DRIVE["project files"], TODAY, WS))
        print(" Drive 'workspace mirror' (%s): upload every helper changed this run + secrets/pseudonyms.json (PHI: Drive only)" % DRIVE["workspace mirror"])
        print(" Postman connector: updateCollection with docs/postman_effinger_amd.json (createCollection the first time)")
        print(" Drive 'chat history' (%s): the dated digest" % DRIVE["chat history"])
        if not ok:
            print(" Drive 'github mirror' (%s): the bundle from %s/outbox/" % (DRIVE["github mirror"], WS))
        return
    if cmd == "postman":
        return build_postman()
    sys.exit("usage: mirror.py [status|sync \"message\"|postman]")

if __name__ == "__main__":
    main()
