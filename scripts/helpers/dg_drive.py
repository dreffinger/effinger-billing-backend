# PLAIN ENGLISH (deceased cache <-> Drive 'workspace mirror' copy, 10/14/2026)
# Decides: nothing. Packs the guard's cache (pid -> dod / checked / src / name) into the compact names-free form kept on
#   Drive 'workspace mirror' as deceased_cache.json ({"dated": {pid: [dod, checked]}, "nodeath": {pid: checked}}) and
#   unpacks that form back into the cache the guard reads - merging, newest 'checked' wins, a real date always beats a
#   scrubbed '[DOB]' (the GitHub copy is PHI-gated and useless to the guard).
# Rules it uses: no names on Drive either (the guard never needs them); chart ids + dates only.
# Never touches: AMD, Stedi.
#   python3 dg_drive.py pack   <cache.json> <drive.json>
#   python3 dg_drive.py unpack <drive.json> <cache.json> [<cache2.json> ...]   (merge into every cache path given)
import json, re, sys
DATE = re.compile(r"\d{4}-\d{2}-\d{2}$")

def pack(cache_path, out_path):
    c = json.load(open(cache_path))
    dated = {k: [v["dod"], v.get("checked")] for k, v in c.items() if v.get("dod") and DATE.match(str(v["dod"]))}
    nodeath = {k: v.get("checked") for k, v in c.items() if not v.get("dod")}
    json.dump({"format": "deceased_cache_drive v1: dated = {pid: [dod, checked]}, nodeath = {pid: checked}", "dated": dated, "nodeath": nodeath},
              open(out_path, "w"), separators=(",", ":"), sort_keys=True)
    return len(dated), len(nodeath)

def unpack(drive_path, cache_paths):
    d = json.load(open(drive_path)); n = 0
    for cp in cache_paths:
        try: c = json.load(open(cp))
        except Exception: c = {}
        for pid, (dod, checked) in d.get("dated", {}).items():
            cur = c.get(pid) or {}
            if not (cur.get("dod") and DATE.match(str(cur.get("dod")))) or (checked or "") >= (cur.get("checked") or ""):
                c[pid] = {**cur, "dod": dod, "checked": checked or cur.get("checked"), "src": cur.get("src") if cur.get("src", "").startswith("stedi-medicare-271") else "stedi-medicare-271 (drive copy)"}; n += 1
        for pid, checked in d.get("nodeath", {}).items():
            cur = c.get(pid) or {}
            if cur.get("dod") and DATE.match(str(cur.get("dod"))): continue          # a real date in the cache beats a no-death note
            if (checked or "") >= (cur.get("checked") or ""):
                c[pid] = {**cur, "dod": None, "checked": checked, "src": cur.get("src") or "stedi: no death on record (drive copy)"}
        json.dump(c, open(cp, "w"), indent=1, sort_keys=True)
    return n

if __name__ == "__main__":
    if sys.argv[1] == "pack": print("packed dated/nodeath:", pack(sys.argv[2], sys.argv[3]))
    elif sys.argv[1] == "unpack": print("dated entries merged:", unpack(sys.argv[2], sys.argv[3:]))
    else: sys.exit(__doc__)
