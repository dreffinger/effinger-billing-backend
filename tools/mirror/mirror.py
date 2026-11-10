#!/usr/bin/env python3
# PLAIN ENGLISH (The triple mirror - GitHub, Postman, Drive - local half)
# Decides: Nothing about billing. Runs the file-side of the mirror that ends every billing run:
#   1. registry  - workspace captured_calls.md (+ any captured_calls_additions_*.md pulled from Drive)
#                  -> merged, PHI-gated -> docs/captured_calls.md
#   2. helpers   - every *.py / carriers.json / facilities.json in the workspace that is newer than
#                  the repo copy -> PHI-gated -> scripts/helpers/  (so a fresh container can restore);
#                  a stale Drive-overlaid copy of the seven protected helpers never overwrites the repo's
#   2b. tree gate - phi_gate.py tree . before `git add -A`: registers / run artifacts scrubbed in place,
#                  digests / needs lists / run reports kept out (Drive only)  (10/6/2026)
#   3. postman   - docs/api_vocabulary.json -> docs/postman_effinger_amd.json (generated)
#   4. git       - commit, push main AND the project's synced branch: with the PAT when secrets/github_pat.key
#                  exists, otherwise through the session proxy (11/2/2026 - a cloud session with the repository
#                  attached needs no PAT: fetch + merge origin/main, push main, push the synced branch); only when
#                  the proxy says 403 ("not in this session's authorized repository set") leave HEAD on its own
#                  branch upstream and write a PACKAGE to /home/claude/unbilled/outbox/ - never retry the push.
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
# 10/6/2026: the repository is the record for these seven. A workspace copy overlaid from Drive carries a fresh
# mtime but can be OLDER code (the pre-10/6 move_to_ins ignores --no-rebill; the old freq1_visit has no reroute);
# a copy that lacks its marker never overwrites scripts/helpers/, whatever its mtime says.
PROTECTED = {"amd.py": "_REBILLED", "resave.py": "def set_insorder", "freq1_visit.py": "def reroute",
             "move_to_ins.py": "--no-rebill", "ins_update.py": "_set_order", "dx_primary_fix.py": "--visits",
             "approval_submit.py": "LASTFIRST", "payreasons.py": "10/6: no patient name", "columns_scan.py": "NAMEKEY",
             # 11/10/2026: the feed import carries William's place-of-service rule (CCM in a nursing building = 32, visits by frequency);
             # a workspace copy from before the rule must never put the old all-31 code back on main
             "claimocity_import.py": "def nf_visit_pos", "claimocity_report.py": "Place of service in the nursing buildings",
             "claimocity_inspector.py": "CCM at the hospital location"}
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
            marker = PROTECTED.get(name)
            if marker and os.path.exists(dst) and marker not in open(src, errors="replace").read():
                print("helpers: STALE workspace copy of %s skipped (no '%s' - the repo copy is newer code); copy the repo's back over the workspace" % (name, marker))
                continue
            gate(src, dst); n += 1
    print("helpers: %d file(s) refreshed into scripts/helpers/" % n)

def gate_tree():
    """10/6/2026: everything `git add -A` would commit passes through phi_gate's tree mode first - registers,
    scan summaries and run artifacts under practices/ and nightly/runs/ were reaching GitHub with patient
    names in them. Names -> pseudonym or [name]; identifiers -> [MBI]/[SSN]/[member id]; a run digest, needs
    list / needs section or run report never enters the tree (Drive carries those)."""
    r = subprocess.run([sys.executable, GATE, "tree", "."], capture_output=True, text=True, cwd=ROOT)
    sys.stdout.write(r.stdout)
    if r.returncode:
        sys.stdout.write(r.stderr)
        raise SystemExit("phi_gate tree FAILED - nothing committed; fix the source and rerun")

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
    gate_tree()
    sh("git add -A")
    st = sh("git status --porcelain").stdout.strip()
    if not st:
        print("git: nothing changed since the last mirror")
    else:
        trailer = "\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>\nClaude-Session: %s" % os.environ.get("CLAUDE_SESSION_URL", "(set CLAUDE_SESSION_URL to the running session before mirror.py sync)")
        msgfile = os.path.join(WS, "outbox", ".commit_msg.txt"); os.makedirs(os.path.dirname(msgfile), exist_ok=True)
        open(msgfile, "w").write(message + trailer + "\n")   # 9/25: -F keeps the trailer on real lines (json.dumps through the shell left literal \n in the message)
        sh('git -c user.name="Claude" -c user.email="noreply@anthropic.com" commit -q -F %s' % json.dumps(msgfile))   # 9/22 stop-hook rule: commits are authored by Claude <noreply@anthropic.com>, never billing-mirror
        print("git: committed -> %s" % sh("git rev-parse --short HEAD").stdout.strip())
    tok = token()
    if not tok:
        print("git: no secrets/github_pat.key - pushing through the session proxy (the attached repository's own credential)")
        if push_via_proxy():
            return True
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

