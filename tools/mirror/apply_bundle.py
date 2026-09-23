#!/usr/bin/env python3
# PLAIN ENGLISH (GitHub inbox: apply a bundle package that a blocked session left on Drive / in the project)
# Decides: Nothing about billing. Takes a git bundle (.bundle or base64 .b64 text, as the chat sessions leave them in Drive
#          "github mirror" and in the project doc mirror/outbox/), verifies it (sha256 against the manifest/POINTER when given,
#          then `git bundle verify`), pulls its `main` into this clone, and records it in practices/<practice>/registers/bundles_applied.json
#          so the routine's mirror step can push main + the synced branch and regenerate Postman/Drive from what the session learned.
# Rules it uses: never applies the same bundle twice (sha256 register); never force-merges - a conflict stops with the bundle left
#          untouched for William; the working tree must be clean.  Never touches: AMD, Drive, Postman (the caller does the mirror).
"""Usage: python3 tools/mirror/apply_bundle.py <bundle.b64|bundle> [--sha256 <hex>] [--register practices/ehpa/registers/bundles_applied.json] [--dry]
Exit 0 = applied (or already applied), 2 = verification failed, 3 = merge conflict / dirty tree."""
import sys, os, json, base64, hashlib, subprocess, datetime, re
def sh(*a, **k):
    r = subprocess.run(a, capture_output=True, text=True, **k); return r.returncode, (r.stdout + r.stderr).strip()
def main():
    args = sys.argv[1:]
    if not args: print(__doc__); return 1
    src = args[0]; want = args[args.index("--sha256") + 1] if "--sha256" in args else None
    reg = args[args.index("--register") + 1] if "--register" in args else "practices/ehpa/registers/bundles_applied.json"
    dry = "--dry" in args
    root = sh("git", "rev-parse", "--show-toplevel")[1]; os.chdir(root)
    raw = open(src, "rb").read()
    if src.endswith(".b64") or raw[:4] != b"# v2":
        text = raw.decode("ascii", "ignore"); text = re.sub(r"\s+", "", text)      # Drive text uploads may wrap / flip characters (9/14 lesson) - the sha256 check below catches a flip
        raw = base64.b64decode(text)
    h = hashlib.sha256(raw).hexdigest()
    if want and h.lower() != want.lower(): print("SHA256 MISMATCH: bundle %s vs manifest %s - not applied" % (h, want)); return 2
    applied = json.load(open(reg)) if os.path.exists(reg) else []
    if any(x.get("sha256") == h for x in applied): print("already applied:", h); return 0
    tmp = os.path.join(root, ".inbox_%s.bundle" % h[:12]); open(tmp, "wb").write(raw)
    try:
        code, out = sh("git", "bundle", "verify", tmp)
        if code != 0: print("git bundle verify FAILED:", out); return 2
        heads = sh("git", "bundle", "list-heads", tmp)[1]; print("bundle heads:", heads.replace("\n", " | "))
        if sh("git", "status", "--porcelain")[1].strip(): print("working tree not clean - commit or stash first"); return 3
        if dry: print("DRY: would pull", tmp); return 0
        code, out = sh("git", "pull", "--no-rebase", "--no-edit", tmp, "main")
        if code != 0:
            sh("git", "merge", "--abort"); print("PULL FAILED (conflict?) - bundle left for William:", out[-400:]); return 3
        head = sh("git", "rev-parse", "HEAD")[1]
        applied.append({"sha256": h, "source": os.path.basename(src), "applied": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"), "head_after": head, "heads": heads})
        os.makedirs(os.path.dirname(reg), exist_ok=True); json.dump(applied, open(reg, "w"), indent=1)
        print("applied", h[:12], "-> HEAD", head[:9], "| now push main + the synced branch and run the mirror (Postman regenerate, Drive copies)")
        return 0
    finally:
        if os.path.exists(tmp): os.remove(tmp)
if __name__ == "__main__": sys.exit(main())
