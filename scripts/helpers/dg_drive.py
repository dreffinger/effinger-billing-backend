# PLAIN ENGLISH (deceased cache <-> Drive 'workspace mirror' copy, 10/14/2026)
# Decides: nothing. Packs the guard's cache (pid -> dod / checked / src / name) into the compact names-free form kept on
#   Drive 'workspace mirror' as deceased_cache.json ({"dated": {pid: [dod, checked]}, "nodeath": {pid: checked}}) and
#   unpacks that form back into the cache the guard reads - merging, newest 'checked' wins, a real date always beats a
#   scrubbed '[DOB]' (the GitHub copy is PHI-gated and useless to the guard).
# Rules it uses: no names on Drive either (the guard never needs them); chart ids + dates only.
# Never touches: AMD, Stedi.
#   python3 dg_drive.py pack   <cache.json> <drive.json>
#   python3 dg_drive.py unpack <drive.json> <cache.json> [<cache2.json> ...]   (merge into every cache path given)
# 11/25/2026 (the second verification of that day's change): a day a helper wrote in eight digits or as MM/DD/YYYY IS a day - pack left
#   such a chart out of the Drive copy altogether (neither dated nor 'no death'), so the next run did not know it; and unpack stumbled over
#   an entry whose source is null. A day is now read in every shape a helper has written it in and goes to Drive as YYYY-MM-DD.
import json, re, sys, datetime
DATE = re.compile(r"\d{4}-\d{2}-\d{2}$")
def day(v):
    """A day as YYYY-MM-DD when it is a real calendar date written YYYY-MM-DD, in eight digits or as MM/DD/YYYY; None for anything else."""
    s = str(v or "").strip(); m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})$", s)
    if re.match(r"\d{8}$", s): s = "%s-%s-%s" % (s[:4], s[4:6], s[6:])
    elif m: s = "%s-%02d-%02d" % (m.group(3), int(m.group(1)), int(m.group(2)))
    if not DATE.match(s): return None
    try: return datetime.date.fromisoformat(s).isoformat()
    except ValueError: return None

def pack(cache_path, out_path):
    c = json.load(open(cache_path)); c = {k: v for k, v in c.items() if isinstance(v, dict)}
    dated = {k: [day(v["dod"]), v.get("checked")] for k, v in c.items() if v.get("dod") and day(v["dod"])}
    nodeath = {k: v.get("checked") for k, v in c.items() if not v.get("dod")}
    json.dump({"format": "deceased_cache_drive v1: dated = {pid: [dod, checked]}, nodeath = {pid: checked}", "dated": dated, "nodeath": nodeath},
              open(out_path, "w"), separators=(",", ":"), sort_keys=True)
    return len(dated), len(nodeath)

def unpack(drive_path, cache_paths):
    d = json.load(open(drive_path)); n = 0
    for cp in cache_paths:
        try: c = json.load(open(cp))
        except Exception: c = {}
        if not isinstance(c, dict): c = {}
        for pid, (dod, checked) in d.get("dated", {}).items():
            cur = c.get(pid) if isinstance(c.get(pid), dict) else {}
            if not day(dod): continue                                                # the Drive copy holds days only; anything else is not taken
            if not day(cur.get("dod")) or (checked or "") >= (cur.get("checked") or ""):
                c[pid] = {**cur, "dod": day(dod), "checked": checked or cur.get("checked"), "src": cur.get("src") if str(cur.get("src") or "").startswith(("stedi-medicare-271", "amd-medicare-271")) else "stedi-medicare-271 (drive copy)"}; n += 1
        for pid, checked in d.get("nodeath", {}).items():
            cur = c.get(pid) if isinstance(c.get(pid), dict) else {}
            if day(cur.get("dod")): continue                                         # a real date in the cache beats a no-death note
            if (checked or "") >= (cur.get("checked") or ""):
                c[pid] = {**cur, "dod": None, "checked": checked, "src": cur.get("src") or "stedi: no death on record (drive copy)"}
        json.dump(c, open(cp, "w"), indent=1, sort_keys=True)
    return n

if __name__ == "__main__":
    if sys.argv[1] == "pack": print("packed dated/nodeath:", pack(sys.argv[2], sys.argv[3]))
    elif sys.argv[1] == "unpack": print("dated entries merged:", unpack(sys.argv[2], sys.argv[3:]))
    else: sys.exit(__doc__)
