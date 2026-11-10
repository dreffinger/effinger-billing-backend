#!/usr/bin/env python3
"""Load finished folders of one layer of the AdvancedMD pull into the practice database through its one door (tools/db/neon_db.py
load-docs, source amd_history; the collection is the layer's name). A folder is loaded when every chart in it is done for that layer,
or when the pull for that layer has ended; the upsert is idempotent.
Usage: load_layer.py <prod|preview> <chartfacts|chargedetail> [--watch]"""
import os, sys, json, time, subprocess, datetime
S = "/tmp/claude-0/-home-user/5aaa27c8-6973-50aa-bba1-4b473bbc3aa7/scratchpad/amdpull"
NEON_DB = "/tmp/claude-0/-home-user/5aaa27c8-6973-50aa-bba1-4b473bbc3aa7/scratchpad/billing-main/tools/db/neon_db.py"
target, layer = sys.argv[1], sys.argv[2]; watch = "--watch" in sys.argv
CMDNAME = {"chartfacts": "demog", "chargedetail": "detail"}[layer]
LOADED = os.path.join(S, "state", "loaded_%s_%s.json" % (layer, target)); LOG = os.path.join(S, "load.log")
def log(*p):
    line = "%s %s" % (datetime.datetime.now(datetime.timezone.utc).strftime("%H:%M:%S"), " ".join(str(x) for x in p))
    open(LOG, "a").write(line + "\n"); print(line, flush=True)
allids = sorted((l.strip() for l in open(os.path.join(S, "state", "patients.txt")) if l.strip().isdigit()), key=int)
buckets = {}
for i, pid in enumerate(allids): buckets.setdefault("b%03d" % (i // 500), []).append(pid)
def done_ids():
    d = set(); p = os.path.join(S, "state", "progress_%s.jsonl" % layer)
    if os.path.exists(p):
        for line in open(p):
            try:
                r = json.loads(line)
                if r.get("ok"): d.add(r["id"])
            except Exception: pass
    return d
def running(): return subprocess.run(["pgrep", "-f", "amd_pull2.py %s" % CMDNAME], capture_output=True).returncode == 0
loaded = json.load(open(LOADED)) if os.path.exists(LOADED) else {}
while True:
    done = done_ids(); run = running(); did = 0
    for b, ids in sorted(buckets.items()):
        have = [i for i in ids if i in done]; complete = len(have) == len(ids)
        if not have or loaded.get(b, {}).get("docs") == len(have): continue
        if not complete and run: continue
        d = os.path.join(S, "docs_" + layer, b)
        r = subprocess.run([sys.executable, os.path.join(S, "neon_exec.py"), target, "--env-for-subprocess", sys.executable, NEON_DB, "load-docs", "--src", d,
                            "--source", "amd_history", "--by", "chat session 11/10/2026: AdvancedMD pull (%s)" % layer], capture_output=True, text=True)
        out = (r.stdout.strip().splitlines() or [""])[-1]
        if r.returncode != 0 or "load-docs" not in out:
            log("LOAD FAILED", layer, b, (r.stderr or r.stdout)[-300:].replace("\n", " ")); time.sleep(30); continue
        loaded[b] = {"docs": len(have), "complete": complete, "at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
        json.dump(loaded, open(LOADED, "w"), indent=1); did += 1
        log("loaded %s %s on %s: %s" % (layer, b, target, out[out.find("->"):][:140]))
    if not watch: break
    if not run and all(loaded.get(b, {}).get("docs") == len([i for i in ids if i in done]) for b, ids in buckets.items() if any(i in done for i in ids)):
        log("LOAD DONE %s on %s: %d folders, %d chart documents" % (layer, target, len(loaded), sum(v["docs"] for v in loaded.values()))); break
    if not did: time.sleep(45)
