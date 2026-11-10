#!/usr/bin/env python3
"""Load finished folders of pulled chart documents into the practice database through its one door (tools/db/neon_db.py load-docs,
source amd_history). A folder is loaded once every chart in it has been pulled; the upsert is idempotent, so a re-run changes nothing.
Usage: load_buckets.py <prod|preview> [--watch]   (--watch keeps going until the pull has finished and every folder is loaded)"""
import os, sys, json, time, glob, subprocess, datetime
S = "/tmp/claude-0/-home-user/5aaa27c8-6973-50aa-bba1-4b473bbc3aa7/scratchpad/amdpull"
NEON_DB = "/tmp/claude-0/-home-user/5aaa27c8-6973-50aa-bba1-4b473bbc3aa7/scratchpad/billing-main/tools/db/neon_db.py"
target = sys.argv[1]; watch = "--watch" in sys.argv
LOADED = os.path.join(S, "state", "loaded_%s.json" % target); LOG = os.path.join(S, "load.log")
def log(*p):
    line = "%s %s" % (datetime.datetime.now(datetime.timezone.utc).strftime("%H:%M:%S"), " ".join(str(x) for x in p))
    open(LOG, "a").write(line + "\n"); print(line, flush=True)
allids = sorted((l.strip() for l in open(os.path.join(S, "state", "patients.txt")) if l.strip().isdigit()), key=int)
buckets = {}
for i, pid in enumerate(allids): buckets.setdefault("b%03d" % (i // 500), []).append(pid)
def pulled():
    done = set(); errs = set()
    p = os.path.join(S, "state", "progress.jsonl")
    if os.path.exists(p):
        for line in open(p):
            try:
                r = json.loads(line)
                if r.get("ok"): done.add(r["id"])
            except Exception: pass
    return done
def pull_running(): return subprocess.run(["pgrep", "-f", "amd_pull.py pull"], capture_output=True).returncode == 0
loaded = json.load(open(LOADED)) if os.path.exists(LOADED) else {}
while True:
    done = pulled(); running = pull_running(); did = 0
    for b, ids in sorted(buckets.items()):
        have = [i for i in ids if i in done]
        complete = len(have) == len(ids)
        if loaded.get(b, {}).get("docs") == len(have) and (complete or not running): continue
        if not complete and running: continue                       # wait until the folder is whole (or the pull has ended)
        if not have: continue
        d = os.path.join(S, "docs", b)
        r = subprocess.run([sys.executable, os.path.join(S, "neon_exec.py"), target, "--env-for-subprocess", sys.executable, NEON_DB, "load-docs", "--src", d,
                            "--source", "amd_history", "--by", "chat session 11/10/2026: AdvancedMD history pull"], capture_output=True, text=True)
        out = (r.stdout.strip().splitlines() or [""])[-1]
        if r.returncode != 0 or "load-docs" not in out:
            log("LOAD FAILED", b, (r.stderr or r.stdout)[-300:].replace("\n", " ")); time.sleep(30); continue
        loaded[b] = {"docs": len(have), "complete": complete, "at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "line": out[-160:]}
        json.dump(loaded, open(LOADED, "w"), indent=1); did += 1
        log("loaded %s on %s: %s" % (b, target, out[out.find("->"):][:150]))
    total = sum(v["docs"] for v in loaded.values())
    if not watch: break
    if not running and all(loaded.get(b, {}).get("docs") == len([i for i in ids if i in done]) for b, ids in buckets.items() if any(i in done for i in ids)):
        log("LOAD DONE on %s: %d folders, %d chart documents" % (target, len(loaded), total)); break
    if not did: time.sleep(45)
