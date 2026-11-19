# PLAIN ENGLISH (insurance block for every card this press touched - BUTTON PRESS 2026-11-19T0805Z item B, William 11/19/2026:
#   "the card must show the insurance without opening AMD"). READ ONLY on AMD: for each card id + chart it reads the chart's plans
#   (getdemographic) in billing order with member id, begin/end dates and the patient's default order, runs AMD's free 271 on every
#   open plan (elig_amd.run per plan, cached per day under patient_db/<pid>/), and writes one upsert op per card: set insid (the lead
#   plan's member id), inscarrier, insplans (every plan in billing order with end dates), mbi (the Medicare plan's number when one is
#   there) + append one checks[] line per 271 and one api[] block per 271 answer. No `updated`, no status/need/why. Ops go to the
#   board_updates file named on the command line (built through board_ops.clean_file). Card ids and chart numbers come from
#   inbox/board_ins_cards_<stamp>.json (not from this file).
import json, sys, re, datetime, subprocess
import amd, elig_amd
from board_ops import clean_file
stamp = sys.argv[1]; NOW = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"); WHEN = "11/19"
cards = json.load(open("inbox/board_ins_cards_%s.json" % stamp))        # {card id: chart}
cj = json.load(open("carriers.json")); CODE = {v: k for k, v in cj.items()} if all(isinstance(v, str) for v in cj.values()) else {k: v[0] for k, v in cj.items()}
amd.login_cached()
def mdy(s): return s or ""
ops = []
for card, pid in cards.items():
    a, plans = elig_amd.plans(pid)
    order = [x for x in (a.get("insorder") or "").split(",") if x]
    def key(p): 
        s = p.get("sequence") or "99"
        return (order.index(s) if s in order else 99, int(s))
    plans = sorted(plans, key=key)
    parts = []; checks = []; api = []; mbi = ""; lead = None
    for p in plans:
        code = CODE.get(p.get("carrier"), p.get("carrier")); num = p.get("subscribernum") or ""; end = p.get("enddate") or ""; beg = p.get("begindate") or ""
        live = not end or datetime.datetime.strptime(end, "%m/%d/%Y").date() >= datetime.date.today()
        parts.append("seq %s %s %s (begin %s%s)" % (p.get("sequence"), code, num, beg, (", ENDED " + end) if end else ""))
        if code == "FLO02" and live and not mbi: mbi = num
        if live and lead is None: lead = (code, num)
        if not live: continue
        try: r = elig_amd.run_plan(pid, re.sub(r"\D", "", p["id"]))
        except Exception as e: r = None
        if r is None:
            checks.append({"ok": "na", "result": "271 not answered", "src": "AMD eligibility (free 271) - %s %s" % (code, p["id"]), "when": WHEN}); continue
        st = r.get("status"); aaa = ",".join(x.get("RejectReasonCode", "") for x in (r.get("aaa") or []))
        others = "; ".join("%s %s %s" % (o.get("type", ""), o.get("plan", ""), o.get("entity", "") or o.get("id", "")) for o in (r.get("other_payers") or [])[:6])
        txt = ("seq %s %s %s -> %s | %s" % (p.get("sequence"), code, num, st, elig_amd.one_line(r)))
        checks.append({"ok": "ok" if st == "ACTIVE" else ("no" if st in ("INACTIVE", "REJECTED") else "na"), "result": "%s%s%s" % (st, (" AAA " + aaa) if aaa else "", (" - other payers: " + others) if others else ""), "src": "AMD eligibility (free 271) - seq %s %s - button press 0805Z" % (p.get("sequence"), code), "when": WHEN})
        api.append({"src": "AMD 271 (free) - seq %s %s" % (p.get("sequence"), code), "at": NOW, "text": txt})
    sets = {"insplans": " · ".join(parts) + (" | chart order %s" % ",".join(order) if order else " | chart order (none)"), "inscarrier": lead[0] if lead else "", "insid": lead[1] if lead else "", "mbi": mbi, "amdid": str(pid)}
    ops.append({"op": "upsert", "collection": "items", "id": card, "set": sets, "append": {"checks": checks, "api": api,
                "notes": [{"who": "Claude", "at": NOW, "text": "Insurance as it stands on the chart after this morning's work (AMD's free 271 on every open plan, 11/19): see insplans / the lookup trail. Written by the ehpa Billing Button press 2026-11-19T0805Z (William: the card must show the insurance without opening AMD)."}]}})
    print(card, pid, sets["inscarrier"], sets["insid"][:3] + "..", len(checks), "271s")
doc = {"schema": "irb-board-updates/1", "source": "ehpa billing button press 2026-11-19T0805Z (run %s)" % stamp, "created": NOW, "ops": ops}
json.dump(clean_file(doc), open("board_updates_%s.json" % stamp, "w"), indent=1)
print(len(ops), "ops")