UNION = ["docs/captured_calls.md merge=union", "docs/captured_calls_additions_*.md merge=union", "practices/ehpa/rules.md merge=union",
         "needs_facesheet_list.md merge=union", "docs/SHARED_LESSONS.md merge=union", "practices/ehpa/registers/rebill_log.jsonl merge=union"]
def union_rules():
    """Append-only text files merge by union (both sides kept) when origin/main moved under us - the same list
    tools/mirror/apply_bundle.py uses; written to .git/info/attributes (repo-local, never committed). Idempotent."""
    d = sh("git rev-parse --git-dir").stdout.strip()
    if not os.path.isabs(d):
        d = os.path.join(ROOT, d)
    f = os.path.join(d, "info", "attributes"); os.makedirs(os.path.dirname(f), exist_ok=True)
    have = open(f).read() if os.path.exists(f) else ""
    add = [r for r in UNION if r not in have]
    if add:
        open(f, "a").write(("" if not have or have.endswith("\n") else "\n") + "\n".join(add) + "\n")

def push_via_proxy():
    """11/2/2026 (William: "make it permanent where I don't have to manually push anything"): a Claude Code cloud session with
    the repository attached pushes through the session proxy, which injects the repository's credential - no PAT, no Drive
    package, no pull request for William to merge. origin/main moves every few hours, so bring it in first (a merge commit;
    append-only files merge by union), then push main and the project's synced branch. A push that GitHub rejects as
    non-fast-forward (main moved again meanwhile) is retried once after another merge. Returns True when main carries HEAD;
    False when the proxy or GitHub refuses - HEAD is then left safe on its own branch upstream and the caller writes the package."""
    for attempt in (1, 2):
        r = sh("git fetch -q origin main", check=False)
        if r.returncode:
            print("git: fetch origin main failed - %s" % (r.stdout + r.stderr).strip()[-300:]); return False
        union_rules()
        if sh("git merge-base --is-ancestor origin/main HEAD", check=False).returncode != 0:
            m = sh('git -c user.name="Claude" -c user.email="noreply@anthropic.com" merge -q --no-edit origin/main', check=False)
            if m.returncode:
                sh("git merge --abort", check=False)
                print("git: merging origin/main CONFLICTS - resolve by hand, then rerun:\n%s" % (m.stdout + m.stderr).strip()[-600:]); return False
            print("git: merged origin/main -> %s" % sh("git rev-parse --short HEAD").stdout.strip())
        r = sh("git push -q origin HEAD:refs/heads/%s" % BRANCHES[0], check=False)
        out = (r.stdout + r.stderr).strip()
        if r.returncode == 0:
            print("git: pushed -> %s (session proxy)" % BRANCHES[0]); break
        if attempt == 1 and ("fetch first" in out or "non-fast-forward" in out):
            print("git: main moved during the push - merging it once more"); continue
        print("git: push to %s refused - %s" % (BRANCHES[0], out[-400:]))
        head = sh("git rev-parse --abbrev-ref HEAD", check=False).stdout.strip()
        if head and head != "HEAD" and head not in BRANCHES:
            r2 = sh("git push -q -u origin %s" % head, check=False)
            print("git: HEAD kept safe on origin/%s%s - open a pull request for it" % (head, "" if r2.returncode == 0 else " FAILED too"))
        return False
    for b in BRANCHES[1:]:
        r = sh("git push -q origin HEAD:refs/heads/%s" % b, check=False)
        print("git: pushed -> %s (session proxy)" % b if r.returncode == 0 else "git: push to %s failed (main is pushed; the synced branch catches up on the next mirror) - %s" % (b, (r.stdout + r.stderr).strip()[-300:]))
    return True

