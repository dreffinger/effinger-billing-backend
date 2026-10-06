#!/usr/bin/env python3
# PLAIN ENGLISH (GitHub inbox: apply a bundle package that a blocked session left on Drive / in the project)
# Decides: Nothing about billing. Takes a git bundle (.bundle or base64 .b64 text, as the chat sessions leave them in Drive
#          "github mirror" and in the project doc mirror/outbox/), verifies it (sha256 against the manifest/POINTER when given,
#          then `git bundle verify`), pulls its `main` into this clone, and records it in practices/<practice>/registers/bundles_applied.json
#          so the routine's mirror step can push main + the synced branch and regenerate Postman/Drive from what the session learned.
# Rules it uses: never applies the same bundle twice (sha256 register); never force-merges - a conflict stops with the bundle left
#          untouched for William; the working tree must be clean.  Never touches: AMD, Drive, Postman (the caller does the mirror).
"""Usage: python3 tools/mirror/apply_bundle.py <bundle.b64|bundle | part01.b64 part02.b64 ...> [--sha256 <hex>] [--register practices/ehpa/registers/bundles_applied.json] [--dry]
Exit 0 = applied (or already applied), 2 = verification failed, 3 = merge conflict / dirty tree."""
import sys, os, json, base64, hashlib, subprocess, datetime, re, tempfile
def sh(*a, **k):
    r = subprocess.run(a, capture_output=True, text=True, **k); return r.returncode, (r.stdout + r.stderr).strip()
UNION = ["docs/captured_calls.md merge=union", "docs/captured_calls_additions_*.md merge=union", "practices/ehpa/rules.md merge=union", "needs_facesheet_list.md merge=union",
         "docs/SHARED_LESSONS.md merge=union", "practices/ehpa/registers/rebill_log.jsonl merge=union"]
def union_rules():
    """Repo-local merge driver (.git/info/attributes, not committed): registry / rules / facesheet list are append-only text, so a
    merge keeps both sides instead of stopping on a conflict. Idempotent."""
    d = sh("git", "rev-parse", "--git-dir")[1]; f = os.path.join(d, "info", "attributes"); os.makedirs(os.path.dirname(f), exist_ok=True)
    have = open(f).read() if os.path.exists(f) else ""
    add = [r for r in UNION if r not in have]
    if add: open(f, "a").write(("" if not have or have.endswith("\n") else "\n") + "\n".join(add) + "\n")
def resolve_generated():
    """A conflicted pull is finished here only when every conflicted file is one this script knows how to rebuild:
    docs/api_vocabulary.json (union of calls by id, the longer description wins) and docs/postman_effinger_amd.json
    (regenerated from the merged vocabulary by tools/mirror/postman_build.py). Anything else -> False (caller aborts)."""
    files = [ln for ln in sh("git", "diff", "--name-only", "--diff-filter=U")[1].splitlines() if ln.strip()]
    if not files: return False
    known = {"docs/api_vocabulary.json", "docs/postman_effinger_amd.json"}
    if any(f not in known for f in files): print("conflicts outside the generated files:", files); return False
    if "docs/api_vocabulary.json" in files:
        try:
            ours = json.loads(sh("git", "show", ":2:docs/api_vocabulary.json")[1]); theirs = json.loads(sh("git", "show", ":3:docs/api_vocabulary.json")[1])
        except Exception as e:
            print("vocabulary sides unreadable:", e); return False
        merged = dict(ours); calls = {c["id"]: c for c in ours.get("calls", [])}
        for c in theirs.get("calls", []):
            if c["id"] not in calls or len(c.get("description", "")) > len(calls[c["id"]].get("description", "")): calls[c["id"]] = c
        for k in ("folders", "variables"):
            if isinstance(ours.get(k), list) and isinstance(theirs.get(k), list):
                merged[k] = ours[k] + [x for x in theirs[k] if x not in ours[k]]
            elif isinstance(ours.get(k), dict) and isinstance(theirs.get(k), dict):
                merged[k] = {**theirs[k], **ours[k]}
        merged["calls"] = list(calls.values())
        json.dump(merged, open("docs/api_vocabulary.json", "w"), indent=1, ensure_ascii=False); sh("git", "add", "docs/api_vocabulary.json")
        print("vocabulary merged by call id:", len(merged["calls"]), "calls")
    if "docs/postman_effinger_amd.json" in files or "docs/api_vocabulary.json" in files:
        pmb = "tools/mirror/postman_build.py"
        if not os.path.exists(pmb): print("postman_build.py missing - cannot regenerate"); return False
        code, out = sh(sys.executable, pmb)
        if code != 0: print("postman_build failed:", out[-300:]); return False
        sh("git", "add", "docs/postman_effinger_amd.json"); print("Postman JSON regenerated from the merged vocabulary")
    code, out = sh("git", "commit", "--no-edit")
    if code != 0: print("merge commit failed:", out[-300:]); return False
    return True

