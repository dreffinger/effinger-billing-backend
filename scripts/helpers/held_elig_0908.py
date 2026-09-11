# PLAIN ENGLISH (AMD eligibility over the 87 board cards that were waiting for Stedi discovery)
# Decides: Nothing yet - it looks. For every Insurance Refresh Board card still 'Holding for Stedi Insurance Discovery', runs AMD's free eligibility on every plan on the chart (elig_amd) and writes held_elig_0908.json: per patient, each plan's status (ACTIVE / INACTIVE / REJECTED + reason), Medicare Part A/B dates, the Advantage / other payer Medicare names, the SMMC MMA plan Medicaid names, hospice, date of death. The acting step reads that file.
# Rules it uses: elig_amd.run_plan (cached per day). Never SSNs.
# Never touches: charts, claims, the board.
# ---
import elig_amd, amd, json, glob, os, re, time
amd.login_cached()
D = "/tmp/claude-0/-home-claude/f8f2f49c-f474-51d0-8966-696579307f2a/scratchpad/board_new/docs"
out = json.load(open("held_elig_0908.json")) if os.path.exists("held_elig_0908.json") else {}
cards = []
for f in glob.glob(D + "/*-denials.json"):
    d = json.load(open(f))
    if any("Holding for Stedi Insurance Discovery" in (n.get("text") or "") for n in d.get("notes") or []): cards.append((os.path.basename(f)[:-5], d))
print(len(cards), "held cards")
import unicodedata
def slug(nm):
    last, first = (nm.split(",") + [""])[:2]; t = (last.strip() + "-" + first.strip().split(" ")[0]).lower()
    return re.sub(r"[^a-z0-9]+", "-", unicodedata.normalize("NFKD", t)).strip("-")
CAS = {}
for l in open(sorted(glob.glob("denial_cascade2_*.jsonl"))[-1]):
    r = json.loads(l); CAS[slug(r["patient"])] = str(r["pid"])
for cid, d in cards:
    pid = re.sub(r"\D", "", str(d.get("amdid") or "")) or CAS.get(cid.replace("-denials", ""), "")
    if not pid: print("no pid for", cid); continue
    if cid in out: continue
    try:
        pa, pl = elig_amd.plans(pid); rec = {"pid": pid, "patient": pa.get("name"), "dob": pa.get("dob"), "plans": []}
        for p in pl:
            s = elig_amd.run_plan(pid, p["id"].replace("ins", ""))
            rec["plans"].append({"seq": p.get("sequence"), "carrier": p.get("carrier"), "num": p.get("subscribernum"), "begin": p.get("begindate"), "end": p.get("enddate"), "status": s.get("status"),
                                 "plan_dates": s.get("plan_dates"), "partA": s.get("partA"), "partB": s.get("partB"), "death": s.get("date_of_death"),
                                 "others": [{"type": o.get("type"), "plan": o.get("plan"), "who": [x.get("name") or x.get("role") for x in o.get("entities") or []], "ids": [x.get("id") for x in o.get("entities") or [] if x.get("id")], "dates": o.get("dates")} for o in s.get("other_payers") or []],
                                 "mma": [(e.get("plan"), [x.get("name") for x in e.get("entities") or [] if x.get("name")]) for e in s.get("eb") or [] if (e.get("plan") or "").startswith("SMMC")],
                                 "aaa": s.get("aaa"), "address": s.get("address")})
            time.sleep(0.2)
        out[cid] = rec
        print("%-26s" % rec["patient"], " | ".join("%s %s %s" % (p["carrier"], p["status"], (p["others"][:1] or p["mma"][:1] or "")) for p in rec["plans"])[:200], flush=True)
    except Exception as e: out[cid] = {"pid": pid, "error": str(e)[:100]}; print(cid, "ERR", str(e)[:80])
    json.dump(out, open("held_elig_0908.json", "w"), indent=1)
print("done", len(out))