def bundle(slug="", base_ref=None):
    """Fallback when the push is blocked (William 9/23/2026): leave a PACKAGE the 2-hourly routine applies to the triple mirror -
    a thin git bundle (everything after origin/main when that ref is known, else --all), the same bundle as base64 TEXT (Drive
    text uploads survive; binaries download corrupt through the connector) and a JSON manifest with the sha256 the routine
    verifies before `tools/mirror/apply_bundle.py` pulls it and pushes main + the synced branch. Nothing learned waits for William."""
    import hashlib, base64, json as _json
    out = os.path.join(WS, "outbox"); os.makedirs(out, exist_ok=True)
    stem = "effinger-billing-backend_%s%s" % (TODAY, ("_" + slug) if slug else "")
    path = os.path.join(out, stem + ".bundle")
    base = sh("git rev-parse --verify -q %s" % (base_ref or "origin/main"), check=False).stdout.strip()   # base_ref: a follow-up package on top of an earlier package's head (its commits are not on origin yet)
    branch = sh("git rev-parse --abbrev-ref HEAD", check=False).stdout.strip() or "main"
    rng = "%s..%s" % (base_ref or "origin/main", branch) if base and sh("git merge-base --is-ancestor %s HEAD" % (base_ref or "origin/main"), check=False).returncode == 0 else "--all"
    sh("git bundle create -q %s %s" % (path, rng))   # thin: only the new commits, under the branch's own ref name (refs/heads/<branch>) so `git pull <bundle> <branch>` finds it
    raw = open(path, "rb").read(); sha = hashlib.sha256(raw).hexdigest()
    b64 = base64.b64encode(raw).decode(); open(path + ".b64", "w").write(b64)
    PART = 45000   # a Drive text upload through the connector is one tool call, capped well under this; parts of 45 KB survive (9/23 lesson)
    parts = []
    for i in range(0, len(b64), PART):
        name = "%s.bundle.b64.part%02d" % (stem, len(parts) + 1); chunk = b64[i:i + PART]
        chunk = "\n".join(chunk[j:j + 76] for j in range(0, len(chunk), 76)) + "\n"   # 76-char lines: a Read tool truncates very long lines; apply_bundle strips the whitespace again
        open(os.path.join(out, name), "w").write(chunk); parts.append({"name": name, "chars": len(chunk), "sha256": hashlib.sha256(chunk.encode()).hexdigest()})
    commits = sh("git log --format=%%h\\ %%s %s" % (rng if rng != "--all" else "-20"), check=False).stdout.strip().splitlines()
    man = {"package": stem, "bundle": stem + ".bundle.b64", "sha256": sha, "bytes": len(raw), "range": rng, "branch": branch, "base": base, "head": sh("git rev-parse HEAD").stdout.strip(),
           "commits": commits, "created": TODAY,
           "parts": parts,
           "apply": "download every part (PACKAGE_<stem>.bundle.b64.partNN, text) and tools/mirror/apply_bundle.py (loose copy 'PACKAGE_apply_bundle.py' in 'github mirror' when tools/mirror/ is not in main yet); "
                    "python3 apply_bundle.py <part01> <part02> ... --sha256 %s (it concatenates the parts, decodes, verifies, pulls refs/heads/%s = a fast-forward when main is still at base %s) "
                    "&& git push origin %s && git push origin HEAD:<synced branch>; then mirror.py sync (Postman regenerate + Drive copies). Without apply_bundle.py: cat parts > x.b64; base64 -d x.b64 > x.bundle; git bundle verify x.bundle; git pull --no-rebase x.bundle %s" % (sha, branch, base[:9], branch, branch)}
    _json.dump(man, open(os.path.join(out, stem + ".manifest.json"), "w"), indent=1)
    print("git: push blocked -> PACKAGE written: %s(.b64) + %s.manifest.json (sha256 %s, %d commits)" % (path, stem, sha[:12], len(commits)))
    print("     upload the PARTS (%d x <=45 KB text, PACKAGE_<stem>.bundle.b64.partNN) + the manifest (PACKAGE_<stem>.manifest.json) + a loose PACKAGE_apply_bundle.py to Drive 'github mirror' (%s)"
          " - the routine cannot read project docs, so Drive must carry the bytes; project_write the whole .b64 as mirror/outbox/%s.bundle.b64 too (byte-exact, for a chat session)."
          " The next routine run's GITHUB INBOX step applies it and pushes. William need not touch it." % (len(parts), DRIVE["github mirror"], stem))
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