def main():
    args = sys.argv[1:]
    if not args: print(__doc__); return 1
    want = args[args.index("--sha256") + 1] if "--sha256" in args else None
    reg = args[args.index("--register") + 1] if "--register" in args else "practices/ehpa/registers/bundles_applied.json"
    dry = "--dry" in args
    flags = {"--sha256", "--register"}
    srcs = [a for i, a in enumerate(args) if not a.startswith("--") and (i == 0 or args[i - 1] not in flags)]   # one .bundle/.b64, or the .b64 PARTS in order (part01 part02 ...; a Drive text upload is capped, so big packages are split - 9/23 lesson)
    src = srcs[0]
    if len(srcs) > 1 or src.endswith(".b64"):
        text = "".join(open(s_, "rb").read().decode("ascii", "ignore") for s_ in sorted(srcs) if len(srcs) > 1) if len(srcs) > 1 else open(src, "rb").read().decode("ascii", "ignore")
        text = re.sub(r"\s+", "", text)      # Drive text uploads may wrap / flip characters (9/14 lesson) - the sha256 check below catches a flip
        raw = base64.b64decode(text)
    else:
        raw = open(src, "rb").read()
        if raw[:4] != b"# v2":
            raw = base64.b64decode(re.sub(r"\s+", "", raw.decode("ascii", "ignore")))
    h = hashlib.sha256(raw).hexdigest()
    if want and h.lower() != want.lower(): print("SHA256 MISMATCH: bundle %s vs manifest %s - not applied" % (h, want)); return 2
    applied = json.load(open(reg)) if os.path.exists(reg) else []
    if any(x.get("sha256") == h for x in applied): print("already applied:", h); return 0
    tmp = os.path.join(tempfile.gettempdir(), "inbox_%s.bundle" % h[:12]); open(tmp, "wb").write(raw)   # outside the repo: an untracked file must not fail the clean-tree check
    try:
        code, out = sh("git", "bundle", "verify", tmp)
        if code != 0: print("git bundle verify FAILED:", out); return 2
        heads = sh("git", "bundle", "list-heads", tmp)[1]; print("bundle heads:", heads.replace("\n", " | "))
        refs = [ln.split()[1] for ln in heads.splitlines() if len(ln.split()) > 1]
        ref = next((r.replace("refs/heads/", "") for r in refs if r.startswith("refs/heads/")), "HEAD")   # thin packages carry refs/heads/<branch>; older ones only HEAD
        if sh("git", "status", "--porcelain", "--untracked-files=no")[1].strip(): print("working tree not clean (tracked changes) - commit or stash first"); return 3
        if dry: print("DRY: would pull", tmp); return 0
        union_rules()                                     # append-only text files merge by union (both sides kept) - origin/main moves every 2 h, so the pull is a merge, not a fast-forward
        code, out = sh("git", "pull", "--no-rebase", "--no-edit", tmp, ref)
        if code != 0 and not resolve_generated():
            sh("git", "merge", "--abort"); print("PULL FAILED (conflict?) - bundle left for William:", out[-400:]); return 3
        head = sh("git", "rev-parse", "HEAD")[1]
        applied.append({"sha256": h, "source": os.path.basename(src), "applied": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"), "head_after": head, "heads": heads})
        os.makedirs(os.path.dirname(reg), exist_ok=True); json.dump(applied, open(reg, "w"), indent=1)
        print("applied", h[:12], "-> HEAD", head[:9], "| now push main + the synced branch and run the mirror (Postman regenerate, Drive copies)")
        return 0
    finally:
        if os.path.exists(tmp): os.remove(tmp)
if __name__ == "__main__": sys.exit(main())
