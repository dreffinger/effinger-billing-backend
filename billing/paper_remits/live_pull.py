#!/usr/bin/env python3
import os
# PLAIN ENGLISH (any list of AMD accounts -> live chart state)
# Decides: Nothing. Reads a JSON list of {"acct": "19448899A", "patient": "..."} and writes <out>.json with each visit's live
#          charges / payments / write-offs / balances (gettxhistory visitid=) and the patient's plans (getdemographic).
#          Patient id: the unpaid-list name map, else lookuppatient by "LAST,FIR%".  Never touches: anything (read-only).
# Usage: python3 live_pull.py <in.json> <out.json>
import sys, json, re, time, collections
sys.path.insert(0, os.environ.get("SCANS_DIR", "/home/claude/scans") + "")
import amd, txh, payreasons
import xml.etree.ElementTree as ET
IN, OUT = sys.argv[1], sys.argv[2]
items = json.load(open(IN))
try: live = json.load(open(OUT))
except Exception: live = {}
U = json.load(open(os.environ.get("SCANS_DIR", "/home/claude/scans") + "/unpaid_2026-09-23.json"))
names = collections.defaultdict(set)
for v in U: names[re.sub(r"[^A-Z ,]", "", v["patientname"].upper()).strip()].add(str(v["patientid"]))
def norm(p): return re.sub(r"(PAMELA P GARCIA|WILLIAM L EFFINGER)", "", (p or "").upper()).strip()
def from_unpaid(patient):
    p = re.sub(r"[^A-Z ]", "", norm(patient)).split()
    if not p: return []
    first, last = p[0], p[-1]; c = set()
    for nm, pids in names.items():
        l, _, f = nm.partition(",")
        if last in l.strip().split(" ") and f.strip()[:3] == first[:3]: c |= pids
    return sorted(c)
def _lk(last, first):
    r = amd.post('<ppmdmsg action="lookuppatient" class="lookup" msgtime="%s" name="%s,%s%%" nocookie="1"/>' % (amd._msgtime(), last, first[:3]))
    try: return [x.attrib.get("id", "").replace("pat", "") for x in ET.fromstring(r.encode("latin-1", "ignore")).iter("patient") if x.attrib.get("id")]
    except Exception: return []
def lookup(patient):
    """'LAST,FIRST M' (CHAMPVA) or 'FIRST M LAST' / 'FIRST M LAST LAST2' (Florida Blue) -> AMD patient ids; tries the two-word surname too."""
    nm = norm(patient)
    if "," in nm:
        last, _, first = nm.partition(","); first = re.sub(r"[^A-Z ]", "", first).split()
        return _lk(re.sub(r"[^A-Z ]", "", last).strip(), first[0] if first else "")
    p = re.sub(r"[^A-Z ]", "", nm).split()
    if not p: return []
    first = p[0]
    for last in ([" ".join(p[-2:])] if len(p) >= 3 else []) + [p[-1]]:
        ids = _lk(last, first)
        if ids: return ids
    return []
def plans(pid):
    r = amd.post('<ppmdmsg action="getdemographic" class="demographics" msgtime="%s" patientid="pat%s" nocookie="1"/>' % (amd._msgtime(), pid))
    pl = [dict(re.findall(r'(\w+)="([^"]*)"', blk)) for blk in re.findall(r"<insplan [^>]*>", r)]
    dead = re.search(r'deathdate="([^"]+)"', r) or re.search(r'dod="([^"]+)"', r)
    return [{k: p.get(k) for k in ("id", "carrier", "sequence", "begindate", "enddate", "subscribernum", "insorder", "finclass")} for p in pl], (dead.group(1) if dead else "")
pl_cache = {}; lk = {}; n = 0
for it in items:
    acct = it["acct"]; key = acct
    if key in live and live[key].get("charges") is not None: continue
    vid = acct[:8] if re.match(r"\d{8}", acct) else None
    rec = {"acct": acct, "patient": it.get("patient"), "charges": None}
    if not vid: rec["error"] = "no visit id"; live[key] = rec; continue
    pids = it.get("pids") or from_unpaid(it.get("patient"))
    if not pids and it.get("patient"):
        if it.get("patient") not in lk: lk[it.get("patient")] = lookup(it.get("patient")); time.sleep(0.3)
        pids = lk[it.get("patient")]
    if not pids:   # no name at all: any unpaid visit of the same patient? (visit ids are per patient, so a neighbouring visit id is no guide) -> give up
        pids = []
    rec["pids"] = pids
    for pid in pids[:4]:
        try: st = payreasons.visit_state(pid, vid, root=txh.fetch_visit(pid, vid))
        except Exception as e: rec["error"] = str(e)[:120]; continue
        if st:
            rec["pid"] = pid; rec["charges"] = st
            if pid not in pl_cache:
                try: pl_cache[pid] = plans(pid)
                except Exception as e: pl_cache[pid] = ([], "err %s" % str(e)[:60])
            rec["plans"], rec["dod"] = pl_cache[pid]; break
        time.sleep(0.3)
    if rec["charges"] is None and "error" not in rec: rec["error"] = "visit not found under %s" % pids
    live[key] = rec; n += 1
    if n % 10 == 0: json.dump(live, open(OUT, "w"), indent=1); print(n, "done", flush=True)
    time.sleep(0.4)
json.dump(live, open(OUT, "w"), indent=1)
print("finished", len(live), "records;", sum(1 for r in live.values() if r.get("charges")), "with charges;", collections.Counter((r.get("error") or "ok")[:40] for r in live.values()))
