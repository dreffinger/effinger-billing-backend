#!/usr/bin/env python3
"""Load the staging folders of one layer of the AdvancedMD pull into the practice database through its one door (tools/db/neon_db.py
load-docs, source amd_history; the collection is the layer's name). The pull writes folders of 200 charts in the order they finish
(docs_<layer>/sNNNNN/<layer>/pat<id>.json); every folder but the one still filling is loaded as soon as it is full, the last one when the
pull has ended. The upsert is idempotent, so a folder loaded twice changes nothing.
Usage: load_layer.py <prod|preview> <chartfacts|chargedetail> [--watch]"""
import os, sys, json, time, glob, subprocess, datetime
S = "/tmp/claude-0/-home-user/5aaa27c8-6973-50aa-bba1-4b473bbc3aa7/scratchpad/amdpull"
NEON_DB = "/tmp/claude-0/-home-user/5aaa27c8-6973-50aa-bba1-4b473bbc3aa7/scratchpad/billing-main/tools/db/neon_db.py"
target, layer = sys.argv[1], sys.argv[2]; watch = "--watch" in sys.argv
CMDNAME = {"chartfacts": "demog", "chargedetail": "detail"}[layer]
LOADED = os.path.join(S, "state", "loaded_%s_%s.json" % (layer, target)); LOG = os.path.join(S, "load.log")
def log(*p):
    line = "%s %s" % (datetime.datetime.now(datetime.timezone.utc).strftime("%H:%M:%S"), " ".join(str(x) for x in p))
    open(LOG, "a").write(line + "\n"); print(line, flush=True)
def running(): return subprocess.run(["pgrep", "-f", "amd_pull2.py %s" % CMDNAME], capture_output=True).returncode == 0
def folders(): return sorted(d for d in glob.glob(os.path.join(S, "docs_" + layer, "s*")) if os.path.isdir(os.path.join(d, layer)))
def count(d): return len([f for f in os.listdir(os.path.join(d, layer)) if f.endswith(".json")])
loaded = json.load(open(LOADED)) if os.path.exists(LOADED) else {}
fails = 0
while True:
    run = running(); fs = folders(); did = 0
    for d in fs:
        b = os.path.basename(d); n = count(d)
        if not n or loaded.get(b, {}).get("docs") == n: continue
        if run and d == fs[-1]: continue                     # still filling
        r = subprocess.run([sys.executable, os.path.join(S, "neon_exec.py"), target, "--env-for-subprocess", sys.executable, NEON_DB, "load-docs", "--src", d,
                            "--source", "amd_history", "--by", "chat session 11/10/2026: AdvancedMD pull (%s)" % layer], capture_output=True, text=True)
        out = (r.stdout.strip().splitlines() or [""])[-1]
        if r.returncode != 0 or "load-docs" not in out:
            fails += 1; log("LOAD FAILED", layer, b, (r.stderr or r.stdout)[-300:].replace("\n", " "))
            if fails >= 6: log("LOAD STOPPED %s: six failures - the documents stay on disk" % layer); sys.exit(2)
            time.sleep(30); continue
        loaded[b] = {"docs": n, "at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
        json.dump(loaded, open(LOADED, "w"), indent=1); did += 1
        log("loaded %s %s on %s: %s" % (layer, b, target, out[out.find("->"):][:140]))
    if not watch: break
    if not run and all(loaded.get(os.path.basename(d), {}).get("docs") == count(d) for d in folders() if count(d)):
        log("LOAD DONE %s on %s: %d folders, %d chart documents" % (layer, target, len(loaded), sum(v["docs"] for v in loaded.values()))); break
    if not did: time.sleep(45)
